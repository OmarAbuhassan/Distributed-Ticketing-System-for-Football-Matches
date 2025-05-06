import asyncio
import json
import threading
from typing import Dict, Tuple, List

import requests
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from confluent_kafka import Consumer, KafkaException, TopicPartition, Producer
from confluent_kafka.admin import AdminClient, NewTopic
from contextlib import asynccontextmanager
import time

# ─── SETUP LOGGER ───────────────────────────────────────────────────────────────
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ─── CONFIG ─────────────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP = "kafka:9092"
BACKEND_MATCHES_API = "http://backend:8001/api/general/matches"
MAX_QUEUE_SIZE = 1
GROUP_ID = "reservation-queue-service"

# ─── GLOBALS ─────────────────────────────────────────────────────────────────────
app = FastAPI()

admin_client = AdminClient({'bootstrap.servers': KAFKA_BOOTSTRAP})

producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP})

connections: Dict[Tuple[str, str, str], WebSocket] = {}
waiting_users: Dict[str, List[str]] = {}  # topic -> list of usernames
locks: Dict[str, asyncio.Lock] = {}       # topic -> Lock

# Add paused state globally
paused_consumers: Dict[str, bool] = {}
consumer_objects: Dict[str, Consumer] = {}

users =[]


# ─── HELPERS ─────────────────────────────────────────────────────────────────────

def get_topic_name(match_id: str, category: str) -> str:
    return f"match.{match_id}.{category.lower()}"

async def get_matches_from_backend():
    response = requests.get(BACKEND_MATCHES_API)
    response.raise_for_status()
    return response.json()

def create_topics(matches_data):
    topics = []
    default_categories = ["vip", "premium", "standard"]

    for match in matches_data:
        match_id = match["match_id"]  # Still get match_id
        for cat in default_categories:
            topic = get_topic_name(match_id, cat)
            topics.append(NewTopic(topic, num_partitions=1, replication_factor=1))
            waiting_users[topic] = []
            locks[topic] = asyncio.Lock()

        for attempt in range(5):  # try 5 times
            futures = admin_client.create_topics(topics)

            all_ok = True
            for topic, future in futures.items():
                try:
                    future.result()
                    logging.info(f"✅ Created topic: {topic}")
                except Exception as e:
                    logging.info(f"⚠️ Failed to create topic {topic}: {e}")
                    all_ok = False

            if all_ok:
                break
            else:
                print("⏳ Waiting 3 seconds before retrying topic creation...")
                time.sleep(1)

def start_consumer(topic_name: str):
    def run():
        consumer = Consumer({
            'bootstrap.servers': KAFKA_BOOTSTRAP,
            'group.id': GROUP_ID + "_" + topic_name,
            'auto.offset.reset': 'earliest'
        })
        tp = TopicPartition(topic_name, 0)
        consumer.subscribe([topic_name])
        consumer_objects[topic_name] = consumer
        paused_consumers[topic_name] = False
        logging.info(f"Starting consumer for topic {topic_name}.")

        while True:
            if len(waiting_users[topic_name]) >= MAX_QUEUE_SIZE:
                logging.info(f"Queue for topic {topic_name} is full. Pausing consumer if not already paused.")
                if not paused_consumers[topic_name]:
                    consumer.pause([tp])
                    paused_consumers[topic_name] = True
                continue

            if paused_consumers[topic_name]:
                logging.info(f"Resuming consumer for topic {topic_name}.")
                consumer.resume([tp])
                paused_consumers[topic_name] = False

            msg = consumer.poll(1.0)
            if msg is None:
                # logging.info(f"No message received for topic {topic_name}.")
                continue
            if msg.error():
                logging.error(f"Error in consumer for topic {topic_name}: {msg.error()}")
                continue

            logging.info(f"Received message for topic {topic_name}: {msg.value()}")
            

            data = json.loads(msg.value())
            logging.info(f"Decoded message: {data}")
            user_name = data["username"]
            while user_name not in users:
                logging.info(f"User {user_name} not registered. Waiting for registration.")
                time.sleep(1)

            asyncio.run(notify_user_if_possible(topic_name, user_name))

    threading.Thread(target=run, daemon=True).start()


async def notify_dashboard(topic: str):
    """Notify dashboard of queue changes"""
    try:
        match_id = topic.split(".")[1]
        category = topic.split(".")[2]
        async with httpx.AsyncClient() as client:
            await client.post("http://dashboard:8003/events", json={
                "type": "queue_update",
                "data": {
                    "match_id": match_id,
                    "category": category,
                    "queue_length": len(waiting_users[topic])
                }
            })
    except Exception as e:
        logging.error(f"Failed to notify dashboard: {e}")

async def notify_user_if_possible(topic: str, user_name: str):
    logging.info(f"Checking if user {user_name} can be notified for topic {topic}.")
    async with locks[topic]:
        if user_name not in waiting_users[topic]:
            logging.info(f"User {user_name} is not in the waiting list for topic {topic}. Adding them.")
            waiting_users[topic].append(user_name)
            await notify_dashboard(topic)  # Notify dashboard of queue change
        else:
            logging.info(f"User {user_name} is already in the waiting list for topic {topic}.")
        
        match_id = topic.split(".")[1]
        cat = topic.split(".")[2]

        logging.info(f"Notifying user {user_name} for topic {topic}.")


        ws_key = (user_name.lower(), topic.split(".")[1], topic.split(".")[2].lower())  # (user_name, match_id, category)
        websocket = connections.get(ws_key)
        logging.info(f"WebSocket connection for user with key {ws_key}: {websocket}")
        if websocket:
            await websocket.send_json({"type":"start_selection",
            "matchId":match_id,
            "category":cat,
            "position":len(waiting_users[topic])})

async def handle_register(data: dict, websocket: WebSocket):
    logging.info(data)
    user_name = data["user_name"].lower()
    match_id = data["matchId"]
    category = data["category"].lower()
    # make sure category is lowercase

    topic = get_topic_name(match_id, category)
    connections[(user_name, match_id, category)] = websocket
    logging.info(f"new connection: user_name={user_name}, match_id={match_id}, category={category}")
    # send response 
    users.append(user_name)
    await websocket.send_json({
        "type": "registered",
        "matchId": match_id,
        "category": category
    })

async def handle_finish(data: dict):
    user_name = data["user_name"]
    match_id = data["matchId"]
    category = data["category"]
    topic = get_topic_name(match_id, category)

    async with locks[topic]:
        if user_name in waiting_users[topic]:
            waiting_users[topic].remove(user_name)
            await notify_dashboard(topic)  # Notify dashboard of queue change

        # resume Kafka consumer if it was paused
        if paused_consumers.get(topic):
            tp = TopicPartition(topic, 0)
            consumer = consumer_objects[topic]
            consumer.resume([tp])
            paused_consumers[topic] = False

# ─── FASTAPI ENDPOINTS ───────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "register":
                logging.info(f"Registering user: {data}")
                await handle_register(data, websocket)

            elif action == "finish":
                logging.info(f"Finishing user: {data}")
                await handle_finish(data)

    except WebSocketDisconnect:
        # Remove disconnected user
        logging.info(f"WebSocket disconnected: {websocket.client}")

# ─── LIFESPAN: INIT ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    matches_data = await get_matches_from_backend()
    print(matches_data)
    await asyncio.to_thread(create_topics, matches_data)

    # Start a consumer thread for each topic
    default_categories = ["vip", "premium", "standard"]
    for match in matches_data:
        match_id = match["match_id"]
        for category in default_categories:
            topic = get_topic_name(match_id, category)
            start_consumer(topic)

    yield

app.router.lifespan_context = lifespan

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "queuing:app",      # "module:variable"
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
