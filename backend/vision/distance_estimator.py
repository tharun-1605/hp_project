"""Multi-Factor Monocular Distance Estimator.

Combines camera pinhole geometry, ground-plane pixel position ($y_2$),
aspect ratio verification, and confidence weighting for robust distance estimation.
"""
from typing import Dict, Any, List
from backend.utils.logger import get_logger

logger = get_logger("DistanceEstimator")

# Real-world estimated dimensions (in meters) [height, width]
REAL_WORLD_DIMENSIONS: Dict[str, List[float]] = {
    "person": [1.70, 0.50],
    "car": [1.50, 1.80],
    "bus": [3.20, 2.55],
    "truck": [3.50, 2.50],
    "bicycle": [1.10, 0.60],
    "motorcycle": [1.10, 0.70],
    "dog": [0.60, 0.35],
    "chair": [0.90, 0.50],
    "table": [0.75, 1.20],
    "dining table": [0.75, 1.20],
    "couch": [0.85, 1.80],
    "bench": [0.80, 1.20],
    "backpack": [0.50, 0.35],
    "suitcase": [0.65, 0.45],
    "bottle": [0.25, 0.08],
    "traffic light": [1.00, 0.35],
    "stop sign": [0.90, 0.90],
    "pole": [2.50, 0.25],
    "pothole": [0.15, 0.60],
    "staircase": [1.20, 1.00],
    "curb": [0.20, 1.00],
    "traffic_cone": [0.70, 0.35],
    "trash_can": [0.90, 0.50],
    "low_hanging_branch": [1.50, 1.50],
    "barrier": [1.00, 1.50]
}

DEFAULT_REAL_HEIGHT_METERS = 1.00
DEFAULT_REAL_WIDTH_METERS = 0.50

class DistanceEstimator:
    """Multi-factor distance estimator integrating height geometry, ground plane, and aspect ratio."""

    def __init__(self, focal_length_px: float = 500.0, camera_height_m: float = 1.40):
        self.focal_length_px = focal_length_px
        self.camera_height_m = camera_height_m # Height of user's handheld or wearable camera from ground

    def estimate_distance(self, detection: Dict[str, Any], frame_height: int = 480) -> float:
        """Calculate multi-factor distance in meters for a given detection object."""
        class_name = detection.get("class", "unknown").lower()
        box_height_px = float(detection.get("height", 0))
        box_width_px = float(detection.get("width", 0))
        bbox = detection.get("bbox", [])

        if box_height_px <= 0:
            return 10.0 # Default safe fallback distance if box invalid

        dims = REAL_WORLD_DIMENSIONS.get(class_name, [DEFAULT_REAL_HEIGHT_METERS, DEFAULT_REAL_WIDTH_METERS])
        real_height_m, real_width_m = dims[0], dims[1]

        # Factor 1: Pinhole Height Geometry (D_h = f * H / h)
        dist_height = (self.focal_length_px * real_height_m) / box_height_px

        # If full bbox coordinates are not present, fallback directly to pure height geometry
        if not bbox or len(bbox) < 4 or bbox[3] <= 0:
            return max(0.3, min(20.0, round(dist_height, 2)))

        y2 = float(bbox[3])
        # Factor 2: Ground-plane Projection Distance (D_g = f * H_cam / (y2 - y_horizon))
        horizon_y = frame_height * 0.45
        y_offset = max(5.0, y2 - horizon_y)
        dist_ground = (self.focal_length_px * self.camera_height_m) / y_offset

        # Factor 3: Pinhole Width Geometry (D_w = f * W / w) as cross-check if width valid
        dist_width = (self.focal_length_px * real_width_m) / box_width_px if box_width_px > 0 else dist_height

        # Multi-factor Fusion
        if class_name in {"pothole", "curb", "staircase"}:
            distance_m = 0.70 * dist_ground + 0.30 * dist_height
        else:
            distance_m = 0.55 * dist_height + 0.30 * dist_ground + 0.15 * dist_width

        # Cap output between 0.3m and 20.0m for realistic navigation range
        distance_m = max(0.3, min(20.0, round(float(distance_m), 2)))
        return distance_m

    def enrich_detections_with_distance(self, detections: List[Dict[str, Any]], frame_height: int = 480) -> List[Dict[str, Any]]:
        """Enrich detection objects with multi-factor distance estimates."""
        enriched = []
        for det in detections:
            det_copy = dict(det)
            det_copy["distance_m"] = self.estimate_distance(det_copy, frame_height)
            enriched.append(det_copy)
        return enriched
