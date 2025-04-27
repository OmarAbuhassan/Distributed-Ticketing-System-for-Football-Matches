import asyncio
import logging
from typing import Dict, Tuple, Set, List
from contextlib import asynccontextmanager

import requests
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError
from aiokafka.structs import TopicPartition, OffsetAndMetadata
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# ─── SETUP LOGGER ───────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("queue-service")

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP  = "kafka:9092"
GROUP_ID         = "reservation-queue-service"
MATCHES_API_URL  = "http://backend:8001/api/general/matches"
REFRESH_INTERVAL = 30  # seconds
MAX_QUEUE_SIZE   = 5

# ─── GLOBALS ────────────────────────────────────────────────────────────────────
consumer: AIOKafkaConsumer
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
        # run the blocking requests.get in a thread
        resp = await asyncio.to_thread(
            requests.get,
            MATCHES_API_URL,
            headers={"accept": "application/json"},
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        print(data)
        return [int(item["match_id"]) for item in data]
    except requests.RequestException as e:
        logger.error(f"Failed to fetch matches: {e}")
        return []
        

# ─── START CONSUMER WITH RETRY ───────────────────────────────────────────────────
async def start_consumer_with_retry():
    global consumer
    consumer = AIOKafkaConsumer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=GROUP_ID,
        enable_auto_commit=False,
    )
    backoff = 1
    while True:
        try:
            await consumer.start()
            logger.info("✅ Kafka consumer started")
            break
        except KafkaConnectionError as e:
            logger.warning(f"❌ Kafka unavailable ({e}), retrying in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)

# ─── DYNAMIC SUBSCRIPTION ───────────────────────────────────────────────────────
async def fetch_and_subscribe():
    prev: Set[str] = set()
    while True:
        ids = await get_matches()
        topics = { f"match.{mid}.{cat}" for mid in ids for cat in ("vip","premium","standard") }
        if topics != prev:
            consumer.subscribe(topics=list(topics))
            logger.info(f"Subscribed to topics: {topics}")
            prev = topics
        await asyncio.sleep(REFRESH_INTERVAL)

# ─── KAFKA HANDLERS ─────────────────────────────────────────────────────────────
async def _handle_join(msg):
    match_id, cat = parse_topic(msg.topic)
    q = await qm.get_queue(match_id, cat)
    req_id = msg.value["request_id"]
    tp = TopicPartition(msg.topic, msg.partition)

    try:
        q.put_nowait((msg, req_id))
    except asyncio.QueueFull:
        consumer.pause(tp)
        _paused_partitions.setdefault((match_id,cat), set()).add(tp)
        await conns.send(req_id, {"type":"queue_full","matchId":match_id,"category":cat})
    else:
        await consumer.commit({tp:OffsetAndMetadata(msg.offset+1,None)})
        await conns.send(req_id,{
            "type":"start_selection",
            "matchId":match_id,
            "category":cat,
            "position":q.qsize()
        })

async def _kafka_listener():
    async for msg in consumer:
        await _handle_join(msg)

# ─── FASTAPI LIFESPAN ───────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1) start consumer with retry
    await start_consumer_with_retry()
    # 2) kick off background tasks
    logger.info("🚀 Starting background tasks…")
    tasks = [
        asyncio.create_task(fetch_and_subscribe()),
        asyncio.create_task(_kafka_listener()),
    ]
    yield
    # 3) shutdown
    for t in tasks:
        t.cancel()
    await consumer.stop()

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
                # Need to check if the request_id is in the queue
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
                    consumer.resume(*paused)

    except WebSocketDisconnect:
        await conns.unregister(req_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "queuing:app",      # "module:variable"
        host="0.0.0.0",
        port=8002,
        reload=True,        # hot-reload on file changes (dev only)
        log_level="info"
    )