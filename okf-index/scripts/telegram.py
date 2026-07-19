"""telegram resource: ingest channel messages as OKF TelegramMessage concepts (mock for tests)."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone

from connectors import is_confirmed, is_dry_run
from enrich import enrich
from envelope import emit_error, emit_success
from okf.concept import Concept
from okf.writer import list_concepts, write_concept
from registry import register
from vault import resolve_vault

_test_messages: list[dict] | None = None  # test injection: [{text, date, id}]


def _fetch(channel: str, limit: int = 50) -> list[dict]:
    global _test_messages
    if _test_messages is not None:
        return _test_messages[:limit]
    # Real telethon path (untestable without API credentials)
    try:
        from settings import load_settings_config
        from credentials import require_credentials

        cfg = load_settings_config()
        creds = require_credentials(["TELEGRAM_API_ID", "TELEGRAM_API_HASH"], cfg)
        # Simplified: telethon client setup (requires user to install telethon)
        # Not implemented in core; production users install telethon and set credentials.
        raise RuntimeError("telethon not installed or credentials not configured")
    except Exception as exc:
        raise RuntimeError(f"Telegram unavailable: {exc}") from exc


@register("telegram", "ingest")
def telegram_ingest(args: argparse.Namespace, out, err) -> int:
    channel = args.channel
    limit = min(getattr(args, "limit", 50) or 50, 200)
    try:
        messages = _fetch(channel, limit)
    except Exception as exc:
        emit_error("failure", str(exc), err)
        return 1

    vault = resolve_vault(create=not is_dry_run(args))
    if is_dry_run(args):
        emit_success({"dry_run": True, "would_ingest": len(messages), "channel": channel}, out)
        return 0
    if not is_confirmed(args):
        emit_error("usage", "telegram ingest requires --dry-run or --yes", err, hint="set OKF_INDEX_AUTO_CONFIRM=1")
        return 2

    existing = list_concepts(vault)
    created = []
    for msg in messages:
        body = msg.get("text", "")
        mid = str(msg.get("id", ""))
        date = msg.get("date", "")
        title = f"tg-{channel}-{mid}"
        concept = Concept(type="TelegramMessage", title=title, body=body, source="telegram", resource=f"tg://{channel}/{mid}")
        concept.source_id = f"telegram-{channel}-{mid}"
        concept.timestamp = date
        enrich(concept, existing)
        path = write_concept(vault, concept)
        created.append(str(path.relative_to(vault)))
    emit_success({"created": created, "count": len(created)}, out)
    return 0
