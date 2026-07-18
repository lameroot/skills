"""Connector shared helpers: mutation gate (dry-run / --yes / OKF_INDEX_AUTO_CONFIRM)."""
from __future__ import annotations

import os


def is_dry_run(args) -> bool:
    return bool(getattr(args, "dry_run", False))


def is_confirmed(args) -> bool:
    if getattr(args, "yes", False):
        return True
    return os.environ.get("OKF_INDEX_AUTO_CONFIRM", "").strip().lower() in ("1", "true", "yes", "on")
