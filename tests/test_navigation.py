"""Unit tests for navigation module: MapManager, RoutingEngine, RouteTracker, and NavigationDecisionEngine."""
import pytest
from backend.navigation.map_manager import MapManager
from backend.navigation.routing_engine import RoutingEngine
from backend.navigation.route_tracker import RouteTracker
from backend.navigation.gps_manager import GPSManager
from backend.navigation.navigation_decision import NavigationDecisionEngine, NavigationState

def test_map_manager_preset_lookup():
    map_mgr = MapManager()
    res = map_mgr.search_destination("Railway Station")
    assert res is not None
    assert "railway station" in res["name"].lower()
    assert "latitude" in res and "longitude" in res

def test_routing_engine_synthetic_fallback():
    engine = RoutingEngine(osrm_server="http://invalid-server-url-12345.org")
    route = engine.calculate_route(11.0025, 76.9620, 11.0080, 76.9670)
    assert "distance" in route
    assert route["distance"] > 0
    assert len(route["steps"]) >= 2
    assert len(route["coordinates"]) > 0

def test_route_tracker_and_deviation():
    tracker = RouteTracker(deviation_threshold_m=15.0)
    mock_route = {
        "distance": 500,
        "steps": [
            {"instruction": "Walk straight", "location": [11.0025, 76.9620]},
            {"instruction": "Turn right", "location": [11.0050, 76.9620]}
        ],
        "coordinates": [
            [11.0025, 76.9620],
            [11.0050, 76.9620]
        ]
    }
    tracker.load_route(mock_route)

    # Position on route
    status = tracker.update_position(11.0030, 76.9620)
    assert status["is_active"] is True
    assert status["is_deviated"] is False
    assert "Walk straight" in status["current_instruction"]

    # Position far off route (> 15m)
    off_status = tracker.update_position(11.0030, 76.9900)
    assert off_status["is_deviated"] is True

def test_decision_engine_critical_obstacle_priority():
    decision_engine = NavigationDecisionEngine()
    route_status = {
        "is_active": True,
        "current_instruction": "Continue straight for 100 meters.",
        "distance_to_next_turn": 50.0,
        "is_deviated": False,
        "has_reached_destination": False
    }
    safe_path = {
        "zones": {"left": "SAFE", "center": "BLOCKED", "right": "SAFE"},
        "recommended_direction": "MOVE LEFT",
        "primary_obstacle": {"class": "wall", "distance_m": 0.7, "zone": "center"}
    }
    risk_analysis = {
        "level": "CRITICAL",
        "reason": "Wall directly ahead at 0.7 meters!"
    }
    gps_status = {"latitude": 11.0025, "longitude": 76.9620}

    # Decision engine must prioritize CRITICAL obstacle over route instruction
    output = decision_engine.process_decision(route_status, safe_path, risk_analysis, gps_status)
    assert output["priority"] == "CRITICAL"
    assert "Stop" in output["instruction"]
    assert output["action"] == "STOP"
    assert output["instruction"] != "Continue straight for 100 meters."
