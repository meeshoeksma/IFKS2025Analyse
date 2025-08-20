
import json
import folium
import matplotlib.pyplot as plt
from geopy.distance import geodesic
from datetime import datetime

# --- Configuration --- #
# Set your desired start and end times here (Unix timestamps)
# Example: start_time_config = 1754988600, end_time_config = 1754995500
start_time_config = 1754988801  # Set to None to use the earliest timestamp in data
end_time_config = 1754994500    # Set to None to use the latest timestamp in data

# --- Data Loading --- #
with open("./Data/B-Match1-Hindelopen.json", "r") as f:
    data = json.load(f)

# --- Pre-process data based on time configuration --- #
processed_shiptracks = []
for ship in data["shiptracks"]:
    filtered_stamps = []
    filtered_lats = []
    filtered_lons = []
    
    for i in range(len(ship["stamp"])):
        timestamp = ship["stamp"][i]
        if (start_time_config is None or timestamp >= start_time_config) and \
           (end_time_config is None or timestamp <= end_time_config):
            filtered_stamps.append(timestamp)
            filtered_lats.append(ship["lat"][i])
            filtered_lons.append(ship["lon"][i])
    
    if filtered_stamps: # Only add if there's data within the time range
        processed_shiptracks.append({
            "name": ship["name"],
            "lat": filtered_lats,
            "lon": filtered_lons,
            "stamp": filtered_stamps
        })

# pre process the buoytracks
processed_buoytracks = []
for buoy in data["buoytracks"]:
    filtered_stamps = []
    filtered_lats = []
    filtered_lons = []
    
    for i in range(len(buoy["stamp"])):
        timestamp = buoy["stamp"][i]
        if (start_time_config is None or timestamp >= start_time_config) and \
           (end_time_config is None or timestamp <= end_time_config):
            filtered_stamps.append(timestamp)
            filtered_lats.append(buoy["lat"][i])
            filtered_lons.append(buoy["lon"][i])
    
    if filtered_stamps: # Only add if there's data within the time range
        processed_buoytracks.append({
            "name": buoy["name"],
            "lat": filtered_lats,
            "lon": filtered_lons,
            "stamp": filtered_stamps
        })


# --- Map Plotting --- #
lats = []
lons = []
for ship in processed_shiptracks:
    lats.extend(ship["lat"])
    lons.extend(ship["lon"])

# Add buoy coordinates to the center calculation if available

center_lat = sum(lats) / len(lats) if lats else 0
center_lon = sum(lons) / len(lons) if lons else 0

m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

colors = [
    "red", "blue", "green", "purple", "orange", "darkred",
    "lightred", "darkblue", "darkgreen", "cadetblue", "darkpurple",
    "white", "black", "pink"
]

for i, ship in enumerate(processed_shiptracks):
    points = list(zip(ship["lat"], ship["lon"]))
    color = colors[i % len(colors)]
    folium.PolyLine(points, color=color, weight=2.5, opacity=1, tooltip=ship["name"]).add_to(m)

for buoy in enumerate(processed_buoytracks):
    points = list(zip(buoy["lat"], buoy["lon"]))
    color = 'black'
    folium.PolyLine(points, color=color, weight=2.5, opacity=1, tooltip="boei").add_to(m)

m.save("sailing_tracks_speed_map.html")

# --- Speed Calculation and Bar Graph --- #
speeds = {}
for ship in processed_shiptracks:
    total_distance_km = 0
    total_time_seconds = 0

    for i in range(len(ship["lat"]) - 1):
        coords_1 = (ship["lat"][i], ship["lon"][i])
        coords_2 = (ship["lat"][i+1], ship["lon"][i+1])
        
        distance = geodesic(coords_1, coords_2).km
        time_diff = ship["stamp"][i+1] - ship["stamp"][i]
        
        total_distance_km += distance
        total_time_seconds += time_diff
    
    if total_time_seconds > 0:
        # Speed in km/h
        speed_kmh = (total_distance_km / total_time_seconds) * 3600
        # Convert to knots (1 knot = 1.852 km/h)
        speed_knots = speed_kmh / 1.852
        speeds[ship["name"]] = speed_knots

# Create bar graph
if speeds:
    ship_names = list(speeds.keys())
    avg_speeds = list(speeds.values())

    plt.figure(figsize=(12, 6))
    plt.bar(ship_names, avg_speeds, color="skyblue")
    plt.xlabel("Ship Name")
    plt.ylabel("Average Speed (knots)")
    plt.title("Average Speed per Ship")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig("average_speeds_bar_graph.png")
    # plt.show() # Don't show in headless environment

print("Script finished. Check sailing_tracks_speed_map.html and average_speeds_bar_graph.png")



