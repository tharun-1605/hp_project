"""Unit tests for CameraManager and ObjectDetector."""
import numpy as np
import pytest
from backend.vision.camera_manager import CameraManager
from backend.vision.object_detector import ObjectDetector

def test_camera_manager_simulation():
    cam = CameraManager(width=640, height=480, target_fps=15)
    started = cam.start()
    assert started is True

    ret, frame = cam.read_frame()
    assert ret is True
    assert isinstance(frame, np.ndarray)
    assert frame.shape == (480, 640, 3)
    cam.stop()

def test_object_detector_structure():
    detector = ObjectDetector(confidence=0.45)
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detections = detector.detect(dummy_frame)

    assert isinstance(detections, list)
    if detections:
        det = detections[0]
        assert "class" in det
        assert "confidence" in det
        assert "bbox" in det
        assert "center" in det
        assert len(det["bbox"]) == 4
        assert len(det["center"]) == 2
