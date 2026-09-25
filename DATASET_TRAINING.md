# WOTR Dataset Loading & YOLOv8 Fine-Tuning Guide

This guide explains how to load, prepare, convert, and fine-tune YOLOv8 models on the **WOTR (Walking Obstacle & Traffic Record)** dataset or any custom outdoor navigation dataset for VisionNav.

---

## 1. Supported Navigation Obstacle Classes

VisionNav object detector is trained to identify outdoor & indoor navigation obstacles:
- `pedestrian` / `person`
- `curb`
- `pothole`
- `staircase`
- `tactile_paving` / `blind_road`
- `pole`
- `crosswalk`
- `barrier` / `roadblock`
- `traffic_cone` / `reflective_cone`
- `trash_can` / `ashcan`
- `car`, `bus`, `truck`, `bicycle`, `motorcycle`

---

## 2. Quick Start — Generate Sample Dataset

If you want to test the training pipeline without downloading full dataset files, generate a synthetic sample dataset:

```bash
python scripts/generate_sample_wotr_dataset.py
```

This creates:
- `data/wotr/JPEGImages/`: 30 sample outdoor street scene images (`wotr_sample_0001.jpg`, etc.)
- `data/wotr/Annotations/`: Pascal VOC XML bounding box annotations

---

## 3. Loading Your Own WOTR / Custom Dataset

To load real WOTR dataset images and annotations:

### Option A: Pascal VOC Format (Recommended)
Place your dataset files in the following directory layout:
```
data/wotr/
├── JPEGImages/
│   ├── image_0001.jpg
│   ├── image_0002.jpg
│   └── ...
└── Annotations/
    ├── image_0001.xml
    ├── image_0002.xml
    └── ...
```

### Option B: Pre-formatted YOLO Format
If your dataset is already in YOLO format:
```
data/wotr/
├── images/
│   ├── train/
│   └── val/
├── labels/
│   ├── train/
│   └── val/
└── data.yaml
```

---

## 4. Convert Pascal VOC Annotations to YOLO Format

Run the converter script to parse Pascal VOC XML files into normalized YOLO `.txt` labels and automatically generate `data/wotr/data.yaml`:

```bash
python scripts/convert_wotr_voc_to_yolo.py
```

This script will:
1. Parse all XML bounding boxes in `data/wotr/Annotations/`.
2. Convert coordinates `[xmin, ymin, xmax, ymax]` to YOLO format `[class_id, x_center, y_center, width, height]`.
3. Split data automatically (80% training set, 20% validation set).
4. Save images and label files to `data/wotr/images/` and `data/wotr/labels/`.
5. Launch fine-tuning automatically.

---

## 5. Fine-Tuning YOLOv8 Model

To launch model fine-tuning manually:

```bash
python scripts/train_wotr.py
```

### Programmatic Usage & Custom Configuration
You can customize training parameters inside Python or by editing `scripts/train_wotr.py`:

```python
from scripts.train_wotr import train_yolo_wotr, create_dataset_structure

yaml_file = create_dataset_structure("data/wotr")

train_yolo_wotr(
    data_yaml=yaml_file,
    epochs=100,            # Number of training epochs
    imgsz=640,             # Input resolution (640x480)
    batch=16,              # Batch size
    model_name="yolov8m.pt", # Base weights
    output_dir="backend/models",
    device="cpu"           # Use '0' or 'cuda' for GPU training
)
```

Upon completion, the best trained weights will automatically be saved to:
```
backend/models/wotr_yolov8.pt
```

---

## 6. Verifying Model Integration in VisionNav

Once `backend/models/wotr_yolov8.pt` is generated, the VisionNav backend automatically loads both models during startup:
1. `wotr_yolov8.pt` (Navigation & obstacle classes)
2. `yolov8m.pt` (General COCO indoor & outdoor objects)

Test detection performance via pytest:
```bash
PYTHONPATH=. .venv/bin/pytest -v tests/test_detection.py
```

Or start the server to view live visual detections on the web dashboard / mobile app:
```bash
python backend/main.py
```
