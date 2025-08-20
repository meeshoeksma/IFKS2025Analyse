import json
import folium

# Load the JSON data
with open("./BClasseSloten.json", "r") as f:
    data = json.load(f)

# Calculate the center of the map
lats = []
lons = []
for ship in data["shiptracks"]:
    lats.extend(ship["lat"])
    lons.extend(ship["lon"])

center_lat = sum(lats) / len(lats)
center_lon = sum(lons) / len(lons)

# Create a Folium map centered around the average coordinates
m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

# Define a list of colors for the tracks
colors = [
    "red", "blue", "green", "purple", "orange", "darkred",
    "lightred", "darkblue", "darkgreen", "cadetblue", "darkpurple",
    "white", "black", "pink"
]

# Plot each ship's track
for i, ship in enumerate(data["shiptracks"]):
    # Create a list of (latitude, longitude) pairs for the track
    points = list(zip(ship["lat"], ship["lon"]))
    
    # Get a color for the current ship
    color = colors[i % len(colors)]
    
    # Add the track to the map
    folium.PolyLine(points, color=color, weight=2.5, opacity=1, tooltip=ship["name"]).add_to(m)

# Save the map to an HTML file
m.save("sailing_tracks_map.html")
open("./sailing_tracks_map.html")



def print_all_keys(obj, prefix=''):
    if isinstance(obj, dict):
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            print(full_key)
            print_all_keys(value, full_key)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            print_all_keys(item, f"{prefix}[{i}]")

# Use it after loading your JSON
print_all_keys(data)
