"""Routing Engine for OSRM walking route calculation and turn-by-turn maneuver extraction."""
import requests
import math
from typing import Dict, Any, List, Tuple
from backend.utils.spatial import haversine_distance, calculate_bearing
from backend.utils.logger import get_logger

logger = get_logger("RoutingEngine")

class RoutingEngine:
    """Calculates walking routes using OSRM API or synthetic offline routing engine."""

    def __init__(self, osrm_server: str = "http://router.project-osrm.org", profile: str = "foot"):
        self.osrm_server = osrm_server
        self.profile = profile

    def calculate_route(self, start_lat: float, start_lon: float,
                        end_lat: float, end_lon: float) -> Dict[str, Any]:
        """Calculate walking route between start and destination coordinates."""
        logger.info(f"Calculating route from ({start_lat}, {start_lon}) to ({end_lat}, {end_lon})")

        # Try live OSRM public server
        try:
            url = f"{self.osrm_server}/route/v1/{self.profile}/{start_lon},{start_lat};{end_lon},{end_lat}"
            params = {
                "overview": "full",
                "geometries": "geojson",
                "steps": "true"
            }
            res = requests.get(url, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data.get("code") == "Ok" and data.get("routes"):
                    logger.info("Successfully fetched route from OSRM.")
                    return self._parse_osrm_response(data["routes"][0])
        except Exception as e:
            logger.warning(f"OSRM request failed: {e}. Generating synthetic walking route.")

        return self._generate_synthetic_route(start_lat, start_lon, end_lat, end_lon)

    def _parse_osrm_response(self, route_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse OSRM GeoJSON route data into standard VisionNav route object."""
        total_distance = route_data.get("distance", 0.0)
        total_duration = route_data.get("duration", 0.0)
        geometry = route_data.get("geometry", {}).get("coordinates", [])

        # Convert [lon, lat] to [lat, lon]
        route_coords = [[pt[1], pt[0]] for pt in geometry]

        parsed_steps = []
        legs = route_data.get("legs", [])
        for leg in legs:
            steps = leg.get("steps", [])
            for step in steps:
                maneuver = step.get("maneuver", {})
                location = maneuver.get("location", [0, 0])
                instruction = self._format_osrm_instruction(maneuver, step.get("name", ""))

                parsed_steps.append({
                    "instruction": instruction,
                    "distance": round(step.get("distance", 0.0), 1),
                    "duration": round(step.get("duration", 0.0), 1),
                    "location": [location[1], location[0]], # [lat, lon]
                    "type": maneuver.get("type", "straight"),
                    "modifier": maneuver.get("modifier", "")
                })

        return {
            "distance": round(total_distance, 1),
            "duration": round(total_duration, 1),
            "steps": parsed_steps if parsed_steps else self._default_steps(route_coords),
            "coordinates": route_coords
        }

    def _format_osrm_instruction(self, maneuver: Dict[str, Any], street_name: str) -> str:
        """Convert OSRM maneuver type and modifier into clear voice navigation text."""
        m_type = maneuver.get("type", "")
        m_mod = maneuver.get("modifier", "")
        street = f" onto {street_name}" if street_name else ""

        if m_type == "depart":
            return f"Walk straight{street}"
        elif m_type == "arrive":
            return "You have reached your destination"
        elif "turn" in m_type or "fork" in m_type:
            if "left" in m_mod:
                return f"Turn left{street}"
            elif "right" in m_mod:
                return f"Turn right{street}"
            elif "slight left" in m_mod:
                return f"Bear left{street}"
            elif "slight right" in m_mod:
                return f"Bear right{street}"
            elif "sharp left" in m_mod:
                return f"Turn sharp left{street}"
            elif "sharp right" in m_mod:
                return f"Turn sharp right{street}"
            return f"Turn {m_mod}{street}"
        elif m_type == "continue" or m_type == "new name":
            return f"Continue straight{street}"
        
        return f"Walk straight{street}"

    def _generate_synthetic_route(self, s_lat: float, s_lon: float, e_lat: float, e_lon: float) -> Dict[str, Any]:
        """Generate a structured multi-leg walking route for offline testing."""
        # Create an L-shaped polyline path (Start -> Turn Point -> Destination)
        mid_lat = s_lat + (e_lat - s_lat) * 0.6
        mid_lon = s_lon

        coords = [
            [s_lat, s_lon],
            [mid_lat, mid_lon],
            [e_lat, e_lon]
        ]

        # Interpolate coordinates along legs to form smooth polyline
        dense_coords = []
        for i in range(len(coords) - 1):
            p1 = coords[i]
            p2 = coords[i+1]
            steps_cnt = 10
            for k in range(steps_cnt):
                frac = k / steps_cnt
                lat = p1[0] + (p2[0] - p1[0]) * frac
                lon = p1[1] + (p2[1] - p1[1]) * frac
                dense_coords.append([round(lat, 6), round(lon, 6)])
        dense_coords.append([round(e_lat, 6), round(e_lon, 6)])

        dist1 = haversine_distance(s_lat, s_lon, mid_lat, mid_lon)
        dist2 = haversine_distance(mid_lat, mid_lon, e_lat, e_lon)
        total_dist = dist1 + dist2

        turn_direction = "right" if (e_lon > s_lon) else "left"

        steps = [
            {
                "instruction": "Walk straight",
                "distance": round(dist1, 1),
                "duration": round(dist1 / 1.2, 1),
                "location": [s_lat, s_lon],
                "type": "depart",
                "modifier": "straight"
            },
            {
                "instruction": f"Turn {turn_direction}",
                "distance": round(dist2, 1),
                "duration": round(dist2 / 1.2, 1),
                "location": [mid_lat, mid_lon],
                "type": "turn",
                "modifier": turn_direction
            },
            {
                "instruction": "You have reached your destination",
                "distance": 0.0,
                "duration": 0.0,
                "location": [e_lat, e_lon],
                "type": "arrive",
                "modifier": "straight"
            }
        ]

        return {
            "distance": round(total_dist, 1),
            "duration": round(total_dist / 1.2, 1),
            "steps": steps,
            "coordinates": dense_coords
        }

    def _default_steps(self, coords: List[List[float]]) -> List[Dict[str, Any]]:
        if not coords:
            return []
        return [{
            "instruction": "Walk straight to destination",
            "distance": 100.0,
            "duration": 80.0,
            "location": coords[0],
            "type": "depart",
            "modifier": "straight"
        }]
