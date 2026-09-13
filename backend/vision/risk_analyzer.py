"""Dynamic Risk Analyzer incorporating Time-To-Collision (TTC) and motion prediction."""
from typing import Dict, Any, Optional
from backend.utils.logger import get_logger

logger = get_logger("RiskAnalyzer")

# High vulnerability objects (fast moving or large collision hazards)
HIGH_VULNERABILITY_CLASSES = {
    "person", "car", "bus", "truck", "motorcycle", "bicycle", "dog",
    "staircase", "pothole", "curb", "barrier"
}

# Assumed average human walking speed (m/s) if user is approaching stationary obstacle
DEFAULT_USER_WALKING_SPEED = 1.10

class RiskAnalyzer:
    """Evaluates environmental danger levels (LOW, MEDIUM, HIGH, CRITICAL) using TTC + Distance + Motion."""

    def evaluate_risk(self, safe_path_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Compute dynamic risk level and return risk telemetry."""
        primary_obs = safe_path_analysis.get("primary_obstacle")
        zones = safe_path_analysis.get("zones", {})

        if not primary_obs:
            return {
                "level": "LOW",
                "score": 0.0,
                "reason": "No obstacles detected in visual field.",
                "action": "CONTINUE",
                "ttc_seconds": 99.0
            }

        class_name = primary_obs.get("class", "object").lower()
        distance = float(primary_obs.get("distance_m", 10.0))
        zone = primary_obs.get("zone", "center")
        velocity = float(primary_obs.get("velocity_m_s", 0.0))
        motion_state = primary_obs.get("motion_state", "STATIONARY")
        track_id = primary_obs.get("track_id")

        # Time-To-Collision (TTC) Calculation
        # Effective closing speed = user speed (1.1m/s) + object approach velocity
        closing_speed = DEFAULT_USER_WALKING_SPEED + max(0.0, velocity)
        ttc_seconds = round(distance / max(0.1, closing_speed), 2)

        # Base score starts from TTC and distance
        # Distance <= 0.8m or TTC <= 1.2s -> Score ~ 1.0
        ttc_score = max(0.0, min(1.0, (4.5 - ttc_seconds) / 3.5))
        distance_score = max(0.0, min(1.0, (3.5 - distance) / 3.0))

        # Multipliers
        zone_multiplier = 1.5 if zone == "center" else 0.9
        class_multiplier = 1.3 if class_name in HIGH_VULNERABILITY_CLASSES else 1.0
        motion_multiplier = 1.4 if motion_state == "APPROACHING" else 1.0

        risk_score = round((0.6 * ttc_score + 0.4 * distance_score) * zone_multiplier * class_multiplier * motion_multiplier, 2)

        # Decision threshold logic
        if distance <= 0.9 or ttc_seconds <= 1.5 or risk_score >= 1.2 or zones.get("center") == "BLOCKED":
            level = "CRITICAL"
            reason = f"CRITICAL: {class_name.capitalize()} in center at {distance}m (TTC: {ttc_seconds}s)!"
            action = "STOP_IMMEDIATELY"
        elif distance <= 1.8 or ttc_seconds <= 2.8 or risk_score >= 0.7 or zones.get("center") == "PARTIALLY BLOCKED":
            level = "HIGH"
            reason = f"HIGH RISK: {class_name.capitalize()} ahead at {distance}m (TTC: {ttc_seconds}s)."
            action = "PREPARE_TO_AVOID"
        elif distance <= 2.8 or ttc_seconds <= 4.0 or risk_score >= 0.4:
            level = "MEDIUM"
            reason = f"MEDIUM: Approaching {class_name} at {distance}m."
            action = "MONITOR"
        else:
            level = "LOW"
            reason = f"{class_name.capitalize()} detected at safe distance ({distance}m)."
            action = "CONTINUE"

        return {
            "level": level,
            "score": risk_score,
            "reason": reason,
            "action": action,
            "obstacle_class": class_name,
            "distance_m": distance,
            "ttc_seconds": ttc_seconds,
            "motion_state": motion_state,
            "zone": zone,
            "track_id": track_id
        }
