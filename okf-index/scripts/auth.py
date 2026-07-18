"""auth resource: credential lifecycle (status in this SCIU; setup/check/delete follow)."""
from __future__ import annotations

import argparse

from credentials import credential_status
from envelope import emit_success
from registry import register
from settings import load_settings_config


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
    # Backend name only; never any value.
    from credentials import _real_keyring  # local import to pick up monkeypatched global

    backend = _real_keyring
    backend_name = "unavailable" if backend is None else type(backend).__name__
    emit_success({"backend": backend_name, "credentials": creds}, out)
    return 0
