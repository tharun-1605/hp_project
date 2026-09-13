"""Temporal Tracking Engine for tracking detected objects frame-to-frame.

Assigns persistent Track IDs, tracks spatial trajectory, and computes
relative approach velocity (v = delta_distance / delta_time) for collision prediction.
"""
import time
from typing import List, Dict, Any, Tuple, Optional
from backend.utils.logger import get_logger

logger = get_logger("TemporalTracker")

def compute_iou(boxA: List[int], boxB: List[int]) -> float:
    """Calculate Intersection over Union (IoU) between two bounding boxes [x1, y1, x2, y2]."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    denom = float(boxAArea + boxBArea - interArea)
    if denom <= 0:
        return 0.0
    return interArea / denom

class TrackedObject:
    """Holds state history for a tracked obstacle."""
    def __init__(self, track_id: int, initial_detection: Dict[str, Any], timestamp: float):
        self.track_id = track_id
        self.class_name = initial_detection.get("class", "object")
        self.bbox = initial_detection.get("bbox", [0, 0, 0, 0])
        self.distance_m = initial_detection.get("distance_m", 10.0)
        self.center = initial_detection.get("center", [0, 0])
        self.last_updated = timestamp
        self.first_seen = timestamp
        self.history: List[Tuple[float, float, List[int]]] = [(timestamp, self.distance_m, self.center)] # (time, dist, center)
        self.velocity_m_s = 0.0 # positive = approaching user, negative = moving away
        self.motion_state = "STATIONARY"

    def update(self, detection: Dict[str, Any], timestamp: float):
        """Update tracker state with new frame detection."""
        dt = timestamp - self.last_updated
        new_dist = detection.get("distance_m", self.distance_m)

        if dt > 0.01:
            # Velocity = (previous_dist - new_dist) / dt (m/s)
            # Positive value means distance is decreasing -> object approaching
            inst_velocity = (self.distance_m - new_dist) / dt
            self.velocity_m_s = round(0.7 * self.velocity_m_s + 0.3 * inst_velocity, 2)

            if self.velocity_m_s > 0.25:
                self.motion_state = "APPROACHING"
            elif self.velocity_m_s < -0.25:
                self.motion_state = "RECEDING"
            else:
                self.motion_state = "STATIONARY"

        self.bbox = detection.get("bbox", self.bbox)
        self.distance_m = new_dist
        self.center = detection.get("center", self.center)
        self.last_updated = timestamp
        self.history.append((timestamp, new_dist, self.center))
        if len(self.history) > 15:
            self.history.pop(0)

class TemporalTracker:
    """Tracks objects across frames and manages track assignments."""
    def __init__(self, iou_threshold: float = 0.30, max_disappeared_seconds: float = 2.0):
        self.iou_threshold = iou_threshold
        self.max_disappeared_seconds = max_disappeared_seconds
        self.next_track_id = 1
        self.active_tracks: Dict[int, TrackedObject] = {}

    def update(self, detections: List[Dict[str, Any]], timestamp: Optional[float] = None) -> List[Dict[str, Any]]:
        """Process frame detections and attach track_id, velocity, and motion_state."""
        if timestamp is None:
            timestamp = time.time()

        assigned_track_ids = set()
        updated_detections = []

        for det in detections:
            bbox = det.get("bbox", [0, 0, 0, 0])
            cls_name = det.get("class", "")
            best_iou = 0.0
            best_track_id = None

            # Match with active tracks of same class
            for track_id, track in self.active_tracks.items():
                if track_id in assigned_track_ids:
                    continue
                if track.class_name != cls_name:
                    continue

                iou = compute_iou(bbox, track.bbox)
                if iou > best_iou and iou >= self.iou_threshold:
                    best_iou = iou
                    best_track_id = track_id

            if best_track_id is not None:
                track = self.active_tracks[best_track_id]
                track.update(det, timestamp)
                assigned_track_ids.add(best_track_id)
            else:
                # Create new track
                best_track_id = self.next_track_id
                self.next_track_id += 1
                new_track = TrackedObject(best_track_id, det, timestamp)
                self.active_tracks[best_track_id] = new_track
                assigned_track_ids.add(best_track_id)

            track = self.active_tracks[best_track_id]
            det_copy = dict(det)
            det_copy["track_id"] = track.track_id
            det_copy["velocity_m_s"] = track.velocity_m_s
            det_copy["motion_state"] = track.motion_state
            updated_detections.append(det_copy)

        # Cleanup stale tracks
        stale_ids = [
            t_id for t_id, track in self.active_tracks.items()
            if (timestamp - track.last_updated) > self.max_disappeared_seconds
        ]
        for t_id in stale_ids:
            del self.active_tracks[t_id]

        return updated_detections
