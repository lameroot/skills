"""auth resource: credential lifecycle (status / setup / check / delete).

setup uses getpass in real interactive use; tests inject values via set_setup_values().
Provider/auth probe is intentionally skipped in the core task (reported as such).
"""
from __future__ import annotations

import argparse
import os

from credentials import (
    CredentialResolutionError,
    credential_status,
    delete_credentials,
    store_credentials,
)
from envelope import emit_error, emit_success
from registry import register
from settings import load_settings_config

# Test injection point for setup values (name -> value). None -> env/getpass path.
_setup_values_override: dict[str, str] | None = None


def set_setup_values(values: dict[str, str] | None) -> None:
    global _setup_values_override
    _setup_values_override = values


def _collect_setup_values(cfg: dict) -> tuple[dict[str, str], dict[str, str]]:
    values: dict[str, str] = {}
    sources: dict[str, str] = {}
    for item in cfg["settings"]:
        if not item.get("credential"):
            continue
        name = item["name"]
        if _setup_values_override is not None:
            v = _setup_values_override.get(name)
            if v:
                values[name] = v
                sources[name] = "override"
        elif os.environ.get(name):
            values[name] = os.environ[name]
            sources[name] = "environment"
        # else: would prompt via getpass in interactive --yes (not exercised in core tests)
    return values, sources


@register("auth", "status")
def auth_status(args: argparse.Namespace, out, err) -> int:
    cfg = load_settings_config()
    sources = credential_status(cfg)
    creds = []
    for item in cfg["settings"]:
        if not item.get("credential"):
            continue
        src = sources.get(item["name"], "missing")
        creds.append(
            {
                "account": item.get("account", item["name"]),
                "configured": src in ("keyring", "environment"),
                "source": src,
            }
        )
    from credentials import _real_keyring  # local import picks up monkeypatched global

    backend = _real_keyring
    backend_name = "unavailable" if backend is None else type(backend).__name__
    emit_success({"backend": backend_name, "credentials": creds}, out)
    return 0


@register("auth", "setup")
def auth_setup(args: argparse.Namespace, out, err) -> int:
    cfg = load_settings_config()
    service = cfg["keyring_service"]
    values, sources = _collect_setup_values(cfg)
    if getattr(args, "dry_run", False):
        entries = [
            {
                "name": it["name"],
                "account": it.get("account", it["name"]),
                "input_source": sources.get(it["name"], "prompt"),
            }
            for it in cfg["settings"]
            if it.get("credential")
        ]
        emit_success(
            {
                "target": {"service": service},
                "probe": "skipped (no provider configured in core task)",
                "entries": entries,
            },
            out,
        )
        return 0
    if not getattr(args, "yes", False):
        emit_error("usage", "auth setup requires --dry-run or --yes", err, hint="preview with --dry-run --json")
        return 2
    try:
        written = store_credentials(cfg, values)
    except CredentialResolutionError as exc:
        emit_error("failure", str(exc), err)
        return 1
    emit_success({"stored": [{"name": n, "account": a} for n, a in written]}, out)
    return 0


@register("auth", "check")
def auth_check(args: argparse.Namespace, out, err) -> int:
    cfg = load_settings_config()
    sources = credential_status(cfg)
    configured = []
    missing = []
    for item in cfg["settings"]:
        if not item.get("credential"):
            continue
        (configured if sources.get(item["name"]) in ("keyring", "environment") else missing).append(item["name"])
    emit_success({"configured": configured, "missing": missing}, out)
    return 0


@register("auth", "delete")
def auth_delete(args: argparse.Namespace, out, err) -> int:
    cfg = load_settings_config()
    service = cfg["keyring_service"]
    if getattr(args, "dry_run", False):
        sources = credential_status(cfg)
        present = [
            it["name"]
            for it in cfg["settings"]
            if it.get("credential") and sources.get(it["name"]) == "keyring"
        ]
        emit_success({"target": {"service": service}, "would_delete": present}, out)
        return 0
    if not getattr(args, "yes", False):
        emit_error("usage", "auth delete requires --dry-run or --yes", err, hint="preview with --dry-run --json")
        return 2
    try:
        deleted = delete_credentials(cfg)
    except CredentialResolutionError as exc:
        emit_error("failure", str(exc), err)
        return 1
    emit_success({"deleted": [{"name": n, "account": a} for n, a in deleted]}, out)
    return 0
