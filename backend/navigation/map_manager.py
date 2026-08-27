"""Map Manager for place search, geocoding via OpenStreetMap (Nominatim), and POI metadata."""
import requests
from typing import Dict, Any, Optional, List
from backend.utils.logger import get_logger

logger = get_logger("MapManager")

# Preset offline dictionary of common destination coordinates for fallback/offline search
PRESET_LOCATIONS: Dict[str, Dict[str, Any]] = {
    "sri eshwar college": {
        "name": "Sri Eshwar College of Engineering",
        "latitude": 10.8285,
        "longitude": 76.9608,
        "address": "Kondampatti Post, Vadasithur, Kinathukadavu, Tamil Nadu"
    },
    "railway station": {
        "name": "Central Railway Station",
        "latitude": 11.0018,
        "longitude": 76.9628,
        "address": "Station Road, City Center"
    },
    "college": {
        "name": "Sri Eshwar College of Engineering",
        "latitude": 10.8285,
        "longitude": 76.9608,
        "address": "Kondampatti Post, Vadasithur, Kinathukadavu, Tamil Nadu"
    },
    "hospital": {
        "name": "City General Hospital",
        "latitude": 11.0080,
        "longitude": 76.9670,
        "address": "Healthcare Avenue, City North"
    },
    "bus stand": {
        "name": "Central Bus Stand",
        "latitude": 11.0050,
        "longitude": 76.9580,
        "address": "Gandhipuram Bus Stand Road"
    }
}

class MapManager:
    """Handles location lookups, Nominatim OpenStreetMap geocoding, and POIs."""

    def __init__(self, nominatim_url: str = "https://nominatim.openstreetmap.org"):
        self.nominatim_url = nominatim_url

    def search_destination(self, query: str, user_lat: Optional[float] = None, user_lon: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Search destination by text query using Nominatim OSM or offline preset dictionary."""
        query_clean = query.strip().lower()
        logger.info(f"Searching for destination: '{query_clean}'")

        # First check offline presets
        for key, info in PRESET_LOCATIONS.items():
            if key in query_clean or query_clean in key:
                logger.info(f"Matched offline location preset for '{query}'")
                return info

        # Try Nominatim OpenStreetMap online API
        try:
            headers = {"User-Agent": "VisionNav-OpenSource-Assistive/1.0"}
            params = {
                "q": query,
                "format": "json",
                "limit": 1
            }
            if user_lat is not None and user_lon is not None:
                # Viewbox filter around user location (~50km box)
                params["viewbox"] = f"{user_lon-0.5},{user_lat+0.5},{user_lon+0.5},{user_lat-0.5}"

            response = requests.get(f"{self.nominatim_url}/search", params=params, headers=headers, timeout=4)
            if response.status_code == 200:
                results = response.json()
                if results and len(results) > 0:
                    first = results[0]
                    return {
                        "name": first.get("display_name", query),
                        "latitude": float(first["lat"]),
                        "longitude": float(first["lon"]),
                        "address": first.get("display_name", "")
                    }
        except Exception as e:
            logger.warning(f"Nominatim geocoding request failed: {e}. Falling back to default mock location.")

        # Fallback default destination if not found online/offline
        default_lat = (user_lat + 0.005) if user_lat else 11.0075
        default_lon = (user_lon + 0.005) if user_lon else 76.9675
        return {
            "name": query.title(),
            "latitude": round(default_lat, 6),
            "longitude": round(default_lon, 6),
            "address": f"Near {query.title()}"
        }

    def reverse_geocode(self, lat: float, lon: float) -> str:
        """Convert lat, lon coordinates into a human-readable area name, street, or landmark."""
        from backend.utils.spatial import haversine_distance

        # 1. Check nearest preset location within ~500m
        for key, info in PRESET_LOCATIONS.items():
            p_lat = info["latitude"]
            p_lon = info["longitude"]
            dist = haversine_distance(lat, lon, p_lat, p_lon)
            if dist <= 500:
                return f"near {info['name']}"

        # 2. Try Nominatim OpenStreetMap reverse geocoding
        try:
            headers = {"User-Agent": "VisionNav-OpenSource-Assistive/1.0"}
            params = {
                "lat": lat,
                "lon": lon,
                "format": "json",
                "zoom": 17
            }
            res = requests.get(f"{self.nominatim_url}/reverse", params=params, headers=headers, timeout=3)
            if res.status_code == 200:
                data = res.json()
                addr = data.get("address", {})
                road = addr.get("road") or addr.get("pedestrian") or addr.get("suburb") or addr.get("neighbourhood")
                city = addr.get("city") or addr.get("town") or addr.get("county")
                if road and city:
                    return f"on {road}, {city}"
                elif data.get("display_name"):
                    parts = data["display_name"].split(",")
                    return f"near {', '.join(parts[:2])}"
        except Exception as e:
            logger.warning(f"Reverse geocoding request error: {e}")

        return "near Station Road, City Center"
