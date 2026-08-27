"""Configuration package initialization."""
from pathlib import Path
import yaml

CONFIG_DIR = Path(__file__).parent
SETTINGS_FILE = CONFIG_DIR / "settings.yaml"

def load_settings(config_path: Path = SETTINGS_FILE) -> dict:
    """Load application configuration from YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
