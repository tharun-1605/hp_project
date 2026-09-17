#!/usr/bin/env python3
"""Main Application Entry Point for VisionNav (FastAPI Server + WebSocket Telemetry Stream)."""
import os
import sys
import time
import asyncio
import base64
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

# Add project root to Python import path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.config import load_settings
from backend.utils.logger import get_logger
from backend.vision.camera_manager import CameraManager
from backend.vision.object_detector import ObjectDetector
from backend.vision.distance_estimator import DistanceEstimator
from backend.vision.temporal_tracker import TemporalTracker
from backend.vision.safe_path import SafePathDetector
from backend.vision.risk_analyzer import RiskAnalyzer
from backend.navigation.gps_manager import GPSManager
from backend.navigation.map_manager import MapManager
from backend.navigation.routing_engine import RoutingEngine
from backend.navigation.route_tracker import RouteTracker
from backend.navigation.navigation_decision import NavigationDecisionEngine, NavigationState
from backend.voice.speech_recognition import SpeechRecognizer
from backend.voice.command_processor import CommandProcessor
from backend.voice.voice_manager import VoiceManager
from backend.utils.discovery_service import discovery_server

logger = get_logger("VisionNavMain")

# Load configuration settings
settings = load_settings()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting VisionNav system in '{current_mode}' mode...")
    env_port = int(os.getenv("VISIONNAV_PORT", "8000"))
    discovery_server.start(port=env_port)
    camera_mgr.start()
    voice_mgr.speak("VisionNav system initialized. Ready for navigation.", priority="HIGH")
    yield
    logger.info("Shutting down VisionNav system...")
    discovery_server.stop()
    camera_mgr.stop()

app = FastAPI(
    title=settings["app"]["name"],
    version=settings["app"]["version"],
    description="Open-Source AI Navigation Assistant for Visually Impaired People",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core system modules
camera_mgr = CameraManager(
    device=settings["camera"]["device"],
    width=settings["camera"]["width"],
    height=settings["camera"]["height"],
    target_fps=settings["camera"]["target_fps"]
)
detector = ObjectDetector(
    model_path=settings["detection"]["model_path"],
    confidence=settings["detection"]["confidence"],
    device=settings["detection"]["device"]
)
distance_estimator = DistanceEstimator(focal_length_px=settings["distance"]["focal_length_px"])
temporal_tracker = TemporalTracker()
safe_path_detector = SafePathDetector(
    warning_distance=settings["distance"]["warning_distance"],
    critical_distance=settings["distance"]["critical_distance"]
)
risk_analyzer = RiskAnalyzer()
gps_mgr = GPSManager(is_mock=True)
map_mgr = MapManager(nominatim_url=settings["navigation"]["nominatim_server"])
routing_engine = RoutingEngine(osrm_server=settings["navigation"]["osrm_server"])
route_tracker = RouteTracker(deviation_threshold_m=settings["navigation"]["deviation_threshold_meters"])
decision_engine = NavigationDecisionEngine()
speech_recognizer = SpeechRecognizer(model_path=settings["voice"]["vosk_model_path"])
command_processor = CommandProcessor()
voice_mgr = VoiceManager(
    piper_model_path=settings["voice"]["piper_model_path"],
    cooldown_seconds=settings["voice"]["cooldown_seconds"],
    enabled=settings["voice"]["enabled"],
    engine=settings["voice"]["engine"]
)

# Active mode & telemetry state
current_mode = settings["app"]["default_mode"] # simulation, camera_test, full_navigation
active_websockets: List[WebSocket] = []
latest_telemetry: Dict[str, Any] = {}

class CommandRequest(BaseModel):
    command: str

class DestinationRequest(BaseModel):
    destination: str

class FrameUploadRequest(BaseModel):
    frame_b64: str

# --- REST API Endpoints ---

@app.post("/api/camera/frame")
def upload_camera_frame(req: FrameUploadRequest):
    success = camera_mgr.push_external_frame(req.frame_b64)
    if success:
        return {"status": "success", "source": "phone_camera"}
    raise HTTPException(status_code=400, detail="Failed to process camera frame.")

from fastapi import Request

@app.get("/api/discover")
def discover(request: Request):
    actual_port = request.url.port or discovery_server.target_port
    if request.url.port:
        discovery_server.set_target_port(request.url.port)
    return {
        "service": "VisionNav",
        "status": "online",
        "name": "VisionNav Backend Server",
        "version": "1.0.0",
        "port": actual_port
    }

@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "mode": current_mode,
        "state": decision_engine.state,
        "camera_fps": camera_mgr.current_fps,
        "camera_running": camera_mgr.is_running,
        "voice_enabled": voice_mgr.enabled
    }

@app.get("/api/location")
def get_location():
    return gps_mgr.get_location()

@app.post("/api/mode")
def set_mode(mode: str = Body(..., embed=True)):
    global current_mode
    if mode in ["simulation", "camera_test", "full_navigation"]:
        current_mode = mode
        logger.info(f"Switched system mode to: '{mode}'")
        voice_mgr.speak(f"Switched to {mode.replace('_', ' ')} mode.", priority="HIGH")
        return {"status": "success", "mode": current_mode}
    raise HTTPException(status_code=400, detail="Invalid mode specified.")

@app.post("/api/navigation/start")
def start_navigation(req: DestinationRequest):
    dest_info = map_mgr.search_destination(req.destination, gps_mgr.latitude, gps_mgr.longitude)
    if not dest_info:
        raise HTTPException(status_code=404, detail="Destination location not found.")

    curr_loc = gps_mgr.get_location()
    route = routing_engine.calculate_route(
        curr_loc["latitude"], curr_loc["longitude"],
        dest_info["latitude"], dest_info["longitude"]
    )

    route_tracker.load_route(route)
    decision_engine.destination_name = dest_info["name"]
    decision_engine.state = NavigationState.NAVIGATING

    if route.get("coordinates"):
        gps_mgr.set_simulation_route(route["coordinates"])

    voice_mgr.speak(f"Navigation started to {dest_info['name']}.", priority="HIGH", force=True)
    return {
        "status": "started",
        "destination": dest_info,
        "route": route
    }

@app.post("/api/navigation/stop")
def stop_navigation():
    route_tracker.is_route_active = False
    decision_engine.state = NavigationState.STOPPED
    voice_mgr.speak("Navigation stopped.", priority="HIGH", force=True)
    return {"status": "stopped"}

@app.post("/api/navigation/pause")
def pause_navigation():
    decision_engine.state = NavigationState.PAUSED
    voice_mgr.speak("Navigation paused.", priority="MEDIUM")
    return {"status": "paused"}

@app.post("/api/navigation/resume")
def resume_navigation():
    if route_tracker.active_route:
        decision_engine.state = NavigationState.NAVIGATING
        voice_mgr.speak("Resuming navigation.", priority="MEDIUM")
        return {"status": "resumed"}
    raise HTTPException(status_code=400, detail="No active route to resume.")

@app.get("/api/navigation/status")
def get_navigation_status():
    curr_loc = gps_mgr.get_location()
    route_stat = route_tracker.update_position(curr_loc["latitude"], curr_loc["longitude"])
    return {
        "state": decision_engine.state,
        "destination": decision_engine.destination_name,
        "route_status": route_stat,
        "gps": curr_loc
    }

@app.post("/api/voice/command")
def process_voice_command(req: CommandRequest):
    intent_data = command_processor.parse_command(req.command)
    intent = intent_data.get("intent")

    if intent == "navigate":
        dest = intent_data.get("destination", "")
        res = start_navigation(DestinationRequest(destination=dest))
        dest_name = res["destination"]["name"]
        res["speak_text"] = f"Navigation started to {dest_name}."
        return res
    elif intent == "stop_navigation":
        res = stop_navigation()
        res["speak_text"] = "Navigation stopped."
        return res
    elif intent == "pause_navigation":
        res = pause_navigation()
        res["speak_text"] = "Navigation paused."
        return res
    elif intent == "resume_navigation":
        res = resume_navigation()
        res["speak_text"] = "Resuming navigation."
        return res
    elif intent == "query_location":
        loc = gps_mgr.get_location()
        area_desc = map_mgr.reverse_geocode(loc["latitude"], loc["longitude"])
        if decision_engine.destination_name:
            curr_step = latest_telemetry.get("route_status", {}).get("current_instruction", "Walk straight")
            dist_dest = int(latest_telemetry.get("route_status", {}).get("distance_to_destination", 0))
            speak_text = f"You are currently {area_desc}, navigating to {decision_engine.destination_name}. Next maneuver: {curr_step}. Destination is {dist_dest} meters away."
        else:
            speak_text = f"You are currently {area_desc}."
        
        voice_mgr.speak(speak_text, priority="HIGH")
        return {"intent": intent, "result": loc, "speak_text": speak_text, "location_name": area_desc}
    elif intent == "repeat_instruction":
        repeat_text = decision_engine.last_spoken_instruction or "System initialized. Ready for navigation."
        voice_mgr.speak(repeat_text, priority="HIGH", force=True)
        return {"intent": intent, "repeated": repeat_text, "speak_text": repeat_text}
    elif intent == "query_ahead":
        safe_info = latest_telemetry.get("safe_path", {})
        rec = safe_info.get("recommended_direction", "Clear")
        speak_text = f"Path recommendation ahead is {rec.lower()}."
        voice_mgr.speak(speak_text, priority="HIGH")
        return {"intent": intent, "ahead": rec, "speak_text": speak_text}

    speak_text = "Command not recognized. Please try again."
    voice_mgr.speak(speak_text, priority="LOW")
    return {"intent": "unknown", "text": req.command, "speak_text": speak_text}

# --- Real-Time Telemetry WebSocket ---

@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    logger.info("WebSocket client connected for real-time telemetry stream.")
    try:
        while True:
            # Advance simulation GPS if in simulation/full navigation mode
            if current_mode in ["simulation", "full_navigation"]:
                gps_mgr.step_simulation(delta_time=0.2)

            curr_gps = gps_mgr.get_location()
            route_status = route_tracker.update_position(curr_gps["latitude"], curr_gps["longitude"])

            # Camera & Vision processing with WOTR + COCO YOLO models
            _, frame = camera_mgr.read_frame()
            h, w, _ = frame.shape
            detections = detector.detect(frame)

            enriched_detections = distance_estimator.enrich_detections_with_distance(detections, h)
            tracked_detections = temporal_tracker.update(enriched_detections)
            safe_path_analysis = safe_path_detector.analyze_safe_path(tracked_detections, w, h)
            risk_analysis = risk_analyzer.evaluate_risk(safe_path_analysis)

            # Decision Engine synthesis
            decision = decision_engine.process_decision(route_status, safe_path_analysis, risk_analysis, curr_gps)

            # Speak instruction if new high priority alert or route maneuver
            if decision.get("instruction") and decision.get("instruction") != decision_engine.last_spoken_instruction:
                decision_engine.last_spoken_instruction = decision["instruction"]
                voice_mgr.speak(decision["instruction"], priority=decision.get("priority", "MEDIUM"))

            # Draw bounding boxes & corridors on visual frame for web/mobile UI
            annotated_frame = _annotate_frame(frame, enriched_detections, safe_path_analysis, risk_analysis)
            small_frame = cv2.resize(annotated_frame, (320, 240))
            _, buffer = cv2.imencode(".jpg", small_frame, [cv2.IMWRITE_JPEG_QUALITY, 30])
            frame_b64 = base64.b64encode(buffer).decode("utf-8")

            telemetry_packet = {
                "timestamp": time.time(),
                "mode": current_mode,
                "gps": curr_gps,
                "route_status": route_status,
                "detections": enriched_detections,
                "safe_path": safe_path_analysis,
                "risk": risk_analysis,
                "decision": decision,
                "frame_b64": frame_b64
            }

            global latest_telemetry
            latest_telemetry = telemetry_packet

            try:
                await websocket.send_json(telemetry_packet)
            except Exception as send_err:
                logger.warning(f"WebSocket client write failed: {send_err}")
                break

            await asyncio.sleep(0.1) # ~10 smooth FPS stream, low network overhead
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket telemetry error: {e}")
    finally:
        if websocket in active_websockets:
            active_websockets.remove(websocket)

def _annotate_frame(frame: np.ndarray, detections: list, safe_path: dict, risk: dict) -> np.ndarray:
    """Draw bounding boxes, left/center/right corridors, and status text on display frame."""
    annotated = frame.copy()
    h, w, _ = annotated.shape

    # Draw vertical corridor boundary lines (LEFT | CENTER | RIGHT)
    left_x = int(w * 0.33)
    right_x = int(w * 0.67)
    cv2.line(annotated, (left_x, 0), (left_x, h), (255, 255, 255), 1)
    cv2.line(annotated, (right_x, 0), (right_x, h), (255, 255, 255), 1)

    # Draw zone status text
    zones = safe_path.get("zones", {})
    cv2.putText(annotated, f"L: {zones.get('left')}", (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    cv2.putText(annotated, f"C: {zones.get('center')}", (left_x + 10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    cv2.putText(annotated, f"R: {zones.get('right')}", (right_x + 10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

    # Draw detections
    for det in detections:
        bbox = det.get("bbox", [0, 0, 0, 0])
        cls = det.get("class", "object")
        dist = det.get("distance_m", 0)
        conf = det.get("confidence", 0)

        x1, y1, x2, y2 = bbox
        color = (0, 0, 255) if dist <= 1.0 else ((0, 165, 255) if dist <= 2.0 else (0, 255, 0))

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        label = f"{cls} {dist}m ({int(conf*100)}%)"
        cv2.putText(annotated, label, (x1, max(15, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Draw risk status header
    risk_level = risk.get("level", "LOW")
    header_color = (0, 0, 255) if risk_level == "CRITICAL" else ((0, 165, 255) if risk_level == "HIGH" else (0, 255, 0))
    cv2.putText(annotated, f"RISK: {risk_level}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, header_color, 2)

    return annotated

# Serve frontend static files
app.mount("/static", StaticFiles(directory=str(ROOT_DIR / "frontend")), name="static")

@app.get("/")
def serve_frontend():
    index_path = ROOT_DIR / "frontend" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse("<h1>VisionNav Backend API Server Online</h1>")

if __name__ == "__main__":
    import uvicorn
    import socket

    def find_free_port(start_port: int = 8000, max_port: int = 8010) -> int:
        for p in range(start_port, max_port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("0.0.0.0", p)) != 0:
                    return p
        return start_port

    target_port = find_free_port(8000)
    os.environ["VISIONNAV_PORT"] = str(target_port)
    discovery_server.set_target_port(target_port)
    print(f"\n========================================================")
    print(f" VisionNav Server starting on http://localhost:{target_port}")
    print(f"========================================================\n")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=target_port, reload=True)
