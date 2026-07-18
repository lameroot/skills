"""Slugify + collision resolution. ASCII slugs; Cyrillic falls back to transliteration."""
from __future__ import annotations

import hashlib
import re
import unicodedata

try:
    from unidecode import unidecode
except Exception:  # noqa: BLE001 - optional; sha1 fallback covers missing transliteration
    def unidecode(s: str) -> str:  # type: ignore[misc]
        return ""


def slugify(title: str) -> str:
    s = unicodedata.normalize("NFC", title or "").strip().lower()
    kept = "".join(ch if (ch.isascii() and ch.isalnum()) else "-" for ch in s)
    kept = re.sub(r"-+", "-", kept).strip("-")
    if kept:
        return kept[:80]
    t = re.sub(r"[^a-z0-9]+", "-", unidecode(title or "").lower()).strip("-")
    if t:
        return t[:80]
    return "concept-" + hashlib.sha1((title or "").encode("utf-8")).hexdigest()[:10]


def unique_slug(base: str, taken: set[str]) -> str:
    if base not in taken:
        return base
    i = 2
    while f"{base}-{i}" in taken:
        i += 1
    return f"{base}-{i}"
