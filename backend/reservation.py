from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import httpx

app = FastAPI()

seats_queue = []
seats_lock = asyncio.Lock()
backend_lock = asyncio.Lock()   
seats_ep = "http://localhost:8001/seats"  # Example backend endpoint
check_seats_ep = "http://localhost:8001/check_seats"  # Example backend endpoint
reserve_seats_ep = "http://localhost:8001/reserve_seat"  # Example backend endpoint




async def handle_reservation(websocket: WebSocket, data: dict):
    # check if requested seats are available
    match_id = data.get("match_id")
    category = data.get("category")
    user_name = data.get("user_name")
    seat_id = data.get("seat_id", 0)

    async with backend_lock:
        async with httpx.AsyncClient() as client:
            # Check availability
            response = await client.post(check_seats_ep, json={"match_id": match_id, "category": category, "seat_id": seat_id})
            if response.status_code == 200 and response.json().get("available"):
                # Reserve seats
                response = await client.post(reserve_seats_ep, json={"match_id": match_id, "category": category, "user_name": user_name, "seat_id": seat_id})
                if response.status_code == 200:
                    print(f"Reserved {seat_id} seat for match: {match_id}, category: {category}, user: {user_name}")
                    await websocket.send_json({"status": "success", "message": f"Reserved {seat_id} seat."})
                else:
                    print(f"Failed to reserve seat for match: {match_id}, category: {category}, user: {user_name}, seat: {seat_id}")
                    # await websocket.send_json({"status": "error", "message": "Failed to reserve seats.", "error": response.json()})
            else:
                print(f"Seat: {seat_id} is not available for match: {match_id}, category: {category}, user: {user_name}")
                # get seats status
                response = await client.post(seats_ep+"/"+str(match_id)+"/"+str(category), json={"match_id": match_id, "category": category})
                if response.status_code == 200:
                    seats_status = response.json()
                    print(f"Seats status: {seats_status}")
                    await websocket.send_json({"status": "error", "message": "Seats not available.", "seats_status": seats_status})
                else:
                    print("Failed to get seats status, response: ", response.json())

async def handle_init(websocket: WebSocket, data: dict):
    # get seats status
    match_id = data.get("match_id")
    category = data.get("category")
    user_name = data.get("user_name")

    # send rest api request to get seats status
    # For now, we will just simulate it
    async with backend_lock:
        async with httpx.AsyncClient() as client:
            response = await client.post(seats_ep, json={"match_id": match_id, "category": category})
            if response.status_code == 200:
                seats_status = response.json()
            else:
                seats_status = {"error": "Failed to get seats status"}
                print("Failed to get seats status, response: ", response.json())
    print(f"Initializing for match: {match_id}, category: {category}, user: {user_name}")
    # Respond back with seats status
    await websocket.send_json({"status": "success", "seats_status": seats_status})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected")

    try:
        while True:
            data = await websocket.receive_json()
            print(f"Received data: {data}")

            stage = data.get("stage")
            if stage == "2":
                # Handle reservation logic here
                seat_id = data.get("seat_id")
                async with seats_lock:
                    if seat_id in seats_queue:
                        await websocket.send_json({"status": "error", "message": f"Seat already {seat_id} reserved."})
                    else:
                        seats_queue.append(seat_id)
                        asyncio.create_task(handle_reservation(websocket, data))
                
            elif stage == "1":
                asyncio.create_task(handle_init(websocket, data))
            else:
                print("Unknown stage")
                await websocket.send_json({"status": "error", "message": "Unknown stage."})

    except WebSocketDisconnect:
        print("Client disconnected")
