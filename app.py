import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
from streamlit_autorefresh import st_autorefresh
import os
import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Smart Traffic Monitoring System",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CUSTOM CSS FOR PREMIUM LOOK ---
st.markdown("""
<style>
    /* Main container max width */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Premium Metric styling (using Streamlit's native st.metric but styled) */
    div[data-testid="metric-container"] {
        background-color: rgba(30, 30, 30, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    h1, h2, h3 {
        font-weight: 300 !important;
        letter-spacing: -0.5px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- INIT SUPABASE ---
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

@st.cache_resource
def init_supabase():
    if url and key:
        return create_client(url, key)
    return None

supabase: Client = init_supabase()

# --- AUTHENTICATION ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

def login():
    st.title("🌍 Smart Traffic Monitoring System")
    st.markdown("### Secure Access")
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if username == "admin" and password == "admin123":
                    st.session_state['authenticated'] = True
                    st.rerun()
                else:
                    st.error("Invalid credentials.")

def logout():
    st.session_state['authenticated'] = False
    st.rerun()

# --- DATA FETCHING ---
def fetch_sensors():
    if not supabase: return pd.DataFrame()
    res = supabase.table("sensors").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def fetch_historical_traffic(limit=2000):
    if not supabase: return pd.DataFrame()
    res = supabase.table("traffic_records").select("*, sensors(location, latitude, longitude)").order("timestamp", desc=True).limit(limit).execute()
    if not res.data: return pd.DataFrame()
    
    df = pd.DataFrame(res.data)
    df['location'] = df['sensors'].apply(lambda x: x['location'] if x else 'Unknown')
    df['lat'] = df['sensors'].apply(lambda x: x['latitude'] if x else 0.0)
    df['lon'] = df['sensors'].apply(lambda x: x['longitude'] if x else 0.0)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

# --- DASHBOARD APP ---
def dashboard_app():
    if not supabase:
        st.error("Failed to connect to Supabase. Check your .env file.")
        return

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("🌍 STMS Pro")
        st.markdown("Enterprise Traffic Command Center")
        st.markdown("---")
        page = st.radio("Navigation", ["Live Operations", "Advanced Analytics", "Infrastructure Management"])
        
        st.markdown("---")
        st.markdown("### Global Filters")
        weather_filter = st.selectbox("Weather Condition", ["All", "clear", "cloudy", "rain", "fog"])
        
        st.markdown("---")
        st.button("Logout", on_click=logout, use_container_width=True)

    # Fetch Data
    sensors_df = fetch_sensors()
    traffic_df = fetch_historical_traffic()
    
    if traffic_df.empty:
        st.warning("No live traffic data found. Start `python sensor_simulator.py`.")
        return

    # Apply Filters
    if weather_filter != "All":
        traffic_df = traffic_df[traffic_df['weather_condition'] == weather_filter]

    # Calculate current state (latest record per sensor)
    latest_traffic = traffic_df.sort_values('timestamp').drop_duplicates(subset=['sensor_id'], keep='last')
    
    # Calculate previous state (to show deltas)
    # We find the second-latest record for each sensor for comparison
    previous_traffic = traffic_df.sort_values('timestamp').groupby('sensor_id').nth(-2).reset_index()
    if previous_traffic.empty:
        previous_traffic = latest_traffic # fallback if not enough data
        
    if page == "Live Operations":
        st_autorefresh(interval=5000, key="live_dash")
        
        st.title("Live Operations Center")
        
        # --- TOP KPIs with Deltas ---
        curr_vehicles = latest_traffic['vehicle_count'].sum()
        prev_vehicles = previous_traffic['vehicle_count'].sum()
        veh_delta = int(curr_vehicles - prev_vehicles)
        
        curr_speed = latest_traffic['avg_speed_kmh'].mean()
        prev_speed = previous_traffic['avg_speed_kmh'].mean()
        speed_delta = curr_speed - prev_speed
        
        curr_density = latest_traffic['congestion_density_pct'].mean()
        prev_density = previous_traffic['congestion_density_pct'].mean()
        density_delta = curr_density - prev_density
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Network Volume (Active)", f"{curr_vehicles:,}", f"{veh_delta} from last cycle")
        col2.metric("Network Velocity", f"{curr_speed:.1f} km/h", f"{speed_delta:.1f} km/h")
        
        # Invert delta color for density (lower is better)
        col3.metric("Avg Congestion Density", f"{curr_density:.1f}%", f"{density_delta:.1f}%", delta_color="inverse")
        
        active_sensors = len(sensors_df[sensors_df['status'] == 'active'])
        col4.metric("Infrastructure Health", f"{active_sensors} Active", f"{len(sensors_df) - active_sensors} Offline/Maint", delta_color="off")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- MAIN VISUALS ---
        tab1, tab2 = st.tabs(["🗺️ Spatial View (3D Map)", "📈 Temporal View (Trends)"])
        
        with tab1:
            st.markdown("### Real-Time Network Congestion Map")
            
            # Prepare map data
            map_data = latest_traffic[['location', 'lat', 'lon', 'congestion_density_pct', 'avg_speed_kmh', 'vehicle_count']].copy()
            # Normalize density for height mapping (sleeker height)
            map_data['elevation'] = map_data['congestion_density_pct'] * 10
            
            # Color mapping: Red (high density) to Green (low density)
            def get_color(density):
                if density > 75: return [255, 60, 60, 220] # Softer red
                elif density > 40: return [255, 180, 50, 220] # Softer orange
                return [50, 255, 100, 220] # Softer green
            
            map_data['color'] = map_data['congestion_density_pct'].apply(get_color)

            # Define PyDeck map
            view_state = pdk.ViewState(
                latitude=map_data['lat'].mean() if not map_data.empty else 12.8398,
                longitude=map_data['lon'].mean() if not map_data.empty else 80.0526,
                zoom=14,
                pitch=45,
            )
            
            layer = pdk.Layer(
                'ColumnLayer',
                data=map_data,
                get_position='[lon, lat]',
                get_elevation='elevation',
                elevation_scale=1,
                radius=40, # Much thinner radius for city-level zoom
                get_fill_color='color',
                pickable=True,
                auto_highlight=True
            )
            
            tooltip = {
                "html": "<b>{location}</b><br>Density: {congestion_density_pct}%<br>Speed: {avg_speed_kmh} km/h",
                "style": {"background": "grey", "color": "white", "font-family": '"Helvetica Neue", Arial', "z-index": "10000"}
            }
            
            st.pydeck_chart(pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                tooltip=tooltip,
                map_style='mapbox://styles/mapbox/dark-v10'
            ))

        with tab2:
            st.markdown("### System-Wide Velocity Trend (Rolling Average)")
            # Compute rolling average for smoother visualization
            trend_df = traffic_df.groupby('timestamp')['avg_speed_kmh'].mean().reset_index().sort_values('timestamp')
            trend_df['Rolling Speed'] = trend_df['avg_speed_kmh'].rolling(window=5, min_periods=1).mean()
            
            fig = px.area(trend_df, x='timestamp', y=['avg_speed_kmh', 'Rolling Speed'],
                          color_discrete_sequence=['rgba(0,180,216,0.3)', '#0077b6'],
                          template='plotly_dark')
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=400, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)

    elif page == "Advanced Analytics":
        st.title("Advanced Traffic Analytics")
        st.markdown("Historical multidimensional analysis of traffic patterns.")
        
        # Heatmap of congestion by hour and location
        st.subheader("Congestion Matrix: Location vs. Hour of Day")
        heatmap_data = traffic_df.copy()
        heatmap_data['hour'] = heatmap_data['timestamp'].dt.hour
        heatmap_pivot = heatmap_data.groupby(['location', 'hour'])['congestion_density_pct'].mean().unstack().fillna(0)
        
        fig_heat = px.imshow(heatmap_pivot, color_continuous_scale='Magma', aspect='auto', template="plotly_dark")
        fig_heat.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=350)
        st.plotly_chart(fig_heat, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Speed Distribution by Weather")
            # Box plot to show statistical distribution
            fig_box = px.box(traffic_df, x="weather_condition", y="avg_speed_kmh", color="weather_condition",
                             template="plotly_dark", points="all")
            fig_box.update_layout(margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_box, use_container_width=True)
            
        with col2:
            st.subheader("Sensor Performance Radar")
            # Radar chart comparing sensors across metrics
            radar_data = traffic_df.groupby('location')[['avg_speed_kmh', 'congestion_density_pct', 'vehicle_count']].mean().reset_index()
            # Normalize data for radar chart (0-1 scale)
            for col in ['avg_speed_kmh', 'congestion_density_pct', 'vehicle_count']:
                max_val = radar_data[col].max()
                if max_val > 0:
                    radar_data[col] = radar_data[col] / max_val
            
            fig_radar = go.Figure()
            for i, row in radar_data.iterrows():
                fig_radar.add_trace(go.Scatterpolar(
                    r=[row['avg_speed_kmh'], row['congestion_density_pct'], row['vehicle_count'], row['avg_speed_kmh']],
                    theta=['Avg Speed', 'Density', 'Volume', 'Avg Speed'],
                    fill='toself',
                    name=row['location']
                ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=False)),
                showlegend=True,
                template="plotly_dark",
                margin=dict(l=0, r=0, t=30, b=0)
            )
            st.plotly_chart(fig_radar, use_container_width=True)

    elif page == "Infrastructure Management":
        st.title("Infrastructure Management")
        st.markdown("Manage Edge IoT Devices.")
        
        if not sensors_df.empty:
            st.dataframe(sensors_df[['id', 'name', 'location', 'status', 'latitude', 'longitude']], use_container_width=True)
        
        with st.expander("Register New Edge Sensor", expanded=False):
            with st.form("new_sensor_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_name = st.text_input("Hardware Identifier (Name)")
                    new_loc = st.text_input("Deployment Location")
                with col2:
                    new_lat = st.number_input("Latitude", format="%.6f", value=12.8398)
                    new_lon = st.number_input("Longitude", format="%.6f", value=80.0526)
                
                new_status = st.selectbox("Initial Status", ["active", "maintenance", "offline"])
                
                if st.form_submit_button("Deploy Sensor"):
                    if new_name and new_loc:
                        res = supabase.table("sensors").insert({
                            "name": new_name, 
                            "location": new_loc, 
                            "status": new_status,
                            "latitude": new_lat,
                            "longitude": new_lon
                        }).execute()
                        st.success("Sensor deployed successfully!")
                        st.rerun()

# --- MAIN RUNNER ---
if not st.session_state['authenticated']:
    login()
else:
    dashboard_app()
