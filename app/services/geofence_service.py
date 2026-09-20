import math

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle distance between two points on the Earth's surface
    using the Haversine formula. Returns distance in meters rounded to 2 decimal places.
    """
    R = 6371000.0  # Earth radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance = R * c
    return round(distance, 2)

def verify_geofence(emp_lat: float, emp_lon: float, office_lat: float, office_lon: float, radius_meters: float):
    """
    Verifies if employee coordinates fall inside the office radius.
    Returns (is_inside: bool, distance_in_meters: float)
    """
    distance = calculate_haversine_distance(emp_lat, emp_lon, office_lat, office_lon)
    is_inside = distance <= radius_meters
    return is_inside, distance
