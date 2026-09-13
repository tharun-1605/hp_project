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
        """Classify each corridor zone clearance and determine recommended bypass trajectory."""
        left_bound = frame_width * self.left_ratio
        right_bound = frame_width * (self.left_ratio + self.center_ratio)

        zone_obstacles = {"left": [], "center": [], "right": []}

        for det in enriched_detections:
            center_x = det.get("center", [frame_width / 2, frame_height / 2])[0]
            bbox = det.get("bbox", [0, 0, 0, 0])
            x1, x2 = bbox[0] if len(bbox) >= 4 else center_x - 20, bbox[2] if len(bbox) >= 4 else center_x + 20

            in_left = x1 < left_bound or center_x < left_bound
            in_center = (x1 < right_bound and x2 > left_bound) or (left_bound <= center_x < right_bound)
            in_right = x2 > right_bound or center_x >= right_bound

            if in_center:
                zone = "center"
            elif in_left:
                zone = "left"
            else:
                zone = "right"

            det["zone"] = zone
            if in_left:
                zone_obstacles["left"].append(det)
            if in_center:
                zone_obstacles["center"].append(det)
            if in_right:
                zone_obstacles["right"].append(det)

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
        nearest_obstacle = min(enriched_detections, key=lambda x: x.get("distance_m", 99.0)) if enriched_detections else None

        return {
            "zones": zone_status,
            "recommended_direction": recommended_direction,
            "primary_obstacle": nearest_obstacle,
            "all_detections": enriched_detections
        }
