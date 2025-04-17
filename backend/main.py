from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import uvicorn
from db.csv_api import *
from routes import general, reservation
from routes.reservation import process_reservations
from fastapi.middleware.cors import CORSMiddleware
import uuid
import time

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
app = FastAPI()
# Include routers
app.include_router(general.router, prefix="/api/general", tags=["general"])
app.include_router(reservation.router, prefix="/api/reservation", tags=["reservation"])


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for clients to submit reservations.
    """
    await websocket.accept()
    print("Client connected")
    
    try:
        while True:
            try:
                # Receive reservation data from the client
                reservation = await websocket.receive_json()
                stage = reservation.get("stage")
            except Exception as e:
                await websocket.send_json(
                    {"error": "Invalid JSON format, add 'stage':'1' or 'stage':'2'"}
                )
                continue

            if stage == "1":
                try:
                    request_id = str(uuid.uuid1())
                    reservation_id = str(uuid.uuid1())
                    user_name = reservation.get("user_name")
                    match_id = reservation.get("match_id")
                except Exception as e:
                    await websocket.send_json({"error": "Invalid JSON format"})
                    continue

                match = search_records(matches_db, {"match_id": match_id})
                if not match:
                    await websocket.send_json({"error": "Match not found"})
                    continue

                # Update the status to 'In_Queue' and add to the queue
                add_record(
                    requests_status_db,
                    requests_status_fields,
                    {
                        "request_id": request_id,
                        "reservation_id": reservation_id,
                        "status": "In_Queue",
                        "timestamp": str(int(time.time())),
                    },
                )
                add_record(
                    reservations_db,
                    reservations_fields,
                    {
                        "reservation_id": reservation_id,
                        "user_name": user_name,
                        "match_id": match_id,
                        "seat_id": None,
                    },
                )
                await websocket.send_json(
                    {
                        "status": "queued",
                        "reservation_id": reservation_id,
                        "request_id": request_id,
                    }
                )
                
                #########################################################################
                # Abdulmajeed's function should be called here
                # update the status to 'Selecting_seat'
                
                add_record(
                    requests_status_db,
                    requests_status_fields,
                    {
                        "request_id": reservation_id,
                        "reservation_id": reservation_id,
                        "status": "Selecting_seat",
                        "timestamp": str(int(time.time())),
                    },
                )
                # inform the user that he can select a seat
                await websocket.send_json(
                    {
                        "status": "select_seat",
                        "reservation_id": reservation_id,
                        "request_id": request_id,
                    }
                )

                # Set the timeout for selecting a seat (60 seconds)
                try:
                    # Wait for the user to select a seat or timeout after 60 seconds
                    seat_selection = await asyncio.wait_for(websocket.receive_json(), timeout=60)

                    reservation_id = seat_selection.get("reservation_id")
                    seat_id = seat_selection.get("seat_id")

                    # Check if the reservation exists
                    reservation_record = search_records(
                        reservations_db, {"reservation_id": reservation_id}
                    )
                    if not reservation_record:
                        await websocket.send_json({"error": "Reservation not found"})
                        continue

                    # Check if the seat is available
                    seat_record = search_records(
                        seats_db, {"seat_id": seat_id, "occupied": "False"}
                    )
                    if not seat_record:
                        await websocket.send_json({"error": "Seat not available"})
                        continue
                    

                    # Update the reservation with the selected seat
                    update_record(
                        reservations_db,
                        reservations_fields,
                        reservation_id,
                        {"seat_id": seat_id},
                        "reservation_id"
                    )
                    # Update the seat status to occupied
                    update_record(
                        seats_db,
                        seats_fields,
                        seat_id,
                        {"occupied": "True"},
                        "seat_id"
                    )
                    # Update the status to 'Reserved'
                    update_record(
                        requests_status_db,
                        requests_status_fields,
                        reservation_id,
                        {"status": "Reserved"},
                        "reservation_id"
                    )

                except asyncio.TimeoutError:
                    # If the user does not select a seat within 60 seconds
                    await websocket.send_json({"error": "You were disconnected due to inactivity."})
                    await websocket.close()
                    print("Client disconnected due to inactivity.")
                    break  # Exit the loop and close the connection

            elif stage == "2":
                try:
                    reservation_id = reservation.get("reservation_id")
                    seat_id = reservation.get("seat_id")
                except Exception as e:
                    await websocket.send_json({"error": "Invalid JSON format"})
                    continue

                # Check if the reservation exists
                reservation_record = search_records(
                    reservations_db, {"reservation_id": reservation_id}
                )
                if not reservation_record:
                    await websocket.send_json({"error": "Reservation not found"})
                    continue


                #########################################################################
                # Abdulmajeed's function should be called here

                # Check if the seat is available
                seat_record = search_records(
                    seats_db, {"seat_id": seat_id, "occupied": "False"}
                )
                if not seat_record:
                    await websocket.send_json({"error": "Seat not available"})
                    continue

                # if the seat is available, update the reservation

                # Update the reservation with the selected seat
                update_record(
                    reservations_db,
                    reservations_fields,
                    reservation_id,
                    {"seat_id": seat_id},
                    "reservation_id"
                )
                # Update the seat status to occupied
                update_record(
                    seats_db,
                    seats_fields,
                    seat_id,
                    {"occupied": "True"},
                    "seat_id"
                )
                # Update the status to 'Reserved'
                update_record(
                    requests_status_db,
                    requests_status_fields,
                    reservation_id,
                    {"status": "Reserved"},
                    "reservation_id"
                )


            else:
                await websocket.send_json(
                    {"error": "Invalid stage, add 'stage':'1' or 'stage':'2'"}
                )
                continue


    except WebSocketDisconnect:
        print("Client disconnected")


uvicorn.run(app, host="0.0.0.0", port=8001)
