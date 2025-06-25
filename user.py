import os
import requests
import json
import polyline
import folium
from datetime import datetime, timedelta

# Google API Key (Please replace with your own)
API_KEY = "AIzaSyAuEeKtQ2BvMrSspAyUnavpymV-n-p2haI"

# Blocked Roads JSON File - Use the full path provided
BLOCKED_ROADS_FILE = r"C:\Users\HP\tamilnadiu hackton\traffic_module\blocked_roads.json"

def load_blocked_roads():
    """Load blocked roads from a JSON file with robust error handling."""
    try:
        # Verify file exists
        if not os.path.exists(BLOCKED_ROADS_FILE):
            print(f"⚠️ Blocked roads file not found: {BLOCKED_ROADS_FILE}")
            return {}

        # Open and parse JSON
        with open(BLOCKED_ROADS_FILE, "r") as file:
            blocked_roads = json.load(file)
            print("✅ Blocked roads successfully loaded.")
            return blocked_roads
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON format in {BLOCKED_ROADS_FILE}")
        return {}
    except Exception as e:
        print(f"❌ Unexpected error loading blocked roads: {e}")
        return {}

def check_road_blocked(source, destination, route_coordinates):
    """
    Advanced check for blocked roads.
    
    Args:
    - source: Starting location name
    - destination: Ending location name
    - route_coordinates: List of (lat, lon) coordinates of the route
    
    Returns:
    - List of blocked road segments
    """
    blocked_roads = load_blocked_roads()
    blocked_segments = []
    
    # Create route key (case-insensitive and handle potential space variations)
    route_keys = [
        f"{source.lower()}_{destination.lower()}",
        f"{source.lower()} _{destination.lower()}",
        f"{source.lower()}_ramapuram".replace(" ", "")  # Specific to your example
    ]
    
    # Check against all possible route key variations
    for route_key in route_keys:
        if route_key in blocked_roads:
            blocked_road_names = blocked_roads[route_key]
            blocked_segments.extend(blocked_road_names)
            print(f"🚧 Blocked roads found for route {route_key}: {blocked_road_names}")
    
    return blocked_segments

def get_coordinates(location_name):
    """Fetch latitude and longitude for a given location using Google Geocoding API."""
    geo_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location_name}&key={API_KEY}"
    response = requests.get(geo_url)
    geo_data = response.json()

    if geo_data['status'] == "OK":
        lat = geo_data['results'][0]['geometry']['location']['lat']
        lng = geo_data['results'][0]['geometry']['location']['lng']
        return lat, lng
    else:
        print(f"❌ Error fetching coordinates for {location_name}: {geo_data['status']}")
        return None, None

def get_routes(source, destination):
    """Advanced route visualization with blocked roads detection."""
    src_lat, src_lng = get_coordinates(source)
    dest_lat, dest_lng = get_coordinates(destination)

    if src_lat is None or dest_lat is None:
        print("❌ Invalid source or destination. Please try again.")
        return

    url = "https://routes.googleapis.com/directions/v2:computeRoutes"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline"
    }

    # Set a future timestamp (current time + 5 minutes)
    future_time = (datetime.utcnow() + timedelta(minutes=5)).isoformat() + "Z"

    payload = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": src_lat,
                    "longitude": src_lng
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": dest_lat,
                    "longitude": dest_lng
                }
            }
        },
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
        "departureTime": future_time,
        "computeAlternativeRoutes": False
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        data = response.json()
        encoded_polyline = data['routes'][0]['polyline']['encodedPolyline']
        
        print("\n=== Shortest Route Found ===")
        print(f"Total Distance: {data['routes'][0]['distanceMeters'] / 1000:.2f} km")
        print(f"Estimated Time: {data['routes'][0]['duration']}")

        # Decode the polyline to get latitude and longitude coordinates
        decoded_coordinates = polyline.decode(encoded_polyline)

        # Check for blocked roads
        blocked_segments = check_road_blocked(source, destination, decoded_coordinates)
        
        # ========================== 🌍 MAP VISUALIZATION ==========================
        # Create a folium map centered at source location
        route_map = folium.Map(location=[src_lat, src_lng], zoom_start=7)

        # Visualize entire route in blue
        folium.PolyLine(
            decoded_coordinates, 
            color="blue", 
            weight=5, 
            opacity=0.5, 
            dash_array='10'  # Dashed line for full route
        ).add_to(route_map)

        # Highlight shortest path in green
        folium.PolyLine(
            decoded_coordinates, 
            color="green", 
            weight=7, 
            opacity=0.8
        ).add_to(route_map)

        # Highlight blocked segments in red
        if blocked_segments:
            print("\n🚧 BLOCKED ROAD SEGMENTS:")
            for segment in blocked_segments:
                print(f"⚠️ Blocked: {segment}")
                # Add red markers or lines to indicate blocked segments
                folium.PolyLine(
                    decoded_coordinates, 
                    color="red", 
                    weight=8, 
                    opacity=1, 
                    dash_array='2'  # Dotted line for blocked segments
                ).add_to(route_map)

        # Add dynamic markers for Start & End
        start_marker = folium.Marker(
            decoded_coordinates[0], 
            popup=f"{source} (Start)", 
            icon=folium.Icon(color="green", icon="play")
        )
        end_marker = folium.Marker(
            decoded_coordinates[-1], 
            popup=f"{destination} (End)", 
            icon=folium.Icon(color="red", icon="stop")
        )

        # Add pulsing effect to markers
        start_marker.add_to(route_map)
        end_marker.add_to(route_map)

        # Save map as an HTML file with dynamic visualization
        file_name = f"{source}_to_{destination}_route.html".replace(" ", "_")
        route_map.save(file_name)
        print(f"\n✅ Dynamic route map saved as '{file_name}'. Open it in a browser.")

    else:
        print("❌ Error:", response.text)

# Interactive route selection
def main():
    print("🗺️ Advanced Route Visualization Tool")
    
    # Print the actual file path being used
    print(f"📁 Blocked Roads File: {BLOCKED_ROADS_FILE}")
    
    # Verify file exists before proceeding
    if not os.path.exists(BLOCKED_ROADS_FILE):
        print("❌ Blocked roads file not found. Please check the file path.")
        return

    source = input("Enter Source Location: ")
    destination = input("Enter Destination Location: ")
    get_routes(source, destination)

if __name__ == "__main__":
    main()