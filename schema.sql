-- Execute this in your Supabase SQL Editor

-- 1. Create sensors table
CREATE TABLE sensors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    latitude FLOAT,
    longitude FLOAT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'maintenance', 'offline')),
    installed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Create traffic_records table
CREATE TABLE traffic_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sensor_id UUID REFERENCES sensors(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    vehicle_count INTEGER NOT NULL,
    avg_speed_kmh FLOAT NOT NULL,
    congestion_density_pct FLOAT NOT NULL,
    weather_condition TEXT DEFAULT 'clear'
);

-- 3. Create index for fast timeseries queries
CREATE INDEX idx_traffic_timestamp ON traffic_records(timestamp DESC);
CREATE INDEX idx_traffic_sensor ON traffic_records(sensor_id);

-- 4. Insert some initial dummy sensors so we have locations to stream to
INSERT INTO sensors (name, location, latitude, longitude) VALUES
('Camera N1', 'GST Road - Guduvanchery', 12.8398, 80.0526),
('Bridge Cam 1', 'Nandivaram', 12.8368, 80.0506),
('Intersection 4A', 'Railway Station Road', 12.8428, 80.0546),
('Bypass S3', 'Defense Colony', 12.8450, 80.0580),
('Avenue C2', 'Urapakkam Border', 12.8300, 80.0450);

-- 5. Enable Row Level Security (RLS)
ALTER TABLE sensors ENABLE ROW LEVEL SECURITY;
ALTER TABLE traffic_records ENABLE ROW LEVEL SECURITY;

-- 6. Create policies to allow access via the anon key
-- (For a production app, you would restrict this to authenticated users, 
-- but for this dashboard prototype, we allow the anon role to read/write)

CREATE POLICY "Allow anon select on sensors" 
ON sensors FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon insert on sensors" 
ON sensors FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY "Allow anon select on traffic_records" 
ON traffic_records FOR SELECT TO anon USING (true);

CREATE POLICY "Allow anon insert on traffic_records" 
ON traffic_records FOR INSERT TO anon WITH CHECK (true);

