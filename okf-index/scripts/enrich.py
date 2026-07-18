"""Enrichment orchestrator. Calls the configured LLM provider; falls back to stub."""
from __future__ import annotations

from enricher import EnrichProvider, EnrichResult, create_provider
from okf.concept import Concept

_provider: EnrichProvider | None | bool = None  # None=uninitialized, False=stub, instance=provider


def _first(text: str) -> str:
    for line in (text or "").splitlines():
        s = line.strip()
        if s:
            return s.lstrip("#").strip()
    return ""


first_line = _first  # public alias used by connectors/note.py


def _get_provider() -> EnrichProvider | None:
    global _provider
    if _provider is None:
        _provider = create_provider() or False
    return _provider if _provider else None  # type: ignore[return-value]


def set_provider(p: EnrichProvider | None) -> None:
    global _provider
    _provider = p


def enrich(concept: Concept, existing_titles: list[str] | None = None) -> Concept:
    """Always-on enrichment. Provider → ok; stub → description=[stub] marker."""
    existing = existing_titles or []
    prov = _get_provider()
    result: EnrichResult | None = None
    if prov:
        try:
            result = prov.enrich(concept, existing)
        except Exception:
            result = None
    if result is None:
        concept.description = f"[stub] {_first(concept.body)}"
        return concept
    concept.description = result.description or concept.description
    if result.tags:
        concept.tags = list(result.tags)
    if result.suggested_links:
        links_section = "\n\n## See also\n\n" + "\n".join(
            f"* [{t}](/path/to/{t.lower().replace(' ', '-')}.md)" for t in result.suggested_links
        )
        concept.body = (concept.body or "").rstrip() + links_section
    return concept
