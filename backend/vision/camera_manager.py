"""Camera Manager for frame acquisition, resizing, throttling, and simulation."""
import cv2
import time
import math
import numpy as np
from typing import Tuple, Optional, Union
from backend.utils.logger import get_logger

logger = get_logger("CameraManager")

class CameraManager:
    """Manages video capture hardware, frame rates, resizing, and synthetic fallback."""
    def __init__(self, device: Union[int, str] = 0, width: int = 640, height: int = 480, target_fps: int = 15):
        self.device = device
        self.width = width
        self.height = height
        self.target_fps = target_fps
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.frame_count = 0
        self.start_time = time.time()
        self.current_fps = 0.0
        self.use_simulation = False

    def start(self) -> bool:
        """Initialize camera device or fallback to synthetic simulation."""
        logger.info(f"Opening camera device: {self.device}")
        try:
            self.cap = cv2.VideoCapture(self.device)
            if self.cap and self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.is_running = True
                logger.info("Camera opened successfully.")
                return True
        except Exception as e:
            logger.warning(f"Failed to open hardware camera: {e}")

        logger.info("Falling back to synthetic camera frame generator.")
        self.use_simulation = True
        self.is_running = True
        return True

    def read_frame(self) -> Tuple[bool, np.ndarray]:
        """Read and resize a single frame from camera or synthetic generator."""
        if not self.is_running:
            return False, self._create_blank_frame()

        if self.use_simulation or not self.cap or not self.cap.isOpened():
            frame = self._generate_synthetic_frame()
            self._update_fps()
            return True, frame

        ret, frame = self.cap.read()
        if not ret:
            logger.warning("Camera read error. Returning synthetic frame.")
            return True, self._generate_synthetic_frame()

        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))

        self._update_fps()
        return True, frame

    def _update_fps(self):
        self.frame_count += 1
        elapsed = time.time() - self.start_time
        if elapsed >= 1.0:
            self.current_fps = round(self.frame_count / elapsed, 1)
            self.frame_count = 0
            self.start_time = time.time()

    def _generate_synthetic_frame(self) -> np.ndarray:
        """Generate a simulated camera frame for indoor/outdoor testing."""
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        # Background gradient (road / sidewalk)
        img[0:int(self.height*0.5), :] = [200, 180, 150] # Sky/buildings
        img[int(self.height*0.5):, :] = [80, 80, 80]     # Asphalt / path

        # Draw sidewalk lines
        cv2.line(img, (int(self.width*0.2), self.height), (int(self.width*0.45), int(self.height*0.5)), (255, 255, 255), 2)
        cv2.line(img, (int(self.width*0.8), self.height), (int(self.width*0.55), int(self.height*0.5)), (255, 255, 255), 2)

        # Dynamic simulated person moving
        t = time.time()
        pos_x = int((self.width / 2) + math.sin(t * 0.8) * 150)
        scale = 0.8 + 0.2 * math.cos(t * 0.5)

        # Draw a simulated obstacle bounding region
        color = (0, 165, 255) # Orange
        pt1 = (int(pos_x - 30 * scale), int(self.height * 0.6))
        pt2 = (int(pos_x + 30 * scale), int(self.height * 0.95))
        cv2.rectangle(img, pt1, pt2, color, 2)
        cv2.putText(img, "Simulated Pedestrian", (pt1[0], pt1[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Timestamp overlay
        cv2.putText(img, f"FPS: {self.current_fps} | Mode: Sim", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        return img

    def _create_blank_frame(self) -> np.ndarray:
        return np.zeros((self.height, self.width, 3), dtype=np.uint8)

    def stop(self):
        """Release camera resources."""
        self.is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        logger.info("Camera stopped.")
