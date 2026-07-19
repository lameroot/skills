"""Enrichment orchestrator. Mechanical tags (always) + LLM (if configured) + cross-links."""
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


def _mechanical_tags(concept: Concept) -> list[str]:
    """Derive baseline tags from source metadata — always present, even without LLM."""
    tags: list[str] = []
    if concept.source == "confluence" and concept.resource:
        # /spaces/SPACEKEY/pages/...
        if "/spaces/" in concept.resource:
            parts = concept.resource.split("/spaces/")
            if len(parts) > 1:
                tags.append(parts[1].split("/")[0].lower())
    elif concept.source == "web" and concept.resource:
        from urllib.parse import urlparse
        domain = urlparse(concept.resource).netloc.replace("www.", "").split(":")[0]
        if domain:
            tags.append(domain)
    elif concept.source == "doc":
        tags.append("document")
    elif concept.source == "note":
        tags.append("note")
    elif concept.source == "telegram":
        tags.append("telegram")
    return tags


def _get_provider() -> EnrichProvider | None:
    global _provider
    if _provider is None:
        _provider = create_provider() or False
    return _provider if _provider else None  # type: ignore[return-value]


def set_provider(p: EnrichProvider | None) -> None:
    global _provider
    _provider = p


def enrich(
    concept: Concept,
    title_to_path: dict[str, str] | None = None,
) -> Concept:
    """Always-on enrichment: mechanical tags + LLM (if configured) + cross-links."""
    existing_titles = list(title_to_path.keys()) if title_to_path else []

    # Mechanical tags — always
    mech_tags = _mechanical_tags(concept)

    # LLM enrichment — if configured
    prov = _get_provider()
    result: EnrichResult | None = None
    if prov:
        try:
            result = prov.enrich(concept, existing_titles)
        except Exception:
            result = None

    # Description
    if result and result.description:
        concept.description = result.description
    else:
        concept.description = f"[stub] {_first(concept.body)}"

    # Tags: mechanical + LLM (merged, deduped)
    llm_tags = result.tags if result else []
    concept.tags = list(dict.fromkeys(mech_tags + llm_tags))  # preserve order, dedup

    # Cross-links: map LLM-suggested titles to real concept paths
    if result and result.suggested_links and title_to_path:
        links = []
        for title in result.suggested_links:
            rel = title_to_path.get(title)
            if rel:
                links.append(f"* [{title}](/{rel})")
        if links:
            concept.body = (concept.body or "").rstrip() + "\n\n## See also\n\n" + "\n".join(links)

    return concept
