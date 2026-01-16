"""Geocode theater addresses to get lat/long coordinates"""
import sqlite3
from geopy.geocoders import Nominatim
import time

# Connect to database
conn = sqlite3.connect('./database/indie_cinema.db')
cursor = conn.cursor()

# Create geocoder
geolocator = Nominatim(user_agent="indie-cinema-scraper")

# Get theaters without coordinates
cursor.execute("""
    SELECT id, name, address 
    FROM theaters 
    WHERE latitude IS NULL OR longitude IS NULL
""")

theaters = cursor.fetchall()

print(f"Geocoding {len(theaters)} theaters...")
print("="*60)

for theater_id, name, address in theaters:
    print(f"\n{name}")
    print(f"  Address: {address}")
    
    try:
        # Try full address first
        location = geolocator.geocode(address)
    
        # If that fails, try without suite/unit number
        if not location and '#' in address:
            simplified = address.split('#')[0].strip()
            print(f"  Retrying with: {simplified}")
            location = geolocator.geocode(simplified)
        
        if location:
            cursor.execute("""
                UPDATE theaters 
                SET latitude = ?, longitude = ?
                WHERE id = ?
            """, (location.latitude, location.longitude, theater_id))
            conn.commit()
            
            print(f"  ✅ Coordinates: ({location.latitude}, {location.longitude})")
        else:
            print(f"  ❌ Could not geocode address")
        
        # Be respectful of rate limits (1 request per second)
        time.sleep(1)
    
    except Exception as e:
        print(f"  ❌ Error: {e}")

print("\n" + "="*60)
print("✅ Geocoding complete!")

conn.close()