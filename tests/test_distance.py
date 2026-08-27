"""Unit tests for DistanceEstimator."""
import pytest
from backend.vision.distance_estimator import DistanceEstimator

def test_distance_estimator_person():
    estimator = DistanceEstimator(focal_length_px=500.0)
    # Bounding box for a person (height = 1.7m real-world) with height 400px in frame
    detection = {
        "class": "person",
        "height": 400
    }
    # Distance = (500 * 1.7) / 400 = 2.125m
    dist = estimator.estimate_distance(detection)
    assert 2.0 <= dist <= 2.25

def test_distance_estimator_enrichment():
    estimator = DistanceEstimator(focal_length_px=500.0)
    detections = [
        {"class": "person", "height": 300},
        {"class": "car", "height": 200}
    ]
    enriched = estimator.enrich_detections_with_distance(detections)
    assert len(enriched) == 2
    assert "distance_m" in enriched[0]
    assert "distance_m" in enriched[1]
    assert enriched[0]["distance_m"] > 0
