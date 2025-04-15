from db.csv_api import *

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


print("Ticket Reservation System Server is running...")
filters = {'seat_id': '1', 'catagory': 'VIP'}
seats_db = 'db/seats.csv'
print(search_records(seats_db, filters))