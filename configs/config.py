import os
import sys

from pathlib import Path
from typing import Any

import yaml

from dotenv import load_dotenv

# Get the directory containing this file
script_dir = Path(__file__).parent
# Load .env from the configs directory
load_dotenv(script_dir / ".env")


def load_and_validate_yaml_config(config_path: str) -> dict[str, Any]:
    try:
        with open(config_path) as config_file:
            config = yaml.safe_load(config_file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found at {config_path}") from None

    if not config or "services" not in config or not config["services"]:
        raise ValueError("Configuration must contain a non-empty 'services' section")

    for service_name, service_config in config["services"].items():
        required_keys = ["service_name", "service_id", "username", "password"]
        missing_keys = [key for key in required_keys if key not in service_config]

        if missing_keys:
            raise ValueError(
                f"Service '{service_name}' is missing required keys: {', '.join(missing_keys)}"
            )

        for key in required_keys:
            if not service_config[key] or service_config[key] == f"<{key.upper()}>":
                raise ValueError(f"Service '{service_name}' has an invalid or unset {key}")
    return config


def load_service_config(config_path: str = "org_config.yaml") -> dict[str, Any]:
    script_dir = Path(__file__).parent
    full_config_path = script_dir / config_path

    try:
        return load_and_validate_yaml_config(str(full_config_path))
    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)


REQUIRED_VARS = [
    "CLICKHOUSE_API_KEY",
    "CLICKHOUSE_API_SECRET",
    "CLICKHOUSE_ORGANIZATION_ID",
    "CLICKHOUSE_FAST_API_USERNAME",
    "CLICKHOUSE_FAST_API_PASSWORD",
    "CLICKHOUSE_FAST_API_PORT",
    "CLICKHOUSE_FAST_API_HOST",
    "CLICKHOUSE_FAST_API_DOCS_PATH",
]

missing_vars = [var for var in REQUIRED_VARS if not os.getenv(var)]

if missing_vars:
    print(
        f"Error: The following required environment variables are missing: {', '.join(missing_vars)}"
    )
    print("Please set these variables in the .env file.")
    sys.exit(1)

CLICKHOUSE_API_KEY = os.getenv("CLICKHOUSE_API_KEY")
CLICKHOUSE_API_SECRET = os.getenv("CLICKHOUSE_API_SECRET")
CLICKHOUSE_ORGANIZATION_ID = os.getenv("CLICKHOUSE_ORGANIZATION_ID")
CLICKHOUSE_FAST_API_USERNAME = os.getenv("CLICKHOUSE_FAST_API_USERNAME")
CLICKHOUSE_FAST_API_PASSWORD = os.getenv("CLICKHOUSE_FAST_API_PASSWORD")
CLICKHOUSE_FAST_API_PORT = os.getenv("CLICKHOUSE_FAST_API_PORT")
CLICKHOUSE_FAST_API_HOST = os.getenv("CLICKHOUSE_FAST_API_HOST")
CLICKHOUSE_FAST_API_DOCS_PATH = os.getenv("CLICKHOUSE_FAST_API_DOCS_PATH")
CLICKHOUSE_SERVICE_CONFIG = load_service_config()


if __name__ == "__main__":
    load_service_config("org_config.yaml")
    pass
