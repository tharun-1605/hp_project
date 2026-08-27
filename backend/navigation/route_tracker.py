"""Route Tracker for tracking progress along polyline, distance to next turn, and deviation detection."""
from typing import Dict, Any, List, Tuple, Optional
from backend.utils.spatial import haversine_distance, point_to_segment_distance
from backend.utils.logger import get_logger

logger = get_logger("RouteTracker")

class RouteTracker:
    """Tracks position relative to active route and detects route deviation."""

    def __init__(self, deviation_threshold_m: float = 15.0):
        self.deviation_threshold_m = deviation_threshold_m
        self.active_route: Optional[Dict[str, Any]] = None
        self.current_step_index = 0
        self.is_route_active = False

    def load_route(self, route_data: Dict[str, Any]):
        """Load a new active route calculated by RoutingEngine."""
        self.active_route = route_data
        self.current_step_index = 0
        self.is_route_active = True
        logger.info(f"Loaded new active route ({route_data.get('distance', 0)}m, {len(route_data.get('steps', []))} steps).")

    def update_position(self, current_lat: float, current_lon: float) -> Dict[str, Any]:
        """Update tracker with user's current GPS coordinate and evaluate progress."""
        if not self.is_route_active or not self.active_route:
            return {
                "is_active": False,
                "distance_to_destination": 0.0,
                "current_instruction": "No active route",
                "distance_to_next_turn": 0.0,
                "is_deviated": False,
                "has_reached_destination": False
            }

        steps = self.active_route.get("steps", [])
        coords = self.active_route.get("coordinates", [])

        if not steps or not coords:
            return {"is_active": False}

        # Calculate distance to final destination
        end_coord = coords[-1]
        dist_to_dest = haversine_distance(current_lat, current_lon, end_coord[0], end_coord[1])

        # Check if destination reached (< 8.0 meters)
        if dist_to_dest <= 8.0 or self.current_step_index >= len(steps) - 1:
            self.is_route_active = False
            return {
                "is_active": True,
                "distance_to_destination": round(dist_to_dest, 1),
                "current_instruction": "You have reached your destination",
                "distance_to_next_turn": 0.0,
                "is_deviated": False,
                "has_reached_destination": True
            }

        # Get current maneuver step and next maneuver step location
        current_step = steps[self.current_step_index]
        next_step_loc = current_step.get("location", coords[0])
        dist_to_turn = haversine_distance(current_lat, current_lon, next_step_loc[0], next_step_loc[1])

        # Advance step if within 6 meters of turn maneuver point
        if dist_to_turn <= 6.0 and self.current_step_index < len(steps) - 1:
            self.current_step_index += 1
            current_step = steps[self.current_step_index]
            next_step_loc = current_step.get("location", end_coord)
            dist_to_turn = haversine_distance(current_lat, current_lon, next_step_loc[0], next_step_loc[1])
            logger.info(f"Advanced to route step {self.current_step_index}: '{current_step.get('instruction')}'")

        # Check perpendicular deviation from route polyline
        is_deviated = self._check_route_deviation(current_lat, current_lon, coords)

        return {
            "is_active": True,
            "distance_to_destination": round(dist_to_dest, 1),
            "current_instruction": current_step.get("instruction", "Walk straight"),
            "distance_to_next_turn": round(dist_to_turn, 1),
            "step_index": self.current_step_index,
            "total_steps": len(steps),
            "is_deviated": is_deviated,
            "has_reached_destination": False
        }

    def _check_route_deviation(self, lat: float, lon: float, coords: List[List[float]]) -> bool:
        """Check if current location is farther than threshold from any route segment."""
        if len(coords) < 2:
            return False

        min_poly_dist = float("inf")
        # Check line segments near current progress
        for i in range(len(coords) - 1):
            p1 = coords[i]
            p2 = coords[i+1]
            seg_d = point_to_segment_distance(lat, lon, p1[0], p1[1], p2[0], p2[1])
            if seg_d < min_poly_dist:
                min_poly_dist = seg_d

        return min_poly_dist > self.deviation_threshold_m
