"""Unified settings manifest loader (AGENTS.md `config/settings.json` contract).

Resolution order:
  non-secret setting: environment -> default from settings.json -> missing
  credential:         handled in credentials.py (keyring -> environment -> missing)

This module only resolves NON-SECRET settings. Credentials are never copied to os.environ.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = SKILL_ROOT / "config" / "settings.json"


class SettingsConfigError(Exception):
    """Raised when the settings manifest is missing, malformed, or fails validation."""


def load_settings_config(path: str | Path | None = None) -> dict:
    p = Path(path) if path is not None else SETTINGS_PATH
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SettingsConfigError(f"settings manifest not found: {p}") from exc
    except json.JSONDecodeError as exc:
        raise SettingsConfigError(f"invalid settings manifest JSON at {p}: {exc}") from exc
    if not isinstance(data, dict):
        raise SettingsConfigError("manifest must be a JSON object")
    for key in ("settings", "keyring_service"):
        if key not in data:
            raise SettingsConfigError(f"manifest missing required key: {key!r}")
    if not isinstance(data["settings"], list):
        raise SettingsConfigError("'settings' must be a list")
    return data


_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off", ""}


def _coerce(value: Any, item: dict) -> Any:
    name = item["name"]
    field_type = item.get("type", "string")
    if field_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            low = value.strip().lower()
            if low in _TRUE:
                return True
            if low in _FALSE:
                return False
        raise SettingsConfigError(f"{name}: invalid boolean value {value!r}")
    if field_type == "integer":
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise SettingsConfigError(f"{name}: invalid integer value {value!r}") from exc
    return str(value)


def resolve_runtime_settings(
    config: dict | None = None, env: dict[str, str] | None = None
) -> tuple[dict[str, Any], dict[str, str]]:
    """Return (values, sources) for NON-SECRET settings only.

    Credentials are skipped here; they are resolved by credentials.resolve_credentials.
    """
    config = load_settings_config() if config is None else config
    env = os.environ if env is None else env
    values: dict[str, Any] = {}
    sources: dict[str, str] = {}
    for item in config["settings"]:
        if item.get("credential"):
            continue
        name = item["name"]
        raw = env.get(name)
        if raw is not None and raw != "":
            values[name] = _coerce(raw, item)
            sources[name] = "environment"
        elif "default" in item:
            values[name] = _coerce(item["default"], item)
            sources[name] = "default"
        else:
            sources[name] = "missing"
    return values, sources


def apply_defaults_to_environ(config: dict | None = None, env: dict[str, str] | None = None) -> None:
    """Seed NON-SECRET defaults into `env` via setdefault (never credentials)."""
    config = load_settings_config() if config is None else config
    env = os.environ if env is None else env
    for item in config["settings"]:
        if item.get("credential"):
            continue
        if "default" in item and item["name"] not in env:
            env.setdefault(item["name"], str(item["default"]))
