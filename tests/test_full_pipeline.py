"""Integration Test Suite for the complete 9-Stage AI Navigation Assistant Pipeline."""
import time
import pytest
import numpy as np
from backend.vision.object_detector import ObjectDetector
from backend.vision.distance_estimator import DistanceEstimator
from backend.vision.temporal_tracker import TemporalTracker
from backend.vision.safe_path import SafePathDetector
from backend.vision.risk_analyzer import RiskAnalyzer
from backend.navigation.navigation_decision import NavigationDecisionEngine, NavigationState
from backend.voice.voice_manager import VoiceManager
from scripts.train_wotr import create_dataset_structure

def test_wotr_dataset_structure():
    """Test WOTR dataset configuration file generation."""
    yaml_path = create_dataset_structure("data/wotr_test")
    assert yaml_path.exists()
    assert "data.yaml" in str(yaml_path)

def test_complete_9_stage_pipeline():
    """Verify end-to-end data flow across all 9 architecture components."""
    # 1. Camera Input (Synthetic 640x480 frame)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # 2. YOLO Object Detection
    detector = ObjectDetector(confidence=0.30)
    raw_detections = detector.detect(frame)
    assert isinstance(raw_detections, list)

    # 3. Multi-Factor Distance Estimation
    distance_estimator = DistanceEstimator(focal_length_px=500.0)
    sample_det = [
        {
            "class": "person",
            "confidence": 0.88,
            "bbox": [200, 100, 300, 400],
            "center": [250, 250],
            "width": 100,
            "height": 300
        }
    ]
    enriched_detections = distance_estimator.enrich_detections_with_distance(sample_det, frame_height=480)
    assert "distance_m" in enriched_detections[0]
    assert 0.3 <= enriched_detections[0]["distance_m"] <= 20.0

    # 4. Temporal Tracking
    tracker = TemporalTracker()
    t1 = time.time()
    tracked_f1 = tracker.update(enriched_detections, timestamp=t1)
    assert "track_id" in tracked_f1[0]
    assert tracked_f1[0]["track_id"] == 1

    # Simulate Frame 2 (Object moving closer)
    sample_det_f2 = [
        {
            "class": "person",
            "confidence": 0.90,
            "bbox": [190, 80, 310, 430],
            "center": [250, 255],
            "width": 120,
            "height": 350
        }
    ]
    enriched_f2 = distance_estimator.enrich_detections_with_distance(sample_det_f2, frame_height=480)
    t2 = t1 + 0.2
    tracked_f2 = tracker.update(enriched_f2, timestamp=t2)
    assert tracked_f2[0]["track_id"] == 1
    assert "velocity_m_s" in tracked_f2[0]

    # 5. Dynamic Risk & Collision Prediction (TTC)
    safe_path_detector = SafePathDetector()
    safe_path_analysis = safe_path_detector.analyze_safe_path(tracked_f2, frame_width=640, frame_height=480)

    risk_analyzer = RiskAnalyzer()
    risk_analysis = risk_analyzer.evaluate_risk(safe_path_analysis)
    assert "level" in risk_analysis
    assert "ttc_seconds" in risk_analysis
    assert risk_analysis["level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    # 6. Risk-Based Safe Path Selection
    assert "recommended_direction" in safe_path_analysis
    assert safe_path_analysis["zones"]["center"] in ["SAFE", "PARTIALLY BLOCKED", "BLOCKED"]

    # 7 & 8. Confidence-Aware Decision Engine & Navigation Decision
    decision_engine = NavigationDecisionEngine()
    route_status = {"is_active": True, "current_instruction": "Walk straight", "distance_to_next_turn": 50.0}
    gps_status = {"latitude": 13.0827, "longitude": 80.2707}

    decision = decision_engine.process_decision(route_status, safe_path_analysis, risk_analysis, gps_status)
    assert "instruction" in decision
    assert "priority" in decision

    # 9. Voice Assistance TTS Engine
    voice_mgr = VoiceManager(enabled=True)
    success = voice_mgr.speak(decision["instruction"], priority=decision.get("priority", "MEDIUM"))
    assert isinstance(success, bool)
