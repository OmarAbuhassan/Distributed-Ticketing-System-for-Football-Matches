import datetime
import uuid
from fastapi import APIRouter
from Models.models import RequestCreate, RequestStatus
from db.csv_api import *
from db.schema import *


router = APIRouter()

@router.get("/matches")
def get_matches():
    """
    Get all matches
    """
    return read_all(matches_db)

@router.get("/catagory")
def get_catagory():
    """
    Get all catagories
    """
    return CATAGORY

@router.get("/seats/{match_id}/{catagory}")
def get_seats(match_id: str, catagory: str):
    """
    input:
    {
        "match_id": "1",
        "catagory": "VIP"
    }
    catagory: VIP, Regular, Economy
    Get all seats for a match
    """
    # Check if the match exists
    match = search_records(matches_db, {'match_id': match_id})
    if not match:
        return {"error": "Match not found"}

    # Check if the catagory is valid
    if catagory not in CATAGORY:
        return {"error": "Invalid catagory"}

    # Get all seats for the match
    filter = {'match_id': match_id, 'catagory': catagory}
    seats = search_records(seats_db, filter)
    print(seats)
    
    return seats

@router.post("/requests")
def create_request(requestCreate: RequestCreate):

    """
    Create a new request
    Input:
    {
        "match_id": "1",
        "user_name": "john",
        "latest_status": "pending"
    }
    """
    request_id = str(uuid.uuid1())
    request = {
        "request_id": request_id,
        "match_id": requestCreate.match_id,
        "user_name": requestCreate.user_name,
        "latest_status": requestCreate.latest_status
    }
    
    request_status = {
        "requests_status_id": str(uuid.uuid1()),
        "request_id": request_id,
        "status": requestCreate.latest_status,
        "timestamp": requestCreate.timestamp if requestCreate.timestamp else str(datetime.datetime.now())
    }
    
    add_record(request_db, request_fields, request)
    add_record(requests_status_db, requests_status_fields, request_status)
    
    return {"request_id": request_id}


@router.post("/request_status")
def create_request_status(requestStatus: RequestStatus):
    """
    Add a new status for a request
    Input:
    {
        "request_id": "1234-5678",
        "status": "approved",
        "timestamp": "2023-05-20T10:30:00"
    }
    """
    request_status = {
        "requests_status_id": str(uuid.uuid1()),
        "request_id": requestStatus.request_id,
        "status": requestStatus.status,
        "timestamp": requestStatus.timestamp
    }
    
    add_record(requests_status_db, requests_status_fields, request_status)
    return request_status
@router.get("/check_seat/{match_id}/{catagory}/{seat_id}")
def check_seat(match_id: str, catagory: str, seat_id: int):
    """
    Check if a seat is available for a match
    Input:
    {
        "match_id": "1",
        "catagory": "VIP",
        "seat_id": 1
    }
    catagory: VIP, Regular, Economy
    """
    # Check if the match exists
    match = search_records(matches_db, {'match_id': match_id})
    if not match:
        return {"error": "Match not found"}

    # Check if the catagory is valid
    if catagory not in CATAGORY:
        return {"error": "Invalid catagory"}

    # Check if the seat is available for the match
    filter = {'match_id': match_id, 'catagory': catagory, 'seat_id': seat_id}
    seat = search_records(seats_db, filter)
    
    if seat and seat[0]['status'] == 'available':
        return {"available": True}
    else:
        return {"available": False}

@router.post("/reserve_seat")
def reserve_seat(requestCreate: RequestCreate):
    """
    Reserve a seat for a match
    Input:
    {
        "match_id": "1",
        "catagory": "VIP",
        "seat_id": 1,
        "user_name": "john",
    }
    catagory: VIP, Regular, Economy
    """
    # Check if the match exists
    print(requestCreate)
    match = search_records(matches_db, {'match_id': requestCreate.match_id})
    if not match:
        return {"error": "Match not found"}

    # Check if the catagory is valid
    if requestCreate.catagory not in CATAGORY:
        return {"error": "Invalid catagory"}

    # Check if the seat is available for the match
    filter = {'match_id': requestCreate.match_id, 'catagory': requestCreate.catagory, 'seat_id': requestCreate.seat_id}
    seat = search_records(seats_db, filter)
    
    if seat and seat[0]['status'] == 'available':
        # update_record(seats_db, filter, requestCreate.seat_id,{'status': 'reserved'},id_field='seat_id')
        update_record(
                    seats_db,
                    seats_fields,
                    requestCreate.seat_id,
                    {'status': 'reserved'},
                    "seat_id"
                )
        # add reservation record
        reservation_id = str(uuid.uuid1())
        reservation = {
            "reservation_id": reservation_id,
            "match_id": requestCreate.match_id,
            "seat_id": requestCreate.seat_id,
            "user_name": requestCreate.user_name
        }
        add_record(reservations_db, reservations_fields, reservation)
        return {"status": "success", "message": f"Reserved seat {requestCreate.seat_id} for match {requestCreate.match_id}"}
    else:
        return {"status": "error", "message": f"Seat {requestCreate.seat_id} is not available for match {requestCreate.match_id}"}


@router.get("/reservations")
def get_reservations():
    """
    Get all reservations
    """
    return read_all(reservations_db)

@router.post("/check_in")
def check_in(request: dict):
    """
    Check in a reservation at the stadium
    Input:
    {
        "reservation_id": "uuid",
        "status": "checked_in",
        "timestamp": "2024-04-30T10:00:00Z"
    }
    """
    print(request)
    # Get the reservation
    reservation = search_records(reservations_db, {"reservation_id": request["reservation_id"]})
    if not reservation:
        return {"status": "error", "message": "Reservation not found"}
    
    # Get all requests by this user for this match
    request_records = search_records(
        request_db, 
        {
            "user_name": reservation[0]["user_name"],
            "match_id": reservation[0]["match_id"]
        }
    )

    if not request_records:
        return {"status": "error", "message": "No requests found for this reservation"}

    # Find the specific request that matches this seat_id
    matching_request = None
    for req in request_records:
        # Get the reservation for this request to check the seat
        req_reservation = search_records(reservations_db, {
            "user_name": req["user_name"],
            "match_id": req["match_id"],
            "seat_id": reservation[0]["seat_id"]  # Match the specific seat
        })
        if req_reservation:
            matching_request = req
            break
    print("matching_request", matching_request)
    if not matching_request:
        return {"status": "error", "message": "No request found for this reservation"}

    # Check if already checked in - only status we need to verify
    if matching_request["latest_status"] == "checked_in" or matching_request["latest_status"] == "checked_out":
        return {"status": "error", "message": "This reservation is already checked in"}

    # Create a new status record for check-in
    status_record = {
        "requests_status_id": str(uuid.uuid1()),
        "request_id": matching_request["request_id"],
        "status": request["status"],
        "timestamp": request["timestamp"]
    }
    # Update request's latest_status
    update_record(
        request_db,
        request_fields,
        matching_request["request_id"],
        {"latest_status": "checked_in"},
        "request_id"
    )
    
    add_record(requests_status_db, requests_status_fields, status_record)
    return {"status": "success", "message": "Check-in recorded successfully"}

@router.post("/check_out")
def check_out(request: dict):
    """
    Check out a reservation from the stadium
    Input:
    {
        "reservation_id": "uuid",
        "status": "checked_out",
        "timestamp": "2024-04-30T10:00:00Z"
    }
    """
    # Get the reservation
    reservation = search_records(reservations_db, {"reservation_id": request["reservation_id"]})
    if not reservation:
        return {"status": "error", "message": "Reservation not found"}
    
    # Get all requests by this user for this match
    request_records = search_records(
        request_db, 
        {
            "user_name": reservation[0]["user_name"],
            "match_id": reservation[0]["match_id"]
        }
    )

    if not request_records:
        return {"status": "error", "message": "No requests found for this reservation"}

    # Find the specific request that matches this seat_id
    matching_request = None
    for req in request_records:
        # Get the reservation for this request to check the seat
        req_reservation = search_records(reservations_db, {
            "user_name": req["user_name"],
            "match_id": req["match_id"],
            "seat_id": reservation[0]["seat_id"]  # Match the specific seat
        })
        if req_reservation:
            matching_request = req
            break

    if not matching_request:
        return {"status": "error", "message": "No request found for this reservation"}

    # Check the status transitions
    if matching_request["latest_status"] == "checked_out":
        return {"status": "error", "message": "This reservation is already checked out"}
    elif matching_request["latest_status"] != "checked_in":
        return {"status": "error", "message": "This reservation must be checked in before it can be checked out"}

    # Create a new status record for check-out
    status_record = {
        "requests_status_id": str(uuid.uuid1()),
        "request_id": matching_request["request_id"],
        "status": request["status"],
        "timestamp": request["timestamp"]
    }
    
    # Update request's latest_status
    update_record(
        request_db,
        request_fields,
        matching_request["request_id"],
        {"latest_status": "checked_out"},
        "request_id"
    )
    
    add_record(requests_status_db, requests_status_fields, status_record)
    return {"status": "success", "message": "Check-out recorded successfully"}




