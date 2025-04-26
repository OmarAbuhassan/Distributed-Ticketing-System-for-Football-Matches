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



