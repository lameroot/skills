"""Credential resolution: keyring -> environment -> missing.

Credentials are NEVER copied to os.environ. Status returns sources only (no values).
"""
from __future__ import annotations

import os
from typing import Any

try:
    import keyring as _real_keyring  # type: ignore
except Exception:  # noqa: BLE001 - optional dependency; status reports 'unavailable'
    _real_keyring = None  # type: ignore[assignment]

from settings import SettingsConfigError, load_settings_config


def _get_backend(keyring_backend: Any) -> Any:
    # Read the module global at call time so tests can monkeypatch credentials._real_keyring.
    if keyring_backend is not None:
        return keyring_backend
    return _real_keyring


class CredentialResolutionError(RuntimeError):
    pass


def resolve_credentials(
    config: dict | None = None,
    env: dict[str, str] | None = None,
    keyring_backend: Any = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Return (values, sources) for credential entries. keyring -> environment -> missing."""
    config = load_settings_config() if config is None else config
    env = os.environ if env is None else env
    backend = _get_backend(keyring_backend)
    service = config["keyring_service"]
    values: dict[str, str] = {}
    sources: dict[str, str] = {}
    for item in config["settings"]:
        if not item.get("credential"):
            continue
        account = item.get("account", item["name"])
        name = item["name"]
        value: str | None = None
        if backend is not None:
            try:
                value = backend.get_password(service, account)
            except Exception:  # noqa: BLE001 - backend errors -> fall through to env
                value = None
        if value:
            values[name] = value
            sources[name] = "keyring"
        elif env.get(name):
            values[name] = env[name]
            sources[name] = "environment"
        else:
            sources[name] = "missing"
    return values, sources


def credential_status(
    config: dict | None = None,
    env: dict[str, str] | None = None,
    keyring_backend: Any = None,
) -> dict[str, str]:
    """Return name -> source for credentials. Values are intentionally discarded."""
    _values, sources = resolve_credentials(config, env, keyring_backend)
    return sources


def require_credentials(
    names: list[str],
    config: dict | None = None,
    env: dict[str, str] | None = None,
    keyring_backend: Any = None,
) -> dict[str, str]:
    """Resolve and ensure all `names` are present, else raise CredentialResolutionError."""
    values, sources = resolve_credentials(config, env, keyring_backend)
    missing = [n for n in names if sources.get(n) == "missing"]
    if missing:
        raise CredentialResolutionError("Missing credentials: " + ", ".join(missing))
    return {n: values[n] for n in names}
