"""Environment verification and diagnostic script for VisionNav."""
import sys
import os
from pathlib import Path

def check_python_version():
    print(f"Checking Python version: {sys.version.split()[0]}...", end="")
    if sys.version_info < (3, 9):
        print(" [FAIL] Python 3.9+ is required.")
        return False
    print(" [OK]")
    return True

def check_directories():
    print("Checking project directory structure...")
    root = Path(__file__).resolve().parent.parent
    required_dirs = [
        "backend/config", "backend/navigation", "backend/vision",
        "backend/voice", "backend/models", "frontend/css", "frontend/js", "tests"
    ]
    all_ok = True
    for d in required_dirs:
        p = root / d
        if not p.exists():
            print(f"  - Directory missing: {d} [FAIL]")
            all_ok = False
        else:
            print(f"  - Directory exists: {d} [OK]")
    return all_ok

def check_packages():
    print("Checking core Python packages...")
    packages = ["fastapi", "uvicorn", "cv2", "numpy", "yaml", "requests"]
    all_ok = True
    for pkg in packages:
        try:
            __import__(pkg)
            print(f"  - {pkg}: Installed [OK]")
        except ImportError:
            print(f"  - {pkg}: Missing [WARNING]")
            all_ok = False
    return all_ok

def main():
    print("=========================================")
    print("VisionNav Environment Diagnostic Tool")
    print("=========================================")
    py_ok = check_python_version()
    dirs_ok = check_directories()
    pkgs_ok = check_packages()
    print("=========================================")
    if py_ok and dirs_ok:
        print("Environment is ready for VisionNav execution!")
    else:
        print("Environment setup incomplete. Please resolve missing prerequisites.")

if __name__ == "__main__":
    main()
