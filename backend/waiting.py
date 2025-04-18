import os
import threading
import time
import uuid
import multiprocessing
from multiprocessing import Process, Queue
from db.csv_api import *
from threading import Lock
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
from collections import deque
from routes import general, reservation
import socket
import json
import uvicorn


# Initialize FastAPI
app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:5173"] to restrict
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Include routers
app.include_router(general.router, prefix="/api/general", tags=["general"])
app.include_router(reservation.router, prefix="/api/reservation", tags=["reservation"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:5173"] to restrict
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Create a queue to store active WebSocket connections for FCFS
connection_queue = Queue()


@app.on_event("startup")
def start_background_tasks():
    threading.Thread(
        target=waiting_queue_manager,
        args=(waiting_queues, reserving_queues),
        daemon=True
    ).start()
    threading.Thread(
        target=reserving_queue_manager,
        args=(reserving_queues, waiting_queues),
        daemon=True
    ).start()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_id = str(uuid.uuid4())
    print(f"[WS] Client connected: {client_id}")

    try:
        while True:
            data = await websocket.receive_json()  # <-- now inside a loop
            # attach the client_id so your manager knows who's who
            connection_queue.put({
                "client_id": client_id,
                **data
            })
    except WebSocketDisconnect:
        print(f"[WS] Client disconnected: {client_id}")
    except Exception as e:
        # if they'd sent bad JSON you can choose to continue or break:
        await websocket.send_json({"error": "Invalid JSON, expected JSON body"})

waiting_queues_lock = Lock()
writing_request_lock = Lock()
writing_status_lock = Lock()

# Configuration
DATA_DIR = "./db"
waiting_queues = {}
waiting_queues_recorder = {}
reserving_queues = {}

worker_processes = {}

# SELECTION_HOST = "127.0.0.1"
# SELECTION_PORT = 6000
LISTEN_HOST    = "127.0.0.1"
LISTEN_PORT    = 5000




requests_status_db = os.path.join(DATA_DIR, "requests_status.csv")
requests_db = os.path.join(DATA_DIR, "requests.csv")

request_feild = ["request_id","user_name","match_id","catagory","latest_status"]
request_status_field = ["requests_status_id", "request_id", "status", "timestamp"]

def request_object(request_id, username, match_id, category, status="waiting"):
    return {
        "request_id": request_id,
        "user_name": username,
        "match_id": match_id,
        "catagory": category,
        "latest_status": status
    }

def status_object(request_id, status):
    return {
        "requests_status_id": str(uuid.uuid4()),
        "request_id": request_id,
        "status": status,
        "timestamp": time.time()
    }

def worker(match_id, category, waiting_queue, reserving_queue):
    t1 = threading.Thread(target=waiting_recorder_thread, args=(match_id, category, waiting_queue))
    t2 = threading.Thread(target=reserving_recorder_thread, args=(match_id, category, reserving_queue))
    t1.start()
    t2.start()
    


def log_selecting(match_id, category, username):
    request_id = f"{match_id}_{category}_{username}"
    with writing_request_lock:
        update_record(
            requests_db,
            request_feild,
            request_id,
            {"latest_status": "selecting"},
            id_field="request_id"
        )
    print(f"[Log] {username} marked as 'selecting' in {match_id}-{category}")
    status_record = status_object(request_id, "selecting")

    with writing_status_lock:
        add_record(
        requests_status_db,
            request_status_field,
            status_record
        )


def waiting_queue_manager(waiting_queues, reserving_queues):
    """Simulate receiving users into the waiting queue (e.g. from API/socket)."""
    print(f"[Init] Waiting queue manager started.")
    while True:
        # Simulated user input (replace with actual API/socket listener)
        data = connection_queue.get()
        print(f"[Input] Received data: {data}")
        username = data["user_name"]
        match_id = data["match_id"]
        category = data["category"]

        key = (match_id, category)

        with waiting_queues_lock:
            if key not in waiting_queues:
                waiting_queues[key] = Queue()
                reserving_queues[key] = Queue()
                waiting_queues_recorder[key] = Queue()
                print(f"[Init] Queues created for {match_id}-{category}")

                # Start a worker process per match-category pair
                worker_process = Process(
                    target=worker,
                    args=(match_id, category, waiting_queues_recorder[key], reserving_queues[key])
                )
                worker_process.start()
                worker_processes[key] = worker_process
                print(f"[Init] Worker started for {match_id}-{category}")

            # Add the user to the waiting queue
            waiting_queues[key].put(username)
            waiting_queues_recorder[key].put(username)
            print(f"[Input] User '{username}' added to waiting queue for {match_id}-{category}")


def reserving_queue_manager(waiting_queues, reserving_queues):
    # 1) Set up server socket once
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LISTEN_HOST, LISTEN_PORT))
    server.listen()
    print(f"[ReserveMgr] Listening on {LISTEN_HOST}:{LISTEN_PORT}…")

    while True:
        conn, addr = server.accept()
        print(f"[ReserveMgr] Connection from {addr}")
        match_id = None
        category = None
        done_user = None
        key = None
        try:
            with conn.makefile("r") as reader:
                for line in reader:
                    line = line.strip()
                    if not line:
                        continue

                    # parse the done-event
                    try:
                        msg = json.loads(line)
                        print(f"[ReserveMgr] Received: {msg}")
                        if "cmd" not in msg:
                            print(f"[ReserveMgr] Invalid JSON, skipping: {line!r}")
                            continue
                        if msg["cmd"] == "DONE":
                            
                            match_id  = msg["match_id"]
                            category  = msg["category"]
                            done_user = msg["user_name"]
                            key = (match_id, category)
                            reserving_queues[key].put(done_user)
                            key = (match_id, category)
                            print(f"[Done] Worker finished {done_user} for {match_id}-{category}")

                            update_record(
                                requests_db,
                                request_feild,
                                f"{match_id}_{category}_{done_user}",
                                {"latest_status": "done"},
                                id_field="request_id"
                            )
                        if msg["cmd"] == "NEXT":
                            # get the next user from any reserving queue
                            for key in waiting_queues:
                                if not waiting_queues[key].empty():
                                    print(f"[ReserveMgr] Found reserving queue for {key}")
                                    next_user = waiting_queues[key].get()
                                    match_id, category = key
                                    print(f"[ReserveMgr] '{next_user}' → selection for {match_id}-{category}")
                                    log_selecting(match_id, category, next_user)

                                    response = {
                                        "match_id": match_id,
                                        "category": category,
                                        "user_name": next_user
                                    }
                                    conn.sendall((json.dumps(response) + "\n").encode())
                                    break
                            else:
                                print(f"[ReserveMgr] no one reserving for {match_id}-{category}")

                    except (ValueError, KeyError):
                        print(f"[ReserveMgr] Invalid JSON, skipping: {line!r}")
                        continue

                    

                    # mark the user as done in the reserving queue
                    
                    next_user = None


                    # get next waiting user, if any
                    with waiting_queues_lock:
                        if key in waiting_queues and not waiting_queues[key].empty() and msg["cmd"] != "NEXT":
                            next_user = waiting_queues[key].get()
                            print(f"[Promote] '{next_user}' → selection for {match_id}-{category}")
                            log_selecting(match_id, category, next_user)

                            response = {
                            "match_id": match_id,
                            "category": category,
                            "user": next_user
                              }
                            conn.sendall((json.dumps(response) + "\n").encode())
                        elif msg["cmd"] != "NEXT":
                            pass
                        else:
                            print(f"[Promote] no one waiting for {match_id}-{category}")

                    # send back the next user (or null) as JSON
                    

        except Exception as e:
            print(f"[ReserveMgr] Connection error: {e}")
        finally:
            conn.close()
            print(f"[ReserveMgr] Disconnected {addr}, listening again…")

def waiting_recorder_thread(match_id, category, queue):
    while True:
        username = queue.get()
        request_id = f"{match_id}_{category}_{username}"
        
        request = request_object(request_id, username, match_id, category)
        with writing_request_lock:
            add_record(requests_db,
                    request_feild,
                    request)
        status = status_object(request_id, "waiting")
        with writing_status_lock:
            add_record(requests_status_db,
                    request_status_field,
                    status)

        print(f"[Record] {username} marked as 'waiting' in {match_id}-{category}")

def reserving_recorder_thread(match_id, category, queue):
    while True:
        username = queue.get()
        request_id = f"{match_id}_{category}_{username}"
        status = status_object(request_id, "done")
        with writing_status_lock:
            add_record(requests_status_db,
                    request_status_field,
                    status)  
        with writing_request_lock:
            update_record(requests_db,
                        request_feild,
                        request_id,
                        {"latest_status": "done"},
                        id_field="request_id")
            print(f"[LOG] {username} marked as 'done' in {match_id}-{category}")

        print(f"[Record] {username} marked as 'done' in {match_id}-{category}")
def main():
    multiprocessing.freeze_support()
    multiprocessing.set_start_method("spawn", force=True)
    # Initialize the queues and worker processes
    t_wait = threading.Thread(target=waiting_queue_manager, args=(waiting_queues, reserving_queues))
    t_res = threading.Thread(target=reserving_queue_manager, args=(reserving_queues,waiting_queues))

    t_wait.start()
    t_res.start()

    uvicorn.run("waiting:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()


