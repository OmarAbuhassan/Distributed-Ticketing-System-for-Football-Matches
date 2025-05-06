from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
import asyncio
import httpx
import logging
from typing import Dict, List
from datetime import datetime
import statistics
from db.csv_api import *
from db.schema import *

app = FastAPI()

# Store active WebSocket connections
connections: List[WebSocket] = []
conn_lock = asyncio.Lock()

# Cache for dashboard stats
stats_cache = {
    "queue_stats": {},
    "checkin_stats": {}
}

async def get_queue_stats():
    """Get statistics about queues for each match and category"""
    matches = read_all(matches_db)
    categories = ["vip", "premium", "standard"]
    stats = {}
    
    for match in matches:
        match_id = match["match_id"]
        stats[match_id] = {}
        for category in categories:
            # Get requests in Waiting status
            waiting_requests = search_records(request_db, {
                "match_id": match_id,
                "catagory": category.upper(),
                "latest_status": "Waiting"
            })
            stats[match_id][category] = {
                "waiting_count": len(waiting_requests)
            }
            
            # Calculate average waiting time
            if waiting_requests:
                waiting_times = []
                for req in waiting_requests:
                    status_records = search_records(requests_status_db, {
                        "request_id": req["request_id"],
                        "status": "Waiting"
                    })
                    if status_records:
                        timestamp = datetime.strptime(status_records[0]["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
                        waiting_time = (datetime.utcnow() - timestamp).total_seconds() / 60  # in minutes
                        waiting_times.append(waiting_time)
                if waiting_times:
                    stats[match_id][category]["avg_waiting_time"] = statistics.mean(waiting_times)
                else:
                    stats[match_id][category]["avg_waiting_time"] = 0
            else:
                stats[match_id][category]["avg_waiting_time"] = 0
    
    return stats

async def get_checkin_stats():
    """Get statistics about checked-in users and average check-in duration"""
    matches = read_all(matches_db)
    stats = {}
    
    for match in matches:
        match_id = match["match_id"]
        stats[match_id] = {}
        
        # Get currently checked in users
        checked_in_requests = search_records(request_db, {
            "match_id": match_id,
            "latest_status": "checked_in"
        })
        stats[match_id]["checked_in_count"] = len(checked_in_requests)
        
        # Calculate average check-in duration for completed check-ins
        checkout_durations = []
        completed_checkouts = search_records(request_db, {
            "match_id": match_id,
            "latest_status": "checked_out"
        })
        
        for req in completed_checkouts:
            status_records = search_records(requests_status_db, {
                "request_id": req["request_id"]
            })
            
            checkin_time = None
            checkout_time = None
            
            for record in status_records:
                if record["status"] == "checked_in":
                    checkin_time = datetime.strptime(record["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ")
                elif record["status"] == "checked_out":
                    checkout_time = datetime.strptime(record["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ")
            
            if checkin_time and checkout_time:
                duration = (checkout_time - checkin_time).total_seconds() / 60  # in minutes
                checkout_durations.append(duration)
        
        if checkout_durations:
            stats[match_id]["avg_checkin_duration"] = statistics.mean(checkout_durations)
        else:
            stats[match_id]["avg_checkin_duration"] = 0
    
    return stats

async def broadcast_stats():
    """Broadcast current stats to all connected clients"""
    dashboard_data = {
        "queue_stats": stats_cache["queue_stats"],
        "checkin_stats": stats_cache["checkin_stats"]
    }
    
    for connection in connections[:]:  # Use a slice copy to avoid modification during iteration
        try:
            await connection.send_json(dashboard_data)
        except:
            # Remove dead connections
            connections.remove(connection)

@app.post("/events")
async def handle_events(request: Request):
    """Handle real-time events from other services"""
    data = await request.json()
    event_type = data["type"]
    event_data = data["data"]
    
    if event_type == "queue_update":
        match_id = event_data["match_id"]
        category = event_data["category"]
        if match_id not in stats_cache["queue_stats"]:
            stats_cache["queue_stats"][match_id] = {}
        if category not in stats_cache["queue_stats"][match_id]:
            stats_cache["queue_stats"][match_id][category] = {}
            
        stats_cache["queue_stats"][match_id][category]["waiting_count"] = event_data["queue_length"]
        # Update average waiting time
        queue_stats = await get_queue_stats()
        if match_id in queue_stats and category in queue_stats[match_id]:
            stats_cache["queue_stats"][match_id][category]["avg_waiting_time"] = queue_stats[match_id][category]["avg_waiting_time"]
    
    elif event_type in ["check_in", "check_out"]:
        # Update check-in stats
        checkin_stats = await get_checkin_stats()
        stats_cache["checkin_stats"] = checkin_stats
    
    # Broadcast updated stats to all connected clients
    await broadcast_stats()
    
    return {"status": "success"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Initialize cache if empty
    if not stats_cache["queue_stats"]:
        stats_cache["queue_stats"] = await get_queue_stats()
    if not stats_cache["checkin_stats"]:
        stats_cache["checkin_stats"] = await get_checkin_stats()
    
    async with conn_lock:
        connections.append(websocket)
    
    try:
        # Send initial stats
        await websocket.send_json({
            "queue_stats": stats_cache["queue_stats"],
            "checkin_stats": stats_cache["checkin_stats"]
        })
        
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "dashboard:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )