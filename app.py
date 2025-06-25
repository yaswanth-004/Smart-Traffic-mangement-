from flask import Flask, render_template, request, jsonify
import os
import json
import polyline
import folium
from datetime import datetime, timedelta
import requests
from flask import Flask, render_template, Response
from vehicle_parking.parking_detector import ParkingDetector
import cv2

app = Flask(__name__)

#
# Configuration
API_KEY = "AIzaSyAuEeKtQ2BvMrSspAyUnavpymV-n-p2haI"
BLOCKED_ROADS_FILE = "blocked_roads.json"
from flask import send_from_directory

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                             'favicon.ico', mimetype='image/vnd.microsoft.icon')

# Helper functions (from your existing code)
def load_blocked_roads():
    try:
        with open(BLOCKED_ROADS_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_blocked_roads(blocked_roads):
    with open(BLOCKED_ROADS_FILE, "w") as file:
        json.dump(blocked_roads, file, indent=4)

def get_coordinates(location_name):
    geo_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location_name}&key={API_KEY}"
    response = requests.get(geo_url)
    geo_data = response.json()
    
    if geo_data['status'] == "OK":
        return geo_data['results'][0]['geometry']['location']['lat'], geo_data['results'][0]['geometry']['location']['lng']
    return None, None

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/map')
def map_route():
    source = request.args.get('source', '')
    destination = request.args.get('destination', '')
    
    if not source or not destination:
        return render_template('error.html', message="Please provide both source and destination")
    
    src_lat, src_lng = get_coordinates(source)
    dest_lat, dest_lng = get_coordinates(destination)

    if src_lat is None or dest_lat is None:
        return render_template('error.html', message="Invalid source or destination location")

    # Get routes from Google Maps API
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
    
    if response.status_code != 200:
        return render_template('error.html', message="Failed to fetch route data from Google Maps")

    data = response.json()
    routes = data.get("routes", [])

    if not routes:
        return render_template('error.html', message="No routes found for the given locations")

    # Create map
    route_map = folium.Map(location=[src_lat, src_lng], zoom_start=10)
    
    # Process routes and blocked roads
    blocked_roads = load_blocked_roads()
    route_key = f"{source.lower()}_{destination.lower()}"
    blocked_segments = blocked_roads.get(route_key, [])
    
    # Add routes to map
    for index, route in enumerate(routes):
        encoded_polyline = route['polyline']['encodedPolyline']
        decoded_coordinates = polyline.decode(encoded_polyline)
        
        # Check if this route has blocked segments
        has_blocked = any(segment in str(decoded_coordinates) for segment in blocked_segments)
        
        # Style based on blocked status
        color = "red" if has_blocked else "blue" if index == 0 else "gray"
        weight = 8 if has_blocked else 6 if index == 0 else 4
        
        folium.PolyLine(
            decoded_coordinates,
            color=color,
            weight=weight,
            opacity=0.8 if index == 0 else 0.5,
            tooltip="Blocked Route" if has_blocked else f"Route {index + 1}"
        ).add_to(route_map)

    # Add markers
    folium.Marker(
        [src_lat, src_lng],
        popup=f"<b>Start: {source}</b>",
        icon=folium.Icon(color="green", icon="play")
    ).add_to(route_map)

    folium.Marker(
        [dest_lat, dest_lng],
        popup=f"<b>End: {destination}</b>",
        icon=folium.Icon(color="red", icon="stop")
    ).add_to(route_map)

    # Save map to HTML string
    map_html = route_map._repr_html_()
    
    return render_template('map.html', 
                         map_html=map_html,
                         source=source,
                         destination=destination,
                         blocked_roads=blocked_segments)

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if request.method == 'POST':
        action = request.form.get('action')
        source = request.form.get('source', '').strip()
        destination = request.form.get('destination', '').strip()
        road = request.form.get('road', '').strip()
        
        blocked_roads = load_blocked_roads()
        route_key = f"{source.lower()}_{destination.lower()}"
        
        if action == 'block':
            if route_key not in blocked_roads:
                blocked_roads[route_key] = []
            if road.lower() not in [r.lower() for r in blocked_roads[route_key]]:
                blocked_roads[route_key].append(road)
                save_blocked_roads(blocked_roads)
                message = f"Road '{road}' blocked between {source} and {destination}"
            else:
                message = f"Road '{road}' is already blocked on this route"
        
        elif action == 'unblock':
            if route_key in blocked_roads and road in blocked_roads[route_key]:
                blocked_roads[route_key].remove(road)
                if not blocked_roads[route_key]:
                    del blocked_roads[route_key]
                save_blocked_roads(blocked_roads)
                message = f"Road '{road}' unblocked between {source} and {destination}"
            else:
                message = f"Road '{road}' is not blocked on this route"
        
        return render_template('admin.html', 
                             blocked_roads=blocked_roads,
                             message=message)
    
    return render_template('admin.html', blocked_roads=load_blocked_roads())

if __name__ == '__main__':
    app.run(debug=True)