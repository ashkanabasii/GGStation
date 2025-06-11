# -*- coding: utf-8 -*-
"""
Created on Fri Apr 25 14:11:42 2025

@author: ashka
"""

import serial
import folium
import webbrowser
import time
import os

# SETTINGS
GPS_PORT = "COM6"
GPS_BAUD = 9600
MAP_FILE = "live_gps_map.html"

# Store the full path to map for browser to open
map_path = os.path.abspath(MAP_FILE)

# Function to extract latitude and longitude from your GPS output
def extract_lat_lon(line):
    try:
        parts = line.split()
        lat = float(parts[2])
        lon = float(parts[3])
        return lat, lon
    except (IndexError, ValueError):
        return None, None

# Function to create or update the map
def update_map(path_points):
    if not path_points:
        return
    gps_map = folium.Map(location=path_points[-1], zoom_start=17)

    # Draw all previous points as a line trail
    folium.PolyLine(path_points, color="blue", weight=2.5, opacity=1).add_to(gps_map)

    # Add the current location as a marker
    folium.Marker(path_points[-1], popup="Current Location").add_to(gps_map)

    gps_map.save(MAP_FILE)
    webbrowser.open("file://" + map_path)  # This will open a new tab every time — or cache reload in browser

def main():
    ser = serial.Serial(GPS_PORT, GPS_BAUD, timeout=1)
    print("Live GPS tracking started. Move around...")

    path_points = []
    last_update_time = 0

    while True:
        line = ser.readline()
        if not line:
            continue

        decoded_line = line.decode('ascii', errors='replace').strip()
        print("Raw GPS:", decoded_line)

        lat, lon = extract_lat_lon(decoded_line)
        if lat is not None and lon is not None:
            print(f"Current Position: Latitude={lat:.6f}, Longitude={lon:.6f}")
            path_points.append((lat, lon))

            # Update map every 5 seconds
            current_time = time.time()
            if current_time - last_update_time > 5:
                update_map(path_points)
                last_update_time = current_time

        time.sleep(1)

if __name__ == "__main__":
    main()
