"""Enrichment STUB. No LLM in the core task — derives a description only.

Task (later) swaps enrich() for a provider-backed pass (description + tags + link suggestions).
This stub is intentionally visible as a stub, never masquerading as real LLM output.
"""
from __future__ import annotations

from okf.concept import Concept


def first_line(body: str) -> str:
    for line in (body or "").splitlines():
        s = line.strip()
        if not s:
            continue
        return s.lstrip("#").strip()
    return ""


def enrich(concept: Concept) -> Concept:
    """STUB: identity except description = first non-empty heading/line when absent."""
    if not concept.description:
        concept.description = first_line(concept.body)
    return concept
