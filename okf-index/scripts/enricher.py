"""Pluggable LLM enrichment providers. Always-on ingest step (Q3 decision).

Factory create_provider() -> EnrichProvider | None via settings/credentials.
Falls back gracefully on import/network/rate-limit errors.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Protocol

from okf.concept import Concept

logger = logging.getLogger("okf-index.enricher")
MAX_BODY = 4000  # chars sent to LLM


@dataclass
class EnrichResult:
    description: str = ""
    tags: list[str] = field(default_factory=list)
    suggested_links: list[str] = field(default_factory=list)  # concept titles to link to


class EnrichProvider(Protocol):
    def enrich(self, concept: Concept, existing_titles: list[str]) -> EnrichResult: ...


class FakeEnrichProvider:
    """Deterministic test double. Returns canned results based on concept body hash."""
    def enrich(self, concept: Concept, existing_titles: list[str]) -> EnrichResult:
        body = concept.body or ""
        keys = [t for t in existing_titles if any(w in body.lower() for w in t.lower().split())]
        return EnrichResult(
            description=f"LLM-generated summary of: {body[:80].strip()!r}",
            tags=["auto-tag-1", "auto-tag-2"],
            suggested_links=keys[:3],
        )


def _prompt(concept: Concept, existing_titles: list[str]) -> str:
    return json.dumps(
        {
            "task": "Enrich an OKF knowledge concept",
            "concept": {
                "type": concept.type,
                "title": concept.title,
                "body": (concept.body or "")[:MAX_BODY],
            },
            "existing_concept_titles": existing_titles[:200],
            "output": {
                "description": "one-sentence summary (max 200 chars)",
                "tags": ["lowercase", "short", "descriptive"],
                "suggested_links": ["title of existing concept to link to (or empty list)"],
            },
        },
        ensure_ascii=False,
    )


def _parse(response_text: str) -> EnrichResult:
    try:
        data = json.loads(response_text)
        return EnrichResult(
            description=str(data.get("description", ""))[:200],
            tags=data.get("tags") or [],
            suggested_links=data.get("suggested_links") or [],
        )
    except (json.JSONDecodeError, TypeError):
        return EnrichResult()


def create_provider() -> EnrichProvider | None:
    """Factory: resolve provider from settings + credentials. Uses OpenAI-compatible protocol."""
    from settings import load_settings_config, resolve_runtime_settings

    cfg = load_settings_config()
    vals, _ = resolve_runtime_settings(cfg)
    model = vals.get("OKF_ENRICH_MODEL", "") or None
    base_url = vals.get("ENRICH_BASE_URL", "") or None

    try:
        from credentials import require_credentials
        creds = require_credentials(["ENRICH_API_KEY"], cfg)
        api_key = creds.get("ENRICH_API_KEY")
        if not api_key:
            logger.warning("ENRICH_API_KEY not configured; enrich will use stub")
            return None
        return OpenAICompatProvider(api_key, model=model, base_url=base_url)
    except Exception:
        logger.warning("ENRICH_API_KEY not configured; enrich will use stub")
        return None


class OpenAICompatProvider:
    def __init__(self, api_key: str, model: str | None = None, base_url: str | None = None):
        from openai import OpenAI

        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)
        self.model = model or "gpt-4.1-mini"
        self._base_url = base_url

    def enrich(self, concept: Concept, existing_titles: list[str]) -> EnrichResult:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": _prompt(concept, existing_titles)}],
                max_tokens=256,
                response_format={"type": "json_object"},
            )
            return _parse(resp.choices[0].message.content or "")
        except Exception:
            logger.exception("Enrichment failed; falling back to stub")
            return EnrichResult()

    def probe(self) -> str:
        label = self._base_url or "openai"
        return f"openai-compat/{self.model} @ {label}"
