"""Injectable clock for deterministic `--help` time context.

AGENTS.md: help must show `Current time (<IANA>): <ISO-8601> · Unix: <ts>` at top,
resource, and leaf --help; NEVER in JSON stdout / command output. Tests inject a
fixed epoch via set_clock() rather than comparing real time.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

DEFAULT_TZ = "Europe/Moscow"

# Test injection point. None in production -> real wall clock.
_now_override: float | None = None


def set_clock(epoch: float | None) -> None:
    """Freeze the clock to `epoch` (Unix seconds), or release with None."""
    global _now_override
    _now_override = epoch


def now_epoch() -> float:
    return _now_override if _now_override is not None else time.time()


def _resolve_tz(name: str):
    try:
        return ZoneInfo(name)
    except Exception:  # noqa: BLE001 - fall back to UTC if tz name unknown / tzdata missing
        return timezone.utc


def time_line(tz: str = DEFAULT_TZ) -> str:
    epoch = now_epoch()
    dt = datetime.fromtimestamp(epoch, tz=_resolve_tz(tz))
    iso = dt.isoformat(timespec="seconds")
    return f"Current time ({tz}): {iso} · Unix: {int(epoch)}"
