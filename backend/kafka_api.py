# service.py
from fastapi import FastAPI, Request
from confluent_kafka import Producer
import json

app = FastAPI()

# Kafka Producer configuration
producer_config = {
    'bootstrap.servers': 'localhost:9092'  # Update as needed
}
producer = Producer(producer_config)

def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery failed for record {msg.key()}: {err}")
    else:
        print(f"Record {msg.key()} successfully produced to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

@app.post("/publish")
async def publish_message(request: Request):
    body = await request.json()

    # Extract topic and message
    topic = body.get("topic")
    request_id = body.get("request_id")
    username = body.get("username")

    # create json message containing request_id and username
    message = {
        "request_id": request_id,
        "username": username
    }

    if not topic or not request_id or not username:
        return {"status": "error", "details": "Both 'topic' and 'message' fields are required."}

    try:
        producer.produce(topic, value=json.dumps(message), callback=delivery_report)
        producer.flush()
        return {"status": "success", "topic": topic, "message": message}
    except Exception as e:
        return {"status": "error", "details": str(e)}
