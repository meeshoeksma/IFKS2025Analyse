
import json
import matplotlib.pyplot as plt
from datetime import datetime

# Load the data from the JSON file
with open('BClasseSloten.json', 'r') as f:
    data = json.load(f)

# Create a new plot
plt.figure(figsize=(12, 6))

# Iterate over each ship track in the data
for ship in data['shiptracks']:
    # Convert timestamps to datetime objects
    timestamps = [datetime.fromtimestamp(ts) for ts in ship['stamp']]
    
    # Filter data from 11:15
    start_time = datetime.strptime("11:15", "%H:%M").time()
    
    filtered_timestamps = []
    filtered_course = []
    
    for i, ts in enumerate(timestamps):
        if ts.time() >= start_time:
            filtered_timestamps.append(ts)
            filtered_course.append(ship['course'][i])

    # Plot course against time
    if ship['name'] == 'Drie Gebroeders':
        plt.plot(filtered_timestamps, filtered_course, label=ship['name'])
    else:
        plt.plot(filtered_timestamps, filtered_course, label=ship['name'], alpha=0.3)

# Add labels and title
plt.xlabel('Tijd')
plt.ylabel('Koers (graden)')
plt.title('Koers van de schepen over tijd')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True)

# Show the plot
plt.savefig('koers_tijd.png')
