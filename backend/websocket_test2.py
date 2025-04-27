from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import uvicorn
from db.csv_api import *
from routes import general, reservation
# from routes.reservation import process_reservations
from fastapi.middleware.cors import CORSMiddleware
import uuid
import time
from collections import deque

# add arguments to the script
def parse_args():
    import argparse

    parser = argparse.ArgumentParser(description="Ticket Reservation System Server")
    # init the db
    parser.add_argument("--init", action="store_true", help="Initialize the database")
    return parser.parse_args()

args = parse_args()

# Initialize the database if --init argument is passed
if args.init:
    from db.init import *

    print("Database initialized and sample data added.")


# Initialize FastAPI
app = FastAPI(debug=True)
from fastapi.middleware.cors import CORSMiddleware


# Include routers
app.include_router(general.router, prefix="/api/general", tags=["general"])
app.include_router(reservation.router, prefix="/api/reservation", tags=["reservation"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # or ["http://localhost:5173"] to restrict
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Create a queue to store active WebSocket connections for FCFS
connection_queue = deque()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for clients to submit reservations.
    """
    await websocket.accept()
    while True:
        try:
            # Wait for a message from the client
            data = await websocket.receive_json()
            
           

            # Add 5 seconds delay
            if data.get("stage") == "1":
                print(f"Received data from: {data}")
                await websocket.send_json({"stage": "1", "status": "success"})

            elif data.get("stage") == "2":
                print(f"Received data from: {data}")
                await websocket.send_json({"stage": "2", "status": "success"})
            else:
                await websocket.send_json({"error": "Invalid stage, please use 'stage': '1' or 'stage': '2'"})
                continue



            # # Check if the message contains 'stage' key
            # if 'stage' not in data:
            #     await websocket.send_json({"error": "Invalid JSON format, add 'stage':'1' or 'stage':'2'"})
            #     continue

            # # Add the connection to the queue
            # connection_queue.append(websocket)

            # # Process the reservation request based on the stage
            # if data['stage'] == '1':
            #     # Process stage 1: Entering the queue
            #     await websocket.send_json({"message": "You have entered the queue."})
            #     print(f"Client  entered the queue.")

            # elif data['stage'] == '2':
            #     # Process stage 2: Reservation processing
            #     await websocket.send_json({"message": "Processing your reservation."})
            #     print(f"Client is processing reservation.")

        except WebSocketDisconnect:
            print(f"Client disconnected.")
            break


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)