import pandas as pd
import numpy as np
import datetime
import random
import os

def generate_sensor_data(num_sensors=10):
    locations = ["Main St & 1st Ave", "Highway 101 North", "Downtown Square", "Westside Bypass", 
                 "Industrial Park Rd", "Airport Expressway", "University Blvd", "Riverside Dr", 
                 "Central Bridge", "Eastside Connector"]
    
    sensors = []
    for i in range(num_sensors):
        sensor_id = f"SENS-{1000 + i}"
        sensors.append({
            "Sensor ID": sensor_id,
            "Location": locations[i % len(locations)],
            "Status": "Active" if random.random() > 0.1 else "Maintenance",
            "Installation Date": (datetime.datetime.now() - datetime.timedelta(days=random.randint(100, 1000))).strftime("%Y-%m-%d")
        })
    return pd.DataFrame(sensors)

def generate_traffic_data(sensors_df, days=7):
    records = []
    
    start_date = datetime.datetime.now() - datetime.timedelta(days=days)
    
    for _, sensor in sensors_df.iterrows():
        sensor_id = sensor["Sensor ID"]
        
        # Generate data every 15 minutes
        current_time = start_date
        end_time = datetime.datetime.now()
        
        while current_time < end_time:
            # Base pattern depends on hour (rush hours are higher)
            hour = current_time.hour
            is_rush_hour = (7 <= hour <= 9) or (16 <= hour <= 19)
            is_night = (23 <= hour <= 24) or (0 <= hour <= 5)
            
            if is_rush_hour:
                base_vehicles = random.randint(150, 300)
                base_speed = random.randint(10, 40)
            elif is_night:
                base_vehicles = random.randint(10, 50)
                base_speed = random.randint(60, 90)
            else:
                base_vehicles = random.randint(50, 150)
                base_speed = random.randint(40, 70)
                
            # Add some random noise
            vehicle_count = max(0, int(np.random.normal(base_vehicles, base_vehicles * 0.2)))
            speed = max(0, min(120, int(np.random.normal(base_speed, base_speed * 0.1))))
            
            # Density is roughly proportional to vehicle count and inversely proportional to speed
            density = min(100, int((vehicle_count / 300) * 100))
            if speed < 20 and vehicle_count > 100:
                density = min(100, density + 20)
                
            records.append({
                "Timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                "Sensor ID": sensor_id,
                "Vehicle Count": vehicle_count,
                "Average Speed (km/h)": speed,
                "Density (%)": density
            })
            
            current_time += datetime.timedelta(minutes=15)
            
    return pd.DataFrame(records)

if __name__ == "__main__":
    print("Generating simulated data...")
    sensors_df = generate_sensor_data()
    traffic_df = generate_traffic_data(sensors_df)
    
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    sensors_df.to_csv(os.path.join(data_dir, "sensors.csv"), index=False)
    traffic_df.to_csv(os.path.join(data_dir, "traffic_records.csv"), index=False)
    
    print(f"Generated {len(sensors_df)} sensors and {len(traffic_df)} traffic records.")
    print("Data saved to the 'data' directory.")
