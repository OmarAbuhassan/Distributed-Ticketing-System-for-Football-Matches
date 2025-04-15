from fastapi import APIRouter
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


