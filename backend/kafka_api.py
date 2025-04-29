# service.py
from fastapi import FastAPI, Request
from confluent_kafka import Producer
import json
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
req_ids = []

# Kafka Producer configuration
producer_config = {
    'bootstrap.servers': 'kafka:9092'  # Update as needed
}
producer = Producer(producer_config)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:5173"] to restrict
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery failed for record {msg.key()}: {err}")
    else:
        print(f"Record {msg.key()} successfully produced to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

@app.post("/publish")
async def publish_message(request: Request, topic: str = None, request_id: str = None, username: str = None):

    if request_id in req_ids:
        return {"status": "error", "details": "Request ID already exists."}
    req_ids.append(request_id)

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
    

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "kafka_api:app",      # "module:variable"
        host="0.0.0.0",
        port=8009,
        reload=True,        # hot-reload on file changes (dev only)
        log_level="info"
    )

