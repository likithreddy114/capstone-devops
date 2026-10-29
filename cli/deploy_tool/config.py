
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".deploy-tool"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "region": "ap-south-1",
    "bucket": "",
    "environment": "dev",
    "ecr_repository": "",
    "ecs_cluster": "",
    "ecs_service": "",
}


def load_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG.copy())

    with CONFIG_FILE.open("r", encoding="utf-8") as file:
        config = json.load(file)

    # Add new defaults while preserving existing settings.
    updated = False
    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value
            updated = True

    if updated:
        save_config(config)

    return config


def save_config(config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    with CONFIG_FILE.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=4)


def set_config(key, value):
    config = load_config()

    if key not in DEFAULT_CONFIG:
        allowed = ", ".join(DEFAULT_CONFIG.keys())
        raise ValueError(f"Invalid key. Allowed keys: {allowed}")

    if not value.strip():
        raise ValueError("Configuration value cannot be empty.")

    config[key] = value.strip()
    save_config(config)


def show_config():
    config = load_config()

    for key, value in config.items():
        print(f"{key}: {value if value else '(not set)'}")
