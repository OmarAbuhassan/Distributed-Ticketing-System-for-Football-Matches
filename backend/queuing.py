import asyncio
import logging
import json
from typing import Dict, Tuple, Set, List
from contextlib import asynccontextmanager

import requests
from confluent_kafka import Consumer, KafkaException, TopicPartition
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from confluent_kafka.admin import AdminClient, NewTopic


# Initialize the AdminClient for managing Kafka topics
admin_client = AdminClient({
    'bootstrap.servers': 'kafka:9092'  # Change to your broker's address
})


# ─── SETUP LOGGER ───────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("queue-service")

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP  = "kafka:9092"
GROUP_ID         = "reservation-queue-service"
MATCHES_API_URL  = "http://backend:8001/api/general/matches"
REFRESH_INTERVAL = 3  # seconds
MAX_QUEUE_SIZE   = 22

# ─── GLOBALS ────────────────────────────────────────────────────────────────────
consumer: Consumer
_paused_partitions: Dict[Tuple[int,str], Set[TopicPartition]] = {}

# ─── CONNECTION MANAGER ─────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self._conns: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def register(self, request_id: str, ws: WebSocket):
        async with self._lock:
            self._conns[request_id] = ws

    async def unregister(self, request_id: str):
        async with self._lock:
            self._conns.pop(request_id, None)

    async def send(self, request_id: str, payload: dict):
        ws = self._conns.get(request_id)
        if ws:
            await ws.send_json(payload)

conns = ConnectionManager()

# ─── QUEUE MANAGER ───────────────────────────────────────────────────────────────
class QueueManager:
    def __init__(self, maxsize: int):
        self._qs: Dict[Tuple[int,str], asyncio.Queue] = {}
        self._lock = asyncio.Lock()
        self.maxsize = maxsize

    async def get_queue(self, match_id: int, category: str) -> asyncio.Queue:
        key = (match_id, category)
        async with self._lock:
            if key not in self._qs:
                self._qs[key] = asyncio.Queue(maxsize=self.maxsize)
            return self._qs[key]

qm = QueueManager(maxsize=MAX_QUEUE_SIZE)

# ─── HELPERS ────────────────────────────────────────────────────────────────────
def parse_topic(topic: str) -> Tuple[int,str]:
    _, mid, cat = topic.split(".")
    return int(mid), cat

async def get_matches() -> List[int]:
    logger.info("Fetching matches from API...")
    try:
        resp = await asyncio.to_thread(
            requests.get,
            MATCHES_API_URL,
            headers={"accept": "application/json"},
            timeout=5
        )
        resp.raise_for_status()
        return [int(item["match_id"]) for item in resp.json()]
    except requests.RequestException as e:
        logger.error(f"Failed to fetch matches: {e}")
        return []

# ─── START CONSUMER WITH RETRY ───────────────────────────────────────────────────
async def start_consumer_with_retry():
    global consumer
    conf = {
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": GROUP_ID,
        "enable.auto.commit": False,
        "default.topic.config": {"auto.offset.reset": "earliest"}
    }
    backoff = 1
    while True:
        try:
            consumer = Consumer(conf)
            logger.info("✅ Kafka consumer created")
            break
        except KafkaException as e:
            logger.warning(f"❌ Kafka unavailable ({e}), retrying in {backoff}s…")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)

# ─── DYNAMIC SUBSCRIPTION ───────────────────────────────────────────────────────
# async def fetch_and_subscribe():
#     prev: Set[str] = set()
#     ids = await get_matches()
#     while True:
#         topics = { f"match.{mid}.{cat}" for mid in ids for cat in ("vip","premium","standard") }
#         if topics != prev:
#             consumer.subscribe(list(topics))
#             logger.info(f"Subscribed to topics: {topics}")
#             prev = topics
#         await asyncio.sleep(REFRESH_INTERVAL)

async def fetch_and_subscribe():
    await asyncio.sleep(3)  # Initial delay to allow consumer to start
    ids = await get_matches()
    
    while True:
        topics = { f"match.{mid}.{cat}" for mid in ids for cat in ("vip", "premium", "standard") }
        
        # Check if the topics exist, and create them if they don't
        for topic in topics:
            if topic not in await check_existing_topics():
                create_topic(topic)

        # Check if the consumer is subscribed to the topics
        consumer.subscribe(list(topics))
        current_subscription = set(consumer.subscription())  # Get the current subscription
        logger.info(f"Current subscription: {current_subscription}")
        logger.info(f"Requested topics: {topics}")
        
        if topics != current_subscription:
            # If not subscribed correctly, retry subscribing
            logger.warning(f"Not subscribed to all topics, retrying subscription...")
            consumer.subscribe(list(topics))  # Retry subscribing
            logger.info(f"Retrying subscription to topics: {topics}")
        
        await asyncio.sleep(REFRESH_INTERVAL)

async def check_existing_topics():
    # Fetch existing topics from Kafka broker
    metadata = admin_client.list_topics(timeout=10)
    return set(metadata.topics.keys())

def create_topic(topic):
    # Create the topic if it doesn't exist
    new_topic = NewTopic(topic, num_partitions=1, replication_factor=1)
    admin_client.create_topics([new_topic])
    logger.info(f"Created topic: {topic}")


# ─── KAFKA HANDLERS ─────────────────────────────────────────────────────────────
async def _handle_join(msg):
    data = json.loads(msg.value().decode('utf-8'))
    match_id, cat = parse_topic(msg.topic())
    q = await qm.get_queue(match_id, cat)
    req_id = data["request_id"]
    tp = TopicPartition(msg.topic(), msg.partition())

    try:
        q.put_nowait((msg, req_id))
    except asyncio.QueueFull:
        consumer.pause([tp])
        _paused_partitions.setdefault((match_id,cat), set()).add(tp)
        await conns.send(req_id, {
            "type":"queue_full","matchId":match_id,"category":cat
        })
    else:
        # commit this offset
        consumer.commit(message=msg)
        await conns.send(req_id,{
            "type":"start_selection",
            "matchId":match_id,
            "category":cat,
            "position":q.qsize()
        })

async def _kafka_listener():
    while True:
        # poll blocks in a thread so as not to block the event loop
        msg = await asyncio.to_thread(consumer.poll, 1.0)
        if msg is None:
            continue
        if msg.error():
            logger.error(f"Consumer error: {msg.error()}")
            continue
        await _handle_join(msg)

# ─── FASTAPI LIFESPAN ───────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.sleep(2)
    await start_consumer_with_retry()
    logger.info("🚀 Starting background tasks…")
    tasks = [
        asyncio.create_task(fetch_and_subscribe()),
        asyncio.create_task(_kafka_listener()),
    ]
    yield
    for t in tasks:
        t.cancel()
    consumer.close()

app = FastAPI(lifespan=lifespan)

# ─── WEBSOCKET ENDPOINT ─────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    data = await ws.receive_json()
    if data.get("action")!="register" or "request_id" not in data:
        await ws.close(code=1008)
        return

    req_id = data["request_id"]
    await conns.register(req_id, ws)

    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("action")=="finish":
                mid, cat = msg["matchId"], msg["category"]
                q = await qm.get_queue(mid, cat)
                try:
                    _, next_req = q.get_nowait()
                except asyncio.QueueEmpty:
                    continue

                await conns.send(next_req,{
                    "type":"your_turn","matchId":mid,"category":cat
                })

                paused = _paused_partitions.pop((mid,cat), None)
                if paused:
                    consumer.resume(list(paused))

    except WebSocketDisconnect:
        await conns.unregister(req_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "queuing:app",      # "module:variable"
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
