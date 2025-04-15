import csv
import os
from typing import List, Dict, Optional

# Initialize CSV file with headers if it doesn't exist
def initialize_db(file_path: str, fieldnames: List[str]):
        with open(file_path, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

# CREATE
def add_record(file_path: str, fieldnames: List[str], data: Dict):
    with open(file_path, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writerow(data)

# READ ALL
def read_all(file_path: str) -> List[Dict]:
    if not os.path.exists(file_path):
        return []
    with open(file_path, mode='r') as file:
        reader = csv.DictReader(file)
        return list(reader)

# READ BY ID
def get_record(file_path: str, record_id: str, id_field: str = 'id') -> Optional[Dict]:
    for row in read_all(file_path):
        if row[id_field] == str(record_id):
            return row
    return None

# UPDATE BY ID
def update_record(file_path: str, fieldnames: List[str], record_id: str, updated_data: Dict, id_field: str = 'id'):
    records = read_all(file_path)
    with open(file_path, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            if row[id_field] == str(record_id):
                row.update(updated_data)
            writer.writerow(row)

# DELETE BY ID
def delete_record(file_path: str, fieldnames: List[str], record_id: str, id_field: str = 'id'):
    records = read_all(file_path)
    with open(file_path, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            if row[id_field] != str(record_id):
                writer.writerow(row)


# SEARCH with filters
def search_records(file_path: str, filters: Dict[str, str]) -> List[Dict]:
    """
    Returns a list of records that match all key-value pairs in the `filters` dict.
    Example oqupied seats:
    filter = {'occupied': 'True'}
    search_records(seats_db, filter)
    """
    results = []
    for row in read_all(file_path):
        if all(str(row.get(k, '')).strip() == str(v).strip() for k, v in filters.items()):
            results.append(row)
    return results
