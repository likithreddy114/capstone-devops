
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".deploy-tool"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "region": "ap-south-1",
    "bucket": "",
    "environment": "dev",

    # Existing deployment settings
    "ecr_repository": "",
    "ecs_cluster": "",
    "ecs_service": "",

    # Reusable ECS deployment settings
    "ecs_execution_role_arn": "",
    "ecs_task_role_arn": "",
    "vpc_id": "",
    "subnet_ids": [],
    "security_group_id": "",
    "assign_public_ip": "ENABLED",
}


def load_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG.copy())

    with CONFIG_FILE.open("r", encoding="utf-8") as file:
        config = json.load(file)

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
        raise ValueError(
            f"Invalid key. Allowed keys: {allowed}"
        )

    if value is None or not value.strip():
        raise ValueError("Configuration value cannot be empty.")

    if isinstance(DEFAULT_CONFIG[key], list):
        value = [
            item.strip()
            for item in value.split(",")
            if item.strip()
        ]

        if not value:
            raise ValueError("At least one list item is required.")

    else:
        value = value.strip()

    if key == "assign_public_ip":
        value = value.upper()

        if value not in ("ENABLED", "DISABLED"):
            raise ValueError(
                "assign_public_ip must be ENABLED or DISABLED."
            )

    config[key] = value
    save_config(config)


def show_config():
    config = load_config()

    for key, value in config.items():
        display_value = value if value else "(not set)"
        print(f"{key}: {display_value}")
