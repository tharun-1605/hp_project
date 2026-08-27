"""Unit tests for SafePathDetector and RiskAnalyzer."""
import pytest
from backend.vision.safe_path import SafePathDetector
from backend.vision.risk_analyzer import RiskAnalyzer

def test_safe_path_center_blocked_recommendation():
    detector = SafePathDetector(warning_distance=2.5, critical_distance=1.0)
    # Person at center corridor (x = 320 in 640px frame) at distance 0.8m (BLOCKED)
    enriched_dets = [
        {
            "class": "person",
            "distance_m": 0.8,
            "center": [320, 240],
            "bbox": [280, 100, 360, 380]
        }
    ]

    analysis = detector.analyze_safe_path(enriched_dets, frame_width=640, frame_height=480)
    assert analysis["zones"]["center"] == "BLOCKED"
    assert analysis["zones"]["left"] == "SAFE"
    assert analysis["zones"]["right"] == "SAFE"
    assert analysis["recommended_direction"] == "MOVE LEFT"

def test_risk_analyzer_critical():
    analyzer = RiskAnalyzer()
    safe_path_analysis = {
        "zones": {"left": "SAFE", "center": "BLOCKED", "right": "SAFE"},
        "recommended_direction": "MOVE LEFT",
        "primary_obstacle": {
            "class": "car",
            "distance_m": 0.7,
            "zone": "center"
        }
    }
    risk = analyzer.evaluate_risk(safe_path_analysis)
    assert risk["level"] == "CRITICAL"
    assert risk["action"] == "STOP_IMMEDIATELY"
