from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import httpx
import time
import logging
from typing import Dict, List

app = FastAPI()

connections: Dict[str, List] = {}
conn_lock = asyncio.Lock()
backend_lock = asyncio.Lock()   
seats_ep = "http://backend:8001/api/general/seats"  # Example backend endpoint
check_seats_ep = "http://backend:8001/api/general/check_seat"  # Example backend endpoint
reserve_seats_ep = "http://backend:8001/api/general/reserve_seat"  # Example backend endpoint




async def handle_reservation(websocket: WebSocket, data: dict):
    # check if requested seats are available
    match_id = data.get("match_id")
    category = data.get("category")
    user_name = data.get("user_name")
    seat_id = data.get("seat_id")
    timestamp = time.time()

    logging.info(f"Handling reservation for match: {match_id}, category: {category}, user: {user_name}, seat: {seat_id}")
    async with backend_lock:
        async with httpx.AsyncClient() as client:
            # Check availability
            response = await client.get(check_seats_ep+"/"+str(match_id)+"/"+str(category)+"/"+str(seat_id)) 
            logging.info(f"Check seat availability response: {response.json()}")
            if response.status_code == 200 and response.json().get("available"):
                # Reserve seats
                body = {"match_id": str(match_id), "user_name": str(user_name), "latest_status": "reserved", "timestamp": str(timestamp), "catagory": str(category), "seat_id": str(seat_id)}
                logging.info(f"Reserving seat with body: {body}")
                response = await client.post(reserve_seats_ep, json=body)
                # response = await client.post(reserve_seats_ep, json={"match_id": match_id, "category": category, "user_name": user_name, "seat_id": seat_id})
                if response.status_code == 200:
                    logging.info(f"Reserved {seat_id} seat for match: {match_id}, category: {category}, user: {user_name}")
                    await websocket.send_json({"stage": "2", "status": "success", "message": f"Reserved {seat_id} seat.", "seat_id": seat_id})
                    response = await client.get(seats_ep+"/"+str(match_id)+"/"+str(category))
                    if response.status_code == 200:
                        seats_status = response.json()
                        for conn in connections[str(match_id)+str(category)]:
                            if conn is not websocket:
                                await conn.send_json({"stage": "3", "seats_status": seats_status})
                else:
                    logging.info(f"Failed to reserve seat for match: {match_id}, category: {category}, user: {user_name}, seat: {seat_id}")
                    # await websocket.send_json({"status": "error", "message": "Failed to reserve seats.", "error": response.json()})
            else:
                logging.info(f"Seat: {seat_id} is not available for match: {match_id}, category: {category}, user: {user_name}")
                # get seats status
                response = await client.get(seats_ep+"/"+str(match_id)+"/"+str(category))
                if response.status_code == 200:
                    seats_status = response.json()
                    logging.info(f"Seats status: {seats_status}")
                    await websocket.send_json({"stage": "2", "status": "error", "message": "Seats not available.", "seats_status": seats_status})
                else:
                    logging.info("Failed to get seats status, response: ", response.json())

async def handle_init(websocket: WebSocket, data: dict):
    # get seats status
    match_id = data.get("match_id")
    category = data.get("category")
    user_name = data.get("user_name")

    async with conn_lock:
        connections[str(match_id)+str(category)].append(websocket)

    # send rest api request to get seats status
    # For now, we will just simulate it
    async with backend_lock:
        async with httpx.AsyncClient() as client:
            response = await client.get(seats_ep+"/"+str(match_id)+"/"+str(category))
            if response.status_code == 200:
                seats_status = response.json()
            else:
                seats_status = {"error": "Failed to get seats status"}
                logging.info("Failed to get seats status, response: ", response.json())
    logging.info(f"Initializing for match: {match_id}, category: {category}, user: {user_name}")
    # Respond back with seats status
    await websocket.send_json({"stage": "1", "status": "success", "seats_status": seats_status})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logging.info("omar")
    await websocket.accept()
    logging.info("Client connected")

    try:
        while True:
            data = await websocket.receive_json()
            logging.info(f"Received data: {data}")

            stage = data.get("stage")
            logging.info(f"Stage: {stage}")
            if stage == "2":
                # Handle reservation logic here
                # seat_id = data.get("seat_id")
                asyncio.create_task(handle_reservation(websocket, data))
        
            elif stage == "1":
                asyncio.create_task(handle_init(websocket, data))
            else:
                logging.info("Unknown stage")
                await websocket.send_json({"status": "error", "message": "Unknown stage."})

    except WebSocketDisconnect:
        logging.info("Client disconnected")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "reservation:app",      # "module:variable"
        host="0.0.0.0",
        port=8000,
        reload=True,        # hot-reload on file changes (dev only)
        log_level="info"
    )