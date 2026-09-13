# VisionNav — Open-Source AI Navigation Assistant for Visually Impaired People

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https.mit-license.org)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)

VisionNav is a 100% open-source, offline-first AI navigation assistant designed to help visually impaired individuals navigate unfamiliar environments safely. The system unifies global GPS route navigation with real-time local computer-vision safe-path guidance.

---

## Key Features

1. **GPS Route Navigation**: OpenStreetMap + OSRM open walking route calculation.
2. **Real-time Monocular Vision**: OpenCV + YOLO object detection (`person`, `car`, `bicycle`, `bus`, `chair`, `stop sign`, etc.).
3. **Safe-Path Analysis**: Splits visual field into `LEFT | CENTER | RIGHT` corridors; evaluates `SAFE`, `PARTIALLY BLOCKED`, or `BLOCKED`.
4. **Monocular Distance Estimation**: Approximate physical distance calculations based on bounding box height heuristics.
5. **Risk Engine**: Categorizes environmental danger (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) and enforces emergency interrupts.
6. **Hierarchical Decision Engine**: Priority order: `CRITICAL OBSTACLE` > `HIGH RISK OBSTACLE` > `SAFE-PATH CORRECTION` > `TURN INSTRUCTION` > `STRAIGHT MOVEMENT`.
7. **Offline Speech Input (Vosk)**: Hands-free voice commands ("Navigate to Railway Station", "Where am I?", "Stop").
8. **Offline Speech Output (Piper / pyttsx3)**: Natural voice announcements with priority queueing, cooldown duplicate suppression, and interrupt capability.
9. **Accessible Web Dashboard**: Dark high-contrast UI (yellow/black), screen reader ARIA labels, live bounding box feed, and interactive Leaflet map.
10. **Laptop Simulation Mode**: Complete testing without physical GPS or webcam.

---

## System Architecture

```
USER
  │
  ▼
VOICE COMMAND ("Navigate to Railway Station")
  │
  ▼
VOSK STT / WEB SPEECH ──► COMMAND PROCESSOR ──► MAP MANAGER (OSM / Nominatim)
                                                      │
                                                      ▼
GPS TRACKER ◄────── ROUTE TRACKER ◄────────── ROUTING ENGINE (OSRM)
     │                    │
     └───────────┬────────┘
                 ▼
     NAVIGATION DECISION ENGINE ◄───── RISK ANALYZER
                 ▲                          ▲
                 │                          │
           SAFE PATH DETECTOR ◄─── DISTANCE ESTIMATOR ◄─── YOLO DETECTOR ◄── CAMERA
                 │
                 ▼
         PIPER / TTS ENGINE
                 │
                 ▼
         VOICE INSTRUCTION ("Obstacle ahead. Move slightly left.") ──► USER
```

---

## Hardware & Software Stack

- **Core**: Python 3.10+, FastAPI, WebSockets, OpenCV
- **Vision**: YOLOv8 (Ultralytics / ONNX / OpenCV DNN)
- **Map Data**: OpenStreetMap, Nominatim Geocoder
- **Routing Engine**: OSRM (Open Source Routing Machine)
- **Speech Recognition**: Vosk (Offline STT)
- **Voice Synthesis**: Piper TTS / pyttsx3 (Offline TTS)
- **Frontend UI**: HTML5, CSS3, JavaScript, Leaflet.js

---

## Quick Start & Installation

### 1. Clone & Create Virtual Environment
```bash
git clone https://github.com/your-username/visionnav.git
cd visionnav

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Download Open-Source AI Models
Run the automated downloader to fetch lightweight YOLOv8, Vosk, and Piper models:
```bash
python scripts/download_models.py
```

### 3. Run Environment Diagnostics
```bash
python scripts/setup_environment.py
```

---

## Running the Application

Start the FastAPI server:
```bash
python backend/main.py
```

Open your browser and navigate to:
```
http://localhost:8000
```

### Operating Modes

1. **Mode 1 — Simulation Mode** (Default):
   Simulates GPS route movement and visual obstacle encounters. Test the entire end-to-end pipeline on any laptop without hardware.
2. **Mode 2 — Camera Test Mode**:
   Connects to local webcam or USB camera to test YOLO detection, monocular distance, safe-path corridor division, and TTS alerts without GPS.
3. **Mode 3 — Full Navigation Mode**:
   Runs physical/simulated GPS + OpenStreetMap OSRM routing + Camera Vision + Voice.

---

## Reproducible Demo Walkthrough

1. Open `http://localhost:8000`.
2. Select **"Mode 1: Simulation Mode"** in the top right header.
3. Click the **"Station"** quick button or type `"Navigate to Railway Station"` in the voice command box and click **SEND COMMAND**.
4. **Expected Sequence**:
   - Voice says: *"Navigation started to Central Railway Station."*
   - Map draws the OpenStreetMap walking polyline.
   - GPS starts moving step-by-step along the route.
   - System announces: *"Walk straight for 50 meters."*
   - Camera frame detects a simulated pedestrian in the center corridor.
   - System overrides straight route instruction and announces: *"Obstacle ahead. Move slightly to your left."*
   - Once corridor clears, system resumes: *"Continue straight for 100 meters."*
   - On destination arrival: *"You have reached your destination."*

---

## Dataset Loading & Model Training

VisionNav includes complete tools for generating sample datasets, loading real outdoor obstacle datasets (Pascal VOC / WOTR format), converting annotations, and fine-tuning custom YOLOv8 models.

### 1. Generate Sample Synthetic Dataset
To quickly test the dataset & training pipeline:
```bash
python scripts/generate_sample_wotr_dataset.py
```

### 2. Load Real WOTR / Custom Dataset
Place images into `data/wotr/JPEGImages/` and Pascal VOC XML files into `data/wotr/Annotations/`.

### 3. Convert VOC XML Annotations & Train YOLOv8
Convert annotations to YOLO format and start fine-tuning:
```bash
python scripts/convert_wotr_voc_to_yolo.py
```
Or run the dedicated trainer script directly:
```bash
python scripts/train_wotr.py
```
Trained weights will be saved to `backend/models/wotr_yolov8.pt` and automatically loaded by the VisionNav backend.

For full step-by-step instructions, see the detailed [Dataset & Training Guide](file:///media/tharun/App/hp_project/DATASET_TRAINING.md).

---

## Automated Unit Testing

Execute the complete test suite:
```bash
pytest -v tests/
```

---

## Docker Deployment

Build and launch via Docker Compose:
```bash
docker-compose up --build
```
The application will be accessible at `http://localhost:8000`.

---

## Safety Disclaimer

> [!CAUTION]
> **IMPORTANT SAFETY NOTICE**: VisionNav is an open-source assistive prototype created for research and educational purposes. It is **NOT** a certified mobility aid or a replacement for white canes, guide dogs, or human assistance. Distance estimates are approximate, computer vision models can miss objects under poor lighting or adverse weather, and GPS accuracy varies. Users must exercise caution and never rely exclusively on this system for safe mobility.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
