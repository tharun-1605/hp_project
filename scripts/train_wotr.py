"""WOTR (Walking Obstacle & Traffic Record) Dataset Preparer and YOLOv8 Fine-Tuning Script.

This script helps format the WOTR dataset layout, create data.yaml,
and launch YOLOv8 fine-tuning for outdoor obstacle detection.
"""
import os
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Optional

# Standard WOTR & Navigation Obstacle Classes
WOTR_CLASSES: Dict[int, str] = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    4: "bus",
    5: "truck",
    6: "pole",
    7: "pothole",
    8: "staircase",
    9: "curb",
    10: "traffic_cone",
    11: "bench",
    12: "trash_can",
    13: "low_hanging_branch",
    14: "barrier"
}

def create_dataset_structure(base_dir: str = "data/wotr") -> Path:
    """Create directory structure for WOTR dataset if not present."""
    base_path = Path(base_dir)
    dirs = [
        base_path / "images" / "train",
        base_path / "images" / "val",
        base_path / "labels" / "train",
        base_path / "labels" / "val",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Generate data.yaml
    yaml_content = {
        "path": str(base_path.resolve()),
        "train": "images/train",
        "val": "images/val",
        "names": WOTR_CLASSES
    }

    yaml_path = base_path / "data.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(yaml_content, f, default_flow_style=False)

    print(f"Dataset structure verified at: {base_path.resolve()}")
    print(f"YAML configuration saved to: {yaml_path.resolve()}")
    return yaml_path

def train_yolo_wotr(
    data_yaml: Path,
    epochs: int = 50,
    imgsz: int = 640,
    batch: int = 16,
    model_name: str = "yolov8n.pt",
    output_dir: str = "backend/models",
    device: str = "cpu"
):
    """Fine-tune YOLOv8 model on WOTR dataset."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("Ultralytics is not installed. Please install it using `pip install ultralytics`.")
        return None

    print(f"Loading base YOLO model: {model_name}")
    model = YOLO(model_name)

    print(f"Starting training on dataset: {data_yaml}")
    print(f"Config: epochs={epochs}, imgsz={imgsz}, batch={batch}, device={device}")

    results = model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project=output_dir,
        name="wotr_yolo",
        exist_ok=True
    )

    best_weights = Path(output_dir) / "wotr_yolo" / "weights" / "best.pt"
    target_weights = Path(output_dir) / "wotr_yolov8.pt"

    if best_weights.exists():
        import shutil
        shutil.copy(best_weights, target_weights)
        print(f"Training completed successfully!")
        print(f"Model saved to: {target_weights.resolve()}")
    else:
        print(f"Training completed. Check results in: {output_dir}/wotr_yolo")

    return results

if __name__ == "__main__":
    yaml_file = create_dataset_structure()

    if "--check-only" in sys.argv:
        print("Check mode completed.")
        sys.exit(0)

    # Train if dataset images exist
    train_images = list(Path("data/wotr/images/train").glob("*.*"))
    if not train_images:
        print("\nNote: 'data/wotr/images/train' is currently empty.")
        print("To train on real WOTR dataset, place your dataset images and YOLO annotation .txt files into 'data/wotr/'.")
        print("Run `python scripts/train_wotr.py` to start fine-tuning when ready.")
    else:
        train_yolo_wotr(data_yaml=yaml_file, epochs=50)
