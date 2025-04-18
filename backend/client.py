# simple_ws_client_random.py

import time
import json
import random
import uuid
from websocket import create_connection

def random_match_id():
    return f"match_{random.randint(1, 100)}"

def random_category():
    return f"category_{random.choice(['A', 'B', 'C', 'D', 'E'])}"

def random_user_name():
    return f"user_{uuid.uuid4().hex[:8]}"

def main():
    ws = create_connection("ws://localhost:8000/ws")
    try:
        while True:
            msg = {
                "stage":    "1",
                "match_id": "11",
                "category":  "VIP",
                "user_name": random_user_name()
            }
            ws.send(json.dumps(msg))
            print("Sent:", msg)
            time.sleep(10)
    except KeyboardInterrupt:
        print("Interrupted, closing connection.")
    finally:
        ws.close()

if __name__ == "__main__":
    main()
