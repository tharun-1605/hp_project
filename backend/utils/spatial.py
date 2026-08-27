"""Spatial and Geographic Math Utilities."""
import math
from typing import Tuple

EARTH_RADIUS_METERS = 6371000.0

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two GPS points in meters."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return EARTH_RADIUS_METERS * c

def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the initial compass bearing from point 1 to point 2 in degrees (0..360)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)

    initial_bearing = math.atan2(y, x)
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360.0) % 360.0

    return compass_bearing

def point_to_segment_distance(plat: float, plon: float,
                             lat1: float, lon1: float,
                             lat2: float, lon2: float) -> float:
    """Calculate approximate distance in meters from point P to line segment (A, B)."""
    # Convert lat/lon to approximate Cartesian meters centered at P
    d_ax = haversine_distance(plat, plon, plat, lon1) * (1 if lon1 >= plon else -1)
    d_ay = haversine_distance(plat, plon, lat1, plon) * (1 if lat1 >= plat else -1)
    
    d_bx = haversine_distance(plat, plon, plat, lon2) * (1 if lon2 >= plon else -1)
    d_by = haversine_distance(plat, plon, lat2, plon) * (1 if lat2 >= plat else -1)

    # Segment length squared
    l2 = (d_bx - d_ax) ** 2 + (d_by - d_ay) ** 2
    if l2 == 0.0:
        return math.sqrt(d_ax ** 2 + d_ay ** 2)

    # Projection factor t
    t = max(0.0, min(1.0, (-(d_ax * (d_bx - d_ax) + d_ay * (d_by - d_ay))) / l2))
    proj_x = d_ax + t * (d_bx - d_ax)
    proj_y = d_ay + t * (d_by - d_ay)

    return math.sqrt(proj_x ** 2 + proj_y ** 2)
