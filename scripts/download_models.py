"""Download script for downloading open-source YOLOv8, Vosk, and Piper models."""
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT_DIR / "backend" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

def download_file(url: str, dest_path: Path):
    """Download a file with progress reporting."""
    print(f"Downloading {dest_path.name} from {url}...")
    def reporthook(blocknum, blocksize, totalsize):
        readsofar = blocknum * blocksize
        if totalsize > 0:
            percent = readsofar * 100 / totalsize
            sys.stdout.write(f"\r progress: {percent:.1f}%")
            sys.stdout.flush()
    try:
        urllib.request.urlretrieve(url, dest_path, reporthook)
        print("\nDownload complete.")
    except Exception as e:
        print(f"\nFailed to download {dest_path.name}: {e}")

def main():
    print("=========================================")
    print("VisionNav Model Setup Script")
    print("=========================================")

    # 1. Download YOLOv8m model weights if missing
    yolo_dest = MODELS_DIR / "yolov8m.pt"
    if not yolo_dest.exists():
        yolo_url = "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8m.pt"
        download_file(yolo_url, yolo_dest)
    else:
        print(f"YOLO model already present: {yolo_dest}")

    # 2. Download Vosk small English model if missing
    vosk_dir = MODELS_DIR / "vosk-model-small-en-us"
    if not vosk_dir.exists():
        vosk_zip = MODELS_DIR / "vosk-model-small-en-us-0.15.zip"
        vosk_url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
        download_file(vosk_url, vosk_zip)
        if vosk_zip.exists():
            print("Extracting Vosk model...")
            with zipfile.ZipFile(vosk_zip, 'r') as zip_ref:
                zip_ref.extractall(MODELS_DIR)
            os.remove(vosk_zip)
            print("Vosk model extracted.")
    else:
        print(f"Vosk model directory already present: {vosk_dir}")

    # 3. Download Piper ONNX voice model if missing
    piper_onnx = MODELS_DIR / "en_US-lessac-medium.onnx"
    if not piper_onnx.exists():
        piper_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
        download_file(piper_url, piper_onnx)
    else:
        print(f"Piper voice model already present: {piper_onnx}")

    print("=========================================")
    print("All models successfully configured!")
    print("=========================================")

if __name__ == "__main__":
    main()
