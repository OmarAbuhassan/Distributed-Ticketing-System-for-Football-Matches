from fastapi import APIRouter
from db.csv_api import *
from db.schema import *


router = APIRouter()

# @router.post("/reserve")
# def reserve_seat(reservation: dict):
#     """
#     input:
#     {
#         "reservation_id": "1",
#         "user_name": "John Doe",
#         "match_id": "1"
#     }
#     Reserve a seat
#     """
#     # Check if the match exists
#     match = search_records(matches_db, matches_fields, reservation['match_id'])
#     if not match:
#         return {"error": "Match not found"}

#     # Create a reservation
#     reservation['seat_id'] = "none"
#     add_record(reservations_db, reservations_fields, reservation)
    
#     return {"message": "Seat reserved successfully"}

# @router.post("/enter_queue")
# def enter_queue(reservation: dict):
#     """
#     input:
#     {
#         "reservation_id": "1",
#         "user_name": "John Doe",
#         "match_id": "1"
#     }
#     Enter the queue for a match
#     """
#     # Check if the match exists
#     match = search_records(matches_db, matches_fields, reservation['match_id'])
#     if not match:
#         return {"error": "Match not found"}

#     # Check if the reservation exists
#     reservation_record = search_records(reservations_db, reservations_fields, reservation['reservation_id'])
#     if not reservation_record:
#         return {"error": "Reservation not found"}

#     # Update the status to In_Queue
#     reservation_record['status'] = 'In_Queue'
#     update_record(reservations_db, reservations_fields, reservation['reservation_id'], reservation_record)

#     return {"message": "Entered queue successfully"}