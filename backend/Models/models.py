
from pydantic import BaseModel


class RequestCreate(BaseModel):
    match_id: str = "1"
    user_name: str = "john"
    latest_status: str = "pending"
    timestamp: str = None

class RequestStatus(BaseModel):
    request_status_id: str
    request_id: str
    status: str
    timestamp: str = None