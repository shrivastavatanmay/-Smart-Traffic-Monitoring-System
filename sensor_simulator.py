import os
import time
import random
import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load credentials
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Missing SUPABASE_URL or SUPABASE_KEY in .env")
    exit(1)

# Initialize Supabase client
supabase: Client = create_client(url, key)

WEATHER_CONDITIONS = ["clear", "clear", "clear", "cloudy", "rain", "fog"]

def get_active_sensors():
    response = supabase.table("sensors").select("id").eq("status", "active").execute()
    return [sensor["id"] for sensor in response.data]

def simulate_traffic():
    print("Starting traffic simulation... (Press Ctrl+C to stop)")
    
    while True:
        try:
            active_sensors = get_active_sensors()
            
            if not active_sensors:
                print("No active sensors found. Waiting 10s...")
                time.sleep(10)
                continue
            
            new_records = []
            
            for sensor_id in active_sensors:
                # Add some randomness to time
                current_time = datetime.datetime.now(datetime.timezone.utc)
                hour = current_time.hour
                
                # Traffic logic based on time
                is_rush_hour = (7 <= hour <= 9) or (16 <= hour <= 19)
                is_night = (23 <= hour <= 24) or (0 <= hour <= 5)
                
                if is_rush_hour:
                    base_vehicles = random.randint(15, 30)
                    base_speed = random.randint(10, 40)
                elif is_night:
                    base_vehicles = random.randint(1, 5)
                    base_speed = random.randint(60, 90)
                else:
                    base_vehicles = random.randint(5, 15)
                    base_speed = random.randint(40, 70)
                    
                # Calculate metrics
                weather = random.choice(WEATHER_CONDITIONS)
                if weather in ["rain", "fog"]:
                    base_speed = max(10, base_speed - 15)
                    
                density = min(100, int((base_vehicles / 30) * 100))
                if base_speed < 20 and base_vehicles > 10:
                    density = min(100, density + 20)
                
                record = {
                    "sensor_id": sensor_id,
                    "timestamp": current_time.isoformat(),
                    "vehicle_count": base_vehicles,
                    "avg_speed_kmh": base_speed,
                    "congestion_density_pct": density,
                    "weather_condition": weather
                }
                new_records.append(record)
            
            # Insert batch into Supabase
            supabase.table("traffic_records").insert(new_records).execute()
            print(f"[{current_time.strftime('%H:%M:%S')}] Inserted {len(new_records)} live traffic records.")
            
            # Sleep for a few seconds before generating the next batch
            time.sleep(5)
            
        except Exception as e:
            print(f"Error during simulation: {e}")
            time.sleep(5)

if __name__ == "__main__":
    simulate_traffic()
