from db.csv_api import *

CATAGORY = ['VIP', 'Regular', 'Economy']
STATUS = ['In_Queue', 'Selecting_seat', 'Reserved', 'Cancelled']

matches_db = 'db/matches.csv'
matches_fields = ['match_id', 'team1_name', 'team2_name', 'number_of_seats']
initialize_db(matches_db, matches_fields)

seats_db = 'db/seats.csv'
seats_fields = ['seat_id', 'match_id', 'catagory', 'occupied'] 
initialize_db(seats_db, seats_fields)

reservations_db = 'db/reservations.csv'
reservations_fields = ['reservation_id', 'user_name', 'match_id', 'seat_id']
initialize_db(reservations_db, reservations_fields)

requests_status_db = 'db/requests_status.csv'
requests_status_fields = ['request_id', 'reservation_id', 'status', "timestamp"]
initialize_db(requests_status_db, requests_status_fields)



add_record(matches_db, matches_fields, {'match_id': '1', 'team1_name': 'Alhilal', 'team2_name': 'Al-Ahli', 'number_of_seats': '10'})
add_record(matches_db, matches_fields, {'match_id': '2', 'team1_name': 'Al-Nasr', 'team2_name': 'Al-Ittihad', 'number_of_seats': '20'})
add_record(matches_db, matches_fields, {'match_id': '3', 'team1_name': 'Al-Faisaly', 'team2_name': 'Al-Taawoun', 'number_of_seats': '15'})


seat_id_counter = 1  # Start global seat ID counter

for match in read_all(matches_db):
    match_id = match['match_id']
    number_of_seats = int(match['number_of_seats'])

    vip_seats = int(number_of_seats * 0.15)
    regular_seats = int(number_of_seats * 0.25)
    economy_seats = number_of_seats - vip_seats - regular_seats

    for _ in range(vip_seats):
        add_record(seats_db, seats_fields, {
            'seat_id': str(seat_id_counter),
            'match_id': match_id,
            'catagory': 'VIP',
            'occupied': 'False'
        })
        seat_id_counter += 1

    for _ in range(regular_seats):
        add_record(seats_db, seats_fields, {
            'seat_id': str(seat_id_counter),
            'match_id': match_id,
            'catagory': 'Regular',
            'occupied': 'False'
        })
        seat_id_counter += 1

    for _ in range(economy_seats):
        add_record(seats_db, seats_fields, {
            'seat_id': str(seat_id_counter),
            'match_id': match_id,
            'catagory': 'Economy',
            'occupied': 'False'
        })
        seat_id_counter += 1

