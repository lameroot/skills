"""web resource: fetch/crawl URLs as OKF WebPage concepts via crawl4ai."""
from __future__ import annotations

import argparse
import asyncio

from connectors import is_confirmed, is_dry_run
from enrich import enrich
from envelope import emit_error, emit_success
from okf.concept import Concept
from okf.writer import list_titles, write_concept
from registry import register
from vault import resolve_vault

_results_override = None  # test injection; list of (url, markdown, title) tuples


def _crawl_results(url: str, *, max_depth: int = 1, max_pages: int = 10, allowed_host: str = "") -> list[tuple[str, str, str]]:
    """Return [(url, markdown, title), ...]. Real impl uses crawl4ai; tests use override."""
    global _results_override
    if _results_override is not None:
        return _results_override

    # Real crawl4ai path (sync wrapper around async API)
    async def _do():
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
        from crawl4ai.deep_crawling.filters import ContentTypeFilter, FilterChain, URLPatternFilter
        from crawl4ai import DefaultMarkdownGenerator

        config = CrawlerRunConfig(
            markdown_generator=DefaultMarkdownGenerator(),
            deep_crawl_strategy=BFSDeepCrawlStrategy(
                max_depth=max_depth,
                include_external=False,
                filter_chain=FilterChain([
                    URLPatternFilter(patterns=["*.html", "*.htm", "*/"]),
                    ContentTypeFilter(allowed_types=["text/html"]),
                ]),
            ),
            verbose=False, stream=False, screenshot=False,
        ) if max_depth > 1 else CrawlerRunConfig(markdown_generator=DefaultMarkdownGenerator(), verbose=False)
        browser = BrowserConfig(headless=True, java_script_enabled=False)
        async with AsyncWebCrawler(config=browser) as crawler:
            result = await crawler.arun(url, config=config)
        items = []
        # result may be single CrawlResult or list
        for item in ([result] if not isinstance(result, list) else result):
            md = getattr(item, "markdown", "") or ""
            t = getattr(item, "metadata", {}) or {}
            u = getattr(item, "url", "") or t.get("url", url)
            title = t.get("title", "") or (md.split("\n")[0].lstrip("# ") if md else u.split("/")[-1])
            items.append((u, md, title))
        return items[:max_pages]

    return asyncio.run(_do())


@register("web", "fetch")
def web_fetch(args: argparse.Namespace, out, err) -> int:
    vault = resolve_vault(create=not is_dry_run(args))
    url = args.url
    try:
        results = _crawl_results(url, max_depth=0)
    except Exception as exc:
        emit_error("failure", f"web fetch failed: {exc}", err)
        return 1
    if not results:
        emit_error("not_found", f"no content fetched from {url}", err, exit_code=3)
        return 3
    u, md, title = results[0]
    concept = Concept(type="WebPage", title=title or url, body=md, source="web", resource=u)
    concept.source_id = f"web-{hash(u) & 0xFFFFFFFF:08x}"
    if is_dry_run(args):
        emit_success({"dry_run": True, "target": {"type": "WebPage", "title": title, "url": u}}, out)
        return 0
    if not is_confirmed(args):
        emit_error("usage", "web fetch requires --dry-run or --yes", err)
        return 2
    enrich(concept, list_titles(vault))
    path = write_concept(vault, concept)
    emit_success({"created": {"path": str(path.relative_to(vault)), "type": "WebPage", "title": title}}, out)
    return 0


@register("web", "crawl")
def web_crawl(args: argparse.Namespace, out, err) -> int:
    vault = resolve_vault(create=not is_dry_run(args))
    url = args.url
    max_depth = getattr(args, "max_depth", 2) or 2
    max_pages = getattr(args, "max_pages", 10) or 10
    try:
        results = _crawl_results(url, max_depth=max_depth, max_pages=max_pages)
    except Exception as exc:
        emit_error("failure", f"web crawl failed: {exc}", err)
        return 1
    if is_dry_run(args):
        emit_success({"dry_run": True, "would_crawl": len(results), "urls": [r[0] for r in results]}, out)
        return 0
    if not is_confirmed(args):
        emit_error("usage", "web crawl requires --dry-run or --yes", err)
        return 2
    existing = list_titles(vault)
    created = []
    for u, md, title in results:
        concept = Concept(type="WebPage", title=title or u, body=md, source="web", resource=u)
        concept.source_id = f"web-{hash(u) & 0xFFFFFFFF:08x}"
        enrich(concept, existing)
        path = write_concept(vault, concept)
        created.append(str(path.relative_to(vault)))
    emit_success({"created": created, "count": len(created)}, out)
    return 0
