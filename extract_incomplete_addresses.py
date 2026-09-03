import os
import sys
import csv
import re
from sqlalchemy import create_engine, text

# Fallback DB URL (Remote Railway database)
DEFAULT_DB_URL = "postgresql://postgres:JbEkstWQnhmNJQLMoXCefBntLFHsfSOx@crossover.proxy.rlwy.net:43302/railway"
db_url = os.environ.get("DATABASE_URL", DEFAULT_DB_URL)

print(f"Connecting to database: {db_url}")

def is_valid_address(address):
    if not address:
        return False
    
    # Normalize address: remove commas, replace multiple spaces with single space, convert to uppercase
    address_clean = address.replace(',', ' ').strip()
    address_clean = re.sub(r'\s+', ' ', address_clean)
    
    # 1. Must start with a number (digits)
    if not re.match(r'^\d+', address_clean):
        return False
        
    # 2. Must end with a ZIP code (5 digits or 5+4 digits)
    if not re.search(r'\d{5}(-\d{4})?$', address_clean):
        return False
        
    # 3. Must have a 2-letter state code before the ZIP code
    if not re.search(r'\b[A-Z]{2}\s+\d{5}(-\d{4})?$', address_clean):
        return False
        
    # 4. Check middle words (street and city name)
    # Strip starting number and trailing State + Zip
    middle = re.sub(r'^\d+\s*', '', address_clean)
    middle = re.sub(r'\s+[A-Z]{2}\s+\d{5}(-\d{4})?$', '', middle)
    middle_words = middle.strip().split()
    
    # We expect at least a street name (1 word) and a city name (1 word) -> total >= 2 words
    if len(middle_words) < 2:
        return False
        
    return True

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        print("Querying all properties...")
        # Querying essential fields from property_details
        sql = text("""
            SELECT id, property_id, parcel_id, address, county, state, amount_due, status, availability_status 
            FROM property_details
        """)
        rows = conn.execute(sql).fetchall()
        print(f"Total properties in database: {len(rows)}")
        
        incomplete_properties = []
        for r in rows:
            addr = r[3]
            if not is_valid_address(addr):
                incomplete_properties.append({
                    "id": r[0],
                    "property_id": r[1],
                    "parcel_id": r[2],
                    "address": addr,
                    "county": r[4],
                    "state": r[5],
                    "amount_due": r[6],
                    "status": r[7],
                    "availability_status": r[8]
                })
        
        print(f"Found {len(incomplete_properties)} properties with incomplete/non-standard addresses.")
        
        # Save to CSV
        output_csv = "../incomplete_addresses.csv"
        csv_columns = ["id", "property_id", "parcel_id", "address", "county", "state", "amount_due", "status", "availability_status"]
        
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=csv_columns)
            writer.writeheader()
            for prop in incomplete_properties:
                writer.writerow(prop)
                
        abs_csv_path = os.path.abspath(output_csv)
        print(f"Successfully saved incomplete properties to: {abs_csv_path}")

except Exception as e:
    print(f"Error executing script: {e}")
