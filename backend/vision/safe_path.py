"""Safe Path Detector for segmenting camera field of view into walkable corridors."""
from typing import List, Dict, Any, Tuple
from backend.utils.logger import get_logger

logger = get_logger("SafePathDetector")

class SafePathDetector:
    """Evaluates LEFT, CENTER, and RIGHT corridor clearance for navigation."""
    def __init__(self, left_ratio: float = 0.33, center_ratio: float = 0.34, right_ratio: float = 0.33,
                 warning_distance: float = 2.5, critical_distance: float = 1.0):
        self.left_ratio = left_ratio
        self.center_ratio = center_ratio
        self.right_ratio = right_ratio
        self.warning_distance = warning_distance
        self.critical_distance = critical_distance

    def analyze_safe_path(self, enriched_detections: List[Dict[str, Any]],
                         frame_width: int = 640, frame_height: int = 480) -> Dict[str, Any]:
        """Classify each zone clearance and determine recommended bypass trajectory."""
        left_bound = frame_width * self.left_ratio
        right_bound = frame_width * (self.left_ratio + self.center_ratio)

        zone_obstacles = {"left": [], "center": [], "right": []}

        for det in enriched_detections:
            center_x = det.get("center", [frame_width / 2, frame_height / 2])[0]
            dist = det.get("distance_m", 10.0)

            # Determine primary zone assignment based on object center
            if center_x < left_bound:
                zone = "left"
            elif center_x < right_bound:
                zone = "center"
            else:
                zone = "right"

            det["zone"] = zone
            zone_obstacles[zone].append(det)

        # Assess risk status per zone
        zone_status = {}
        for z in ["left", "center", "right"]:
            obstacles = zone_obstacles[z]
            if not obstacles:
                zone_status[z] = "SAFE"
                continue

            min_dist = min(o.get("distance_m", 10.0) for o in obstacles)
            if min_dist <= self.critical_distance:
                zone_status[z] = "BLOCKED"
            elif min_dist <= self.warning_distance:
                zone_status[z] = "PARTIALLY BLOCKED"
            else:
                zone_status[z] = "SAFE"

        # Determine best path recommendation
        recommended_direction = "STRAIGHT"
        if zone_status["center"] == "BLOCKED":
            if zone_status["left"] == "SAFE":
                recommended_direction = "MOVE LEFT"
            elif zone_status["right"] == "SAFE":
                recommended_direction = "MOVE RIGHT"
            else:
                recommended_direction = "STOP"
        elif zone_status["center"] == "PARTIALLY BLOCKED":
            if zone_status["left"] == "SAFE":
                recommended_direction = "SLIGHT LEFT"
            elif zone_status["right"] == "SAFE":
                recommended_direction = "SLIGHT RIGHT"
            else:
                recommended_direction = "PROCEED WITH CAUTION"

        # Identify nearest obstacle
        all_obstacles = enriched_detections
        nearest_obstacle = min(all_obstacles, key=lambda x: x.get("distance_m", 99.0)) if all_obstacles else None

        return {
            "zones": zone_status,
            "recommended_direction": recommended_direction,
            "primary_obstacle": nearest_obstacle,
            "all_detections": enriched_detections
        }
