"""GPS Manager for location tracking, bearing calculation, speed measurement, and route simulation."""
import time
from typing import Dict, Any, List, Optional, Tuple
from backend.utils.spatial import haversine_distance, calculate_bearing
from backend.utils.logger import get_logger

logger = get_logger("GPSManager")

class GPSManager:
    """Manages GPS telemetry with abstraction for physical devices and simulation."""

    def __init__(self, initial_lat: float = 11.0025, initial_lon: float = 76.9620, is_mock: bool = True):
        self.latitude = initial_lat
        self.longitude = initial_lon
        self.accuracy = 3.0 # meters
        self.bearing = 0.0 # compass degrees
        self.speed = 1.2 # walking speed ~1.2 m/s
        self.is_mock = is_mock

        # Simulation trajectory state
        self._sim_waypoints: List[Tuple[float, float]] = []
        self._sim_step_index = 0
        self._sim_progress = 0.0 # 0.0 to 1.0 along current segment
        self.last_update_time = time.time()

    def get_location(self) -> Dict[str, Any]:
        """Return current GPS position, bearing, speed, and status."""
        return {
            "latitude": round(self.latitude, 6),
            "longitude": round(self.longitude, 6),
            "accuracy_m": self.accuracy,
            "bearing": round(self.bearing, 1),
            "speed_mps": round(self.speed, 2),
            "is_mock": self.is_mock,
            "timestamp": time.time()
        }

    def update_location(self, lat: float, lon: float, accuracy: float = 3.0, speed: float = 1.2, bearing: Optional[float] = None):
        """Update location from external physical GPS feed."""
        if bearing is None and (lat != self.latitude or lon != self.longitude):
            bearing = calculate_bearing(self.latitude, self.longitude, lat, lon)
        elif bearing is None:
            bearing = self.bearing

        self.latitude = lat
        self.longitude = lon
        self.accuracy = accuracy
        self.speed = speed
        self.bearing = bearing
        self.last_update_time = time.time()

    def set_simulation_route(self, waypoints: List[Tuple[float, float]]):
        """Load a set of GPS coordinates to simulate step-by-step movement along a route."""
        if not waypoints:
            return
        self._sim_waypoints = waypoints
        self._sim_step_index = 0
        self._sim_progress = 0.0
        self.latitude = waypoints[0][0]
        self.longitude = waypoints[0][1]
        self.is_mock = True
        logger.info(f"Loaded simulation route with {len(waypoints)} waypoints.")

    def step_simulation(self, delta_time: float = 1.0) -> Dict[str, Any]:
        """Advance simulated GPS location along loaded route polyline."""
        if not self._sim_waypoints or len(self._sim_waypoints) < 2:
            return self.get_location()

        if self._sim_step_index >= len(self._sim_waypoints) - 1:
            # Reached end of simulation route
            self.speed = 0.0
            return self.get_location()

        p1 = self._sim_waypoints[self._sim_step_index]
        p2 = self._sim_waypoints[self._sim_step_index + 1]

        seg_dist = haversine_distance(p1[0], p1[1], p2[0], p2[1])
        if seg_dist <= 0.1:
            self._sim_step_index += 1
            return self.step_simulation(delta_time)

        step_dist = self.speed * delta_time
        fraction_increase = step_dist / seg_dist
        self._sim_progress += fraction_increase

        if self._sim_progress >= 1.0:
            self._sim_step_index += 1
            self._sim_progress = 0.0
            if self._sim_step_index >= len(self._sim_waypoints) - 1:
                self.latitude, self.longitude = self._sim_waypoints[-1]
                self.speed = 0.0
                return self.get_location()
            p1 = self._sim_waypoints[self._sim_step_index]
            p2 = self._sim_waypoints[self._sim_step_index + 1]

        # Interpolate coordinate
        new_lat = p1[0] + (p2[0] - p1[0]) * self._sim_progress
        new_lon = p1[1] + (p2[1] - p1[1]) * self._sim_progress

        self.bearing = calculate_bearing(self.latitude, self.longitude, new_lat, new_lon)
        self.latitude = new_lat
        self.longitude = new_lon
        self.last_update_time = time.time()

        return self.get_location()
