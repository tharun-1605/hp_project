"""Monocular Distance Estimator based on camera pinhole geometry and object heuristics."""
from typing import Dict, Any
from backend.utils.logger import get_logger

logger = get_logger("DistanceEstimator")

# Real-world object height estimates (in meters)
REAL_WORLD_HEIGHTS_METERS: Dict[str, float] = {
    "person": 1.70,
    "car": 1.50,
    "bus": 3.20,
    "truck": 3.50,
    "bicycle": 1.10,
    "motorcycle": 1.10,
    "dog": 0.60,
    "chair": 0.90,
    "table": 0.75,
    "dining table": 0.75,
    "couch": 0.85,
    "bench": 0.80,
    "backpack": 0.50,
    "suitcase": 0.65,
    "bottle": 0.25,
    "traffic light": 1.00,
    "stop sign": 0.90
}
DEFAULT_REAL_HEIGHT_METERS = 1.00

class DistanceEstimator:
    """Estimates object distance using monocular bounding box proportions."""
    def __init__(self, focal_length_px: float = 500.0):
        self.focal_length_px = focal_length_px

    def estimate_distance(self, detection: Dict[str, Any], frame_height: int = 480) -> float:
        """Calculate approximate distance in meters for a given detection object."""
        class_name = detection.get("class", "unknown").lower()
        box_height_px = float(detection.get("height", 0))

        if box_height_px <= 0:
            return 10.0 # Default safe fallback distance if box invalid

        real_height_m = REAL_WORLD_HEIGHTS_METERS.get(class_name, DEFAULT_REAL_HEIGHT_METERS)
        
        # Pinhole camera distance formula: D = (focal_length * real_height) / bbox_height_px
        distance_m = (self.focal_length_px * real_height_m) / box_height_px

        # Cap output between 0.3m and 20.0m for realistic navigation range
        distance_m = max(0.3, min(20.0, round(distance_m, 2)))
        return distance_m

    def enrich_detections_with_distance(self, detections: list, frame_height: int = 480) -> list:
        """Enrich a list of detection objects with distance estimates and zone information."""
        enriched = []
        for det in detections:
            det_copy = dict(det)
            det_copy["distance_m"] = self.estimate_distance(det_copy, frame_height)
            enriched.append(det_copy)
        return enriched
