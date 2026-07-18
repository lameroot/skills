"""OKF Concept model + producer keys + stable source_id (content-derived, move-safe)."""
from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass, field


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text or "").replace("\r\n", "\n")


def content_hash(body: str) -> str:
    return hashlib.sha256(_normalize(body).encode("utf-8")).hexdigest()


def make_source_id(source: str, body: str) -> str:
    """Stable across path moves: derived from source + content, never from an absolute path."""
    return f"{source}-{hashlib.sha256(_normalize(body).encode('utf-8')).hexdigest()[:12]}"


@dataclass
class Concept:
    type: str
    title: str = ""
    body: str = ""
    description: str = ""
    resource: str = ""
    tags: list[str] = field(default_factory=list)
    timestamp: str = ""
    source: str = ""
    source_id: str = ""
    okf_version: str = "0.1"

    def frontmatter(self) -> dict:
        if not self.type or not str(self.type).strip():
            raise ValueError("OKF concept requires a non-empty 'type'")
        meta: dict = {"type": self.type}
        if self.title:
            meta["title"] = self.title
        if self.description:
            meta["description"] = self.description
        if self.resource:
            meta["resource"] = self.resource
        if self.tags:
            meta["tags"] = list(self.tags)
        if self.timestamp:
            meta["timestamp"] = self.timestamp
        if self.source:
            meta["source"] = self.source
        if self.source_id:
            meta["source_id"] = self.source_id
        meta["content_hash"] = content_hash(self.body)
        meta["okf_version"] = self.okf_version
        return meta
