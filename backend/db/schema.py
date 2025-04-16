CATAGORY = ['VIP', 'Regular', 'Economy']
STATUS = ['In_Queue', 'Selecting_seat', 'Reserved', 'Cancelled']

matches_db = 'db/matches.csv'
matches_fields = ['match_id', 'team1_name', 'team2_name', 'number_of_seats']

seats_db = 'db/seats.csv'
seats_fields = ['seat_id', 'match_id', 'catagory', 'occupied'] 

reservations_db = 'db/reservations.csv'
reservations_fields = ['reservation_id', 'user_name', 'match_id', 'seat_id']

requests_status_db = 'db/requests_status.csv'
requests_status_fields = ['requests_status_id','request_id', 'status', "timestamp"]

request_db = 'db/requests.csv'
request_fields = ['request_id', 'user_name', 'match_id', 'catagory','latest_status']