import os
from typing import Any

import httpx

MOODLE_URL = os.getenv("MOODLE_URL", "").rstrip("/")
MOODLE_TOKEN = os.getenv("MOODLE_TOKEN", "")


class MoodleError(Exception):
    pass


def _flatten_params(prefix: str, value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        flat: dict[str, Any] = {}
        for key, item in value.items():
            name = f"{prefix}[{key}]" if prefix else str(key)
            flat.update(_flatten_params(name, item))
        return flat
    if isinstance(value, list):
        flat = {}
        for index, item in enumerate(value):
            flat.update(_flatten_params(f"{prefix}[{index}]", item))
        return flat
    return {prefix: value}


def _prepare_payload(**params: Any) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, (dict, list)):
            flat.update(_flatten_params(key, value))
        elif value is not None:
            flat[key] = value
    return flat


def call(function: str, **params: Any) -> Any:
    if not MOODLE_URL or not MOODLE_TOKEN:
        raise MoodleError("Задайте MOODLE_URL и MOODLE_TOKEN в .env")

    payload = {
        "wstoken": MOODLE_TOKEN,
        "wsfunction": function,
        "moodlewsrestformat": "json",
        **_prepare_payload(**params),
    }

    response = httpx.post(
        f"{MOODLE_URL}/webservice/rest/server.php",
        data=payload,
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict) and data.get("exception"):
        raise MoodleError(data.get("message", "Moodle API error"))

    return data
