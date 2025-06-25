import json

BLOCKED_ROADS_FILE = "blocked_roads.json"

def load_blocked_roads():
    """Load blocked roads from a JSON file."""
    try:
        with open(BLOCKED_ROADS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_blocked_roads(blocked_roads):
    """Save blocked roads to a JSON file."""
    with open(BLOCKED_ROADS_FILE, "w") as file:
        json.dump(blocked_roads, file, indent=4)

def add_blocked_road(source, destination, blocked_road):
    """Block a specific road between two locations."""
    blocked_roads = load_blocked_roads()
    
    route_key = f"{source.lower()}_{destination.lower()}"
    
    if route_key not in blocked_roads:
        blocked_roads[route_key] = []

    blocked_roads[route_key].append(blocked_road.lower())  # Store in lowercase

    save_blocked_roads(blocked_roads)
    print(f"🚧 Road '{blocked_road}' is now BLOCKED between {source} and {destination}.")

def remove_blocked_road(source, destination, blocked_road):
    """Unblock a road between two locations."""
    blocked_roads = load_blocked_roads()
    route_key = f"{source.lower()}_{destination.lower()}"

    if route_key in blocked_roads and blocked_road.lower() in blocked_roads[route_key]:
        blocked_roads[route_key].remove(blocked_road.lower())

        if not blocked_roads[route_key]:  
            del blocked_roads[route_key]  

        save_blocked_roads(blocked_roads)
        print(f"Road '{blocked_road}' is now UNBLOCKED between {source} and {destination}.")
    else:
        print(f" Road '{blocked_road}' is NOT blocked on this route.")

def admin_interface():
    """Admin panel to block or unblock roads."""
    while True:
        print("\n===== ADMIN PANEL =====")
        print("1️⃣ Block a Road")
        print("2️⃣ Unblock a Road")
        print("3️⃣ View Blocked Roads")
        print("4️⃣ Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            source = input("Enter Source Location: ")
            destination = input("Enter Destination Location: ")
            blocked_road = input("Enter the road to block: ")
            add_blocked_road(source, destination, blocked_road)

        elif choice == "2":
            source = input("Enter Source Location: ")
            destination = input("Enter Destination Location: ")
            blocked_road = input("Enter the road to unblock: ")
            remove_blocked_road(source, destination, blocked_road)

        elif choice == "3":
            blocked_roads = load_blocked_roads()
            if blocked_roads:
                print("\n🚧 BLOCKED ROADS LIST:")
                for route, roads in blocked_roads.items():
                    src, dest = route.split("_")
                    print(f" {src.capitalize()} → {dest.capitalize()}: {', '.join(roads)}")
            else:
                print(" No roads are currently blocked.")

        elif choice == "4":
            print(" Exiting Admin Panel.")
            break

        else:
            print(" Invalid choice. Try again.")

if __name__ == "__main__":
    admin_interface()
