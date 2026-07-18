"""doctor: atomic readiness check (AGENTS.md).

Validates the settings manifest, reports effective sources (never values), and probes
providers ONLY when credentials are configured. Atomic: never writes, prompts, or
mutates. Exit 0 ok / 2 incomplete-or-invalid config / 4 rejected creds / 1 provider failure.
Provider/auth probe is intentionally skipped in the core task (reported as such).
"""
from __future__ import annotations

import argparse
import os

from credentials import _get_backend, credential_status
from envelope import emit_success
from registry import register
from settings import SettingsConfigError, load_settings_config, resolve_runtime_settings

_PROBE_SKIPPED = "skipped (no provider configured in core task)"


def _validate_manifest(config: dict) -> list[str]:
    issues: list[str] = []
    for item in config.get("settings", []):
        if "name" not in item:
            issues.append(f"setting entry missing 'name': {item!r}")
            continue
        if "type" not in item:
            issues.append(f"setting {item['name']!r} missing 'type'")
    return issues


def doctor_check(config: dict | None = None, env: dict[str, str] | None = None, keyring_backend=None) -> dict:
    """Return a report dict with `ok`, `exit_code`, `settings[]` (sources, no values), `backend`, `probe`."""
    try:
        config = load_settings_config() if config is None else config
    except SettingsConfigError as exc:
        return {"ok": False, "exit_code": 2, "issues": [str(exc)], "settings": [], "probe": _PROBE_SKIPPED, "backend": "unknown"}

    env = os.environ if env is None else env
    issues = _validate_manifest(config)
    if issues:
        return {"ok": False, "exit_code": 2, "issues": issues, "settings": [], "probe": _PROBE_SKIPPED, "backend": "unknown"}

    values, sources = resolve_runtime_settings(config, env)
    cred_sources = credential_status(config, env, keyring_backend)
    rows: list[dict] = []
    missing_required: list[dict] = []
    for item in config["settings"]:
        name = item["name"]
        required = bool(item.get("required"))
        if item.get("credential"):
            src = cred_sources.get(name, "missing")
            rows.append({"name": name, "configured": src in ("keyring", "environment"), "source": src, "required": required})
        else:
            src = sources.get(name, "missing")
            rows.append({"name": name, "configured": src != "missing", "source": src, "required": required})
            if required and src == "missing":
                missing_required.append({"name": name, "help": item.get("help", {})})

    backend = _get_backend(keyring_backend)
    backend_name = "unavailable" if backend is None else type(backend).__name__
    if missing_required:
        return {
            "ok": False,
            "exit_code": 2,
            "settings": rows,
            "backend": backend_name,
            "probe": _PROBE_SKIPPED,
            "missing_required": missing_required,
        }
    return {"ok": True, "exit_code": 0, "settings": rows, "backend": backend_name, "probe": _PROBE_SKIPPED}


@register("doctor", "check")
def doctor_cmd(args: argparse.Namespace, out, err) -> int:
    result = doctor_check()
    emit_success(result, out)
    return result["exit_code"]
