"""Sample WOTR Dataset Generator.

Generates sample outdoor navigation obstacle images and Pascal VOC XML annotations
representing WOTR classes (curb, pothole, pedestrian, pole, staircase, crosswalk, tactile_paving)
so the dataset conversion and YOLO fine-tuning pipeline runs end-to-end automatically.
"""
import os
import cv2
import random
import numpy as np
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path

# Sample WOTR classes
SAMPLE_CLASSES = [
    "pedestrian", "curb", "pothole", "staircase", "tactile_paving",
    "pole", "crosswalk", "car", "bus", "trash_can", "barrier"
]

def create_sample_image_and_annotation(image_path: Path, xml_path: Path, img_id: int):
    """Generate a synthetic outdoor street scene with annotated obstacle bounding boxes."""
    w, h = 640, 480
    img = np.zeros((h, w, 3), dtype=np.uint8)

    # Draw simulated street background (sky + road + sidewalk)
    img[0:180, :] = [235, 206, 135] # Sky (Light Blue)
    img[180:320, :] = [80, 80, 80]  # Asphalt Road (Dark Grey)
    img[320:480, :] = [160, 160, 160] # Sidewalk (Light Grey)

    # Randomly select 2-4 obstacles for this sample image
    num_obstacles = random.randint(2, 4)
    objects_data = []

    for _ in range(num_obstacles):
        cls_name = random.choice(SAMPLE_CLASSES)
        
        # Pick random bounding box coordinates in frame
        box_w = random.randint(50, 150)
        box_h = random.randint(60, 200)
        xmin = random.randint(20, w - box_w - 20)
        ymin = random.randint(150, h - box_h - 20)
        xmax = xmin + box_w
        ymax = ymin + box_h

        # Draw obstacle box on image
        color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
        cv2.rectangle(img, (xmin, ymin), (xmax, ymax), color, -1)
        cv2.putText(img, cls_name, (xmin + 5, ymin + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        objects_data.append({
            "name": cls_name,
            "bndbox": {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax}
        })

    # Save synthesized image
    cv2.imwrite(str(image_path), img)

    # Build Pascal VOC XML root
    annotation = ET.Element("annotation")
    ET.SubElement(annotation, "folder").text = "JPEGImages"
    ET.SubElement(annotation, "filename").text = image_path.name
    
    size = ET.SubElement(annotation, "size")
    ET.SubElement(size, "width").text = str(w)
    ET.SubElement(size, "height").text = str(h)
    ET.SubElement(size, "depth").text = "3"

    for obj in objects_data:
        obj_elem = ET.SubElement(annotation, "object")
        ET.SubElement(obj_elem, "name").text = obj["name"]
        ET.SubElement(obj_elem, "pose").text = "Unspecified"
        ET.SubElement(obj_elem, "truncated").text = "0"
        ET.SubElement(obj_elem, "difficult").text = "0"

        bndbox = ET.SubElement(obj_elem, "bndbox")
        ET.SubElement(bndbox, "xmin").text = str(obj["bndbox"]["xmin"])
        ET.SubElement(bndbox, "ymin").text = str(obj["bndbox"]["ymin"])
        ET.SubElement(bndbox, "xmax").text = str(obj["bndbox"]["xmax"])
        ET.SubElement(bndbox, "ymax").text = str(obj["bndbox"]["ymax"])

    # Format XML nicely
    xml_str = minidom.parseString(ET.tostring(annotation)).toprettyxml(indent="  ")
    with open(xml_path, "w") as f:
        f.write(xml_str)

def generate_wotr_sample_dataset(base_dir: str = "data/wotr", num_samples: int = 30):
    """Generate sample dataset structure inside data/wotr/JPEGImages and data/wotr/Annotations."""
    base_path = Path(base_dir)
    images_dir = base_path / "JPEGImages"
    annotations_dir = base_path / "Annotations"

    images_dir.mkdir(parents=True, exist_ok=True)
    annotations_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {num_samples} sample WOTR images & PASCAL VOC XML annotations...")
    for i in range(1, num_samples + 1):
        img_name = f"wotr_sample_{i:04d}.jpg"
        xml_name = f"wotr_sample_{i:04d}.xml"

        create_sample_image_and_annotation(
            images_dir / img_name,
            annotations_dir / xml_name,
            i
        )

    print(f"Sample WOTR dataset generated at: {base_path.resolve()}")

if __name__ == "__main__":
    generate_wotr_sample_dataset()
