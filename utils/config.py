"""Configuration loader for ERIS app and scripts."""
from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    path = PROJECT_ROOT / "config.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_app_config() -> dict:
    return load_config().get("app", {})
