from csv_api import *
from schema import *


initialize_db(matches_db, matches_fields)
initialize_db(seats_db, seats_fields)
initialize_db(reservations_db, reservations_fields)
initialize_db(requests_status_db, requests_status_fields)
initialize_db(request_db,request_fields)



add_record(matches_db, matches_fields, {'match_id': '1', 'team1_name': 'Alhilal', 'team2_name': 'Al-Ahli', 'number_of_seats': '160'})
add_record(matches_db, matches_fields, {'match_id': '2', 'team1_name': 'Al-Nasr', 'team2_name': 'Al-Ittihad', 'number_of_seats': '160'})
add_record(matches_db, matches_fields, {'match_id': '3', 'team1_name': 'Al-Faisaly', 'team2_name': 'Al-Taawoun', 'number_of_seats': '160'})


seat_id_counter = 1  # Start global seat ID counter

for match in read_all(matches_db):
    match_id = match['match_id']
    # number_of_seats = int(match['number_of_seats'])
    number_of_seats = 160

    vip_seats = int(number_of_seats * 0.25)
    regular_seats = int(number_of_seats * 0.25)
    economy_seats = number_of_seats - vip_seats - regular_seats

    for _ in range(vip_seats):
        add_record(seats_db, seats_fields, {
            'seat_id': str(seat_id_counter),
            'seat_name': f'VIP-{_}',
            'match_id': match_id,
            'catagory': 'VIP',
            'status': 'available'
        })
        seat_id_counter += 1

    for _ in range(regular_seats):
        add_record(seats_db, seats_fields, {
            'seat_id': str(seat_id_counter),
            'seat_name': f'Premium-{_}',
            'match_id': match_id,
            'catagory': 'Premium',
            'status': 'available'
        })
        seat_id_counter += 1

    for _ in range(economy_seats):
        add_record(seats_db, seats_fields, {
            'seat_id': str(seat_id_counter),
            'seat_name': f'Standard-{_}',
            'match_id': match_id,
            'catagory': 'Premium',
            'status': 'available'
        })
        seat_id_counter += 1

