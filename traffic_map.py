import requests
import json
import polyline
import folium
from datetime import datetime, timedelta

API_KEY = "ADD KEY"  # Replace with your API Key

def get_coordinates(location_name):
    """Fetch latitude and longitude for a given location."""
    geo_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location_name}&key={API_KEY}"
    response = requests.get(geo_url)
    geo_data = response.json()
    
    if geo_data['status'] == "OK":
        return geo_data['results'][0]['geometry']['location']['lat'], geo_data['results'][0]['geometry']['location']['lng']
    return None, None

def get_traffic_junctions(decoded_route):
    """Find traffic signals and junctions along the route using Google Places API."""
    junctions = []
    for lat, lng in decoded_route[::5]:  # Check every 5th point to reduce API calls
        places_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lng}&radius=100&keyword=traffic%20signal&key={API_KEY}"
        response = requests.get(places_url)
        data = response.json()
        
        if data["status"] == "OK":
            for place in data["results"]:
                junctions.append((place["name"], place["geometry"]["location"]["lat"], place["geometry"]["location"]["lng"]))
    
    return junctions

def get_traffic_time(src_lat, src_lng, dest_lat, dest_lng):
    """Fetch real-time travel duration using Google Distance Matrix API."""
    matrix_url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={src_lat},{src_lng}&destinations={dest_lat},{dest_lng}&departure_time=now&traffic_model=best_guess&key={API_KEY}"
    response = requests.get(matrix_url)
    data = response.json()
    
    if data["status"] == "OK":
        return data["rows"][0]["elements"][0]["duration_in_traffic"]["text"]
    return "Unknown"

def get_routes(source, destination):
    """Fetch route, find traffic signals, and display traffic delays."""
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

    payload = {
        "origin": {"location": {"latLng": {"latitude": src_lat, "longitude": src_lng}}},
        "destination": {"location": {"latLng": {"latitude": dest_lat, "longitude": dest_lng}}},
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
        "departureTime": (datetime.utcnow() + timedelta(minutes=5)).isoformat() + "Z",
        "computeAlternativeRoutes": True
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        data = response.json()
        routes = data.get("routes", [])

        if not routes:
            print("❌ No routes found.")
            return

        # ========================== 🌍 MAP VISUALIZATION ==========================
        route_map = folium.Map(location=[src_lat, src_lng], zoom_start=10)

        # Process each route
        shortest_route = None
        shortest_distance = float("inf")

        for index, route in enumerate(routes):
            encoded_polyline = route['polyline']['encodedPolyline']
            decoded_coordinates = polyline.decode(encoded_polyline)
            distance_km = route['distanceMeters'] / 1000

            # Determine if this is the shortest route
            if distance_km < shortest_distance:
                shortest_distance = distance_km
                shortest_route = decoded_coordinates

            # Add the route to the map (Gray for alternative routes)
            folium.PolyLine(decoded_coordinates, color="gray", weight=4, opacity=0.5).add_to(route_map)

            # Show a label with the route distance
            mid_point = decoded_coordinates[len(decoded_coordinates) // 2]
            folium.Marker(mid_point, popup=f"Route {index + 1}: {distance_km:.2f} km",
                          icon=folium.Icon(color="gray", icon="road")).add_to(route_map)

        # Highlight the shortest route in Blue
        folium.PolyLine(shortest_route, color="blue", weight=6, opacity=0.9, tooltip="Shortest Path").add_to(route_map)

        # 🚦 Traffic Signals & Junctions
        junctions = get_traffic_junctions(shortest_route)
        for name, lat, lng in junctions:
            folium.Marker(
                [lat, lng],
                popup=f"🚦 {name}",
                icon=folium.Icon(color="orange", icon="exclamation-sign")
            ).add_to(route_map)

        # ⏳ Real-Time Traffic Delay
        travel_time = get_traffic_time(src_lat, src_lng, dest_lat, dest_lng)

        # Add Start & End markers with BIG names
        folium.Marker(shortest_route[0], 
                      popup=f"<b style='font-size:14px'>{source} (Start)</b><br>🚗 Estimated Travel Time: {travel_time}", 
                      icon=folium.Icon(color="green", icon="info-sign")).add_to(route_map)

        folium.Marker(shortest_route[-1], 
                      popup=f"<b style='font-size:14px'>{destination} (End)</b>", 
                      icon=folium.Icon(color="red", icon="info-sign")).add_to(route_map)

        # Save map as an HTML file
        file_name = f"{source}_to_{destination}_traffic_routes.html".replace(" ", "_")
        route_map.save(file_name)
        print(f"\n✅ Route map saved as '{file_name}'. Open it in a browser.")

    else:
        print("❌ Error:", response.text)

# Get user input for source and destination
source = input("Enter Source Location: ")
destination = input("Enter Destination Location: ")

# Run the function
get_routes(source, destination)
