
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def normalize(data):
    result = {}
    for key, value in data.items():
        if value is None:
            continue

        key = key.lower()

        if key.startswith("app_"):
            key = key[4:]

        if key == "num_workers":
            key = "workers"

        result[key] = value

    return result


def convert(key, value):
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).lower() in (
            "true", "1", "yes", "on"
        )

    return str(value)


def get_config():
    config = DEFAULTS.copy()

    # Layer 2: YAML
    env_name = os.getenv("APP_ENV", "development")
    path = Path(f"config.{env_name}.yaml")

    if path.exists():
        with path.open(encoding="utf-8") as file:
            config.update(normalize(yaml.safe_load(file) or {}))

    # Layer 3: .env
    config.update(normalize(dict(dotenv_values(".env"))))

    # Layer 4: OS environment variables
    os_vars = {
        key.lower(): value
        for key, value in os.environ.items()
        if key.startswith("APP_") or key == "NUM_WORKERS"
    }
    config.update(normalize(os_vars))

    # Type conversion
    for key, value in list(config.items()):
        config[key] = convert(key, value)

    return config


@app.get("/effective-config")
def effective_config(set: list[str] | None = Query(default=None)):
    config = get_config()

    # Highest precedence: query-string overrides
    for item in set or []:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        key = key.strip().lower()

        if key.startswith("app_"):
            key = key[4:]

        if key == "num_workers":
            key = "workers"

        config[key] = convert(key, value)

    # Never expose the actual secret
    config["api_key"] = "****"

    return config
