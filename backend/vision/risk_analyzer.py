"""Risk Analyzer for assessing environmental danger levels."""
from typing import Dict, Any
from backend.utils.logger import get_logger

logger = get_logger("RiskAnalyzer")

# High vulnerability objects (moving / large objects)
HIGH_VULNERABILITY_CLASSES = {"person", "car", "bus", "truck", "motorcycle", "bicycle", "dog"}

class RiskAnalyzer:
    """Evaluates risk levels: LOW, MEDIUM, HIGH, CRITICAL based on vision telemetry."""

    def evaluate_risk(self, safe_path_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Compute overall risk level and return risk summary."""
        primary_obs = safe_path_analysis.get("primary_obstacle")
        zones = safe_path_analysis.get("zones", {})

        if not primary_obs:
            return {
                "level": "LOW",
                "score": 0.0,
                "reason": "No obstacles detected in visual field.",
                "action": "CONTINUE"
            }

        class_name = primary_obs.get("class", "object").lower()
        distance = primary_obs.get("distance_m", 10.0)
        zone = primary_obs.get("zone", "center")

        # Base score starts from distance inverse
        # Distance <= 0.8m -> Score ~ 1.0, Distance >= 4.0m -> Score ~ 0.1
        distance_score = max(0.0, min(1.0, (3.5 - distance) / 3.0))
        
        # Multipliers
        zone_multiplier = 1.5 if zone == "center" else 0.8
        class_multiplier = 1.3 if class_name in HIGH_VULNERABILITY_CLASSES else 1.0

        risk_score = round(distance_score * zone_multiplier * class_multiplier, 2)

        if distance <= 0.9 or risk_score >= 1.2 or zones.get("center") == "BLOCKED":
            level = "CRITICAL"
            reason = f"{class_name.capitalize()} directly ahead at {distance} meters!"
            action = "STOP_IMMEDIATELY"
        elif distance <= 1.8 or risk_score >= 0.7 or zones.get("center") == "PARTIALLY BLOCKED":
            level = "HIGH"
            reason = f"{class_name.capitalize()} ahead at {distance} meters."
            action = "PREPARE_TO_AVOID"
        elif distance <= 2.8 or risk_score >= 0.4:
            level = "MEDIUM"
            reason = f"Approaching {class_name} at {distance} meters."
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
            "zone": zone
        }
