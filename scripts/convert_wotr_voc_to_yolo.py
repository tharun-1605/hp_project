"""WOTR PASCAL VOC to YOLO Dataset Converter & Automated Trainer.

Converts WOTR PASCAL VOC XML annotations ('Annotations/') and images ('JPEGImages/')
into YOLO bounding box format ('images/train', 'labels/train') and updates data.yaml.
"""
import os
import sys
import yaml
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict

# Official 20 classes of the WOTR dataset
WOTR_CLASSES: List[str] = [
    "tree", "red_light", "green_light", "crosswalk", "tactile_paving",
    "sign", "pedestrian", "bicycle", "bus", "truck",
    "car", "motorcycle", "reflective_cone", "ashcan", "warning_column",
    "roadblock", "pole", "dog", "tricycle", "fire_hydrant"
]

# Alias mappings as specified in WOTR README
CLASS_ALIASES: Dict[str, str] = {
    "blind_road": "tactile_paving",
    "person": "pedestrian"
}

CLASS_TO_ID: Dict[str, int] = {cls_name: i for i, cls_name in enumerate(WOTR_CLASSES)}

def convert_voc_bbox_to_yolo(size: List[int], box: List[float]) -> List[float]:
    """Convert Pascal VOC [xmin, ymin, xmax, ymax] to YOLO normalized [x_center, y_center, width, height]."""
    dw = 1.0 / size[0] if size[0] > 0 else 1.0
    dh = 1.0 / size[1] if size[1] > 0 else 1.0
    x = (box[0] + box[2]) / 2.0 - 1.0
    y = (box[1] + box[3]) / 2.0 - 1.0
    w = box[2] - box[0]
    h = box[3] - box[1]
    return [round(x * dw, 6), round(y * dh, 6), round(w * dw, 6), round(h * dh, 6)]

def convert_voc_xml_to_yolo(xml_file: Path, out_txt_file: Path):
    """Parse XML annotation and write normalized YOLO label file."""
    tree = ET.parse(xml_file)
    root = tree.getroot()

    size_elem = root.find("size")
    if size_elem is None:
        return
    w = int(size_elem.find("width").text)
    h = int(size_elem.find("height").text)

    yolo_lines = []
    for obj in root.iter("object"):
        cls_name = obj.find("name").text.strip()
        cls_name = CLASS_ALIASES.get(cls_name, cls_name)

        if cls_name not in CLASS_TO_ID:
            continue

        cls_id = CLASS_TO_ID[cls_name]
        xmlbox = obj.find("bndbox")
        b = [
            float(xmlbox.find("xmin").text),
            float(xmlbox.find("ymin").text),
            float(xmlbox.find("xmax").text),
            float(xmlbox.find("ymax").text)
        ]
        bb = convert_voc_bbox_to_yolo([w, h], b)
        yolo_lines.append(f"{cls_id} {' '.join(map(str, bb))}\n")

    with open(out_txt_file, "w") as f:
        f.writelines(yolo_lines)

def process_wotr_dataset(base_dir: str = "data/wotr"):
    """Convert Pascal VOC WOTR dataset structure into YOLOv8 dataset format."""
    base_path = Path(base_dir)
    voc_images_dir = base_path / "JPEGImages"
    voc_annotations_dir = base_path / "Annotations"

    if not voc_images_dir.exists() or not voc_annotations_dir.exists():
        print(f"Directory check: Expected 'JPEGImages/' and 'Annotations/' in '{base_path.resolve()}'.")
        return False

    img_files = list(voc_images_dir.glob("*.jpg")) + list(voc_images_dir.glob("*.png"))
    print(f"Found {len(img_files)} images in '{voc_images_dir.resolve()}'.")

    # Create destination train/val directories
    train_img_dir = base_path / "images" / "train"
    val_img_dir = base_path / "images" / "val"
    train_lbl_dir = base_path / "labels" / "train"
    val_lbl_dir = base_path / "labels" / "val"

    for d in [train_img_dir, val_img_dir, train_lbl_dir, val_lbl_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Convert XML files to YOLO .txt
    converted_count = 0
    split_index = int(len(img_files) * 0.8) # 80% train, 20% val

    for i, img_path in enumerate(img_files):
        xml_path = voc_annotations_dir / f"{img_path.stem}.xml"
        if not xml_path.exists():
            continue

        target_img_dir = train_img_dir if i < split_index else val_img_dir
        target_lbl_dir = train_lbl_dir if i < split_index else val_lbl_dir

        shutil.copy(img_path, target_img_dir / img_path.name)
        out_txt = target_lbl_dir / f"{img_path.stem}.txt"
        convert_voc_xml_to_yolo(xml_path, out_txt)
        converted_count += 1

    # Update data.yaml
    names_dict = {i: name for i, name in enumerate(WOTR_CLASSES)}
    yaml_content = {
        "path": str(base_path.resolve()),
        "train": "images/train",
        "val": "images/val",
        "names": names_dict
    }

    yaml_path = base_path / "data.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(yaml_content, f, default_flow_style=False)

    print(f"Successfully converted {converted_count} WOTR images & PASCAL VOC XML annotations to YOLO format!")
    print(f"Updated YOLO data.yaml saved at: {yaml_path.resolve()}")
    return True

if __name__ == "__main__":
    success = process_wotr_dataset()
    if success:
        print("\nLaunching YOLO fine-tuning on converted WOTR dataset...")
        os.system(".venv/bin/python scripts/train_wotr.py")
