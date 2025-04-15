from fastapi import FastAPI
import uvicorn
from db.csv_api import *
from routes import general, reservation

# add arguments to the script
def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description='Ticket Reservation System Server')
    # init the db
    parser.add_argument('--init', action='store_true', help='Initialize the database')
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
uvicorn.run(app, host="0.0.0.0", port=8001)
