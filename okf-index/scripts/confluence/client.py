"""Confluence REST client (embedded, self-contained). Bearer auth via keyring/env."""
from __future__ import annotations

import requests
from requests.auth import HTTPBasicAuth

from credentials import require_credentials
from settings import load_settings_config


class ConfluenceClient:
    def __init__(self, base_url: str, username: str, api_token: str):
        self.base = base_url.rstrip("/")
        self.session = requests.Session()
        if username:
            self.session.auth = HTTPBasicAuth(username, api_token)
        else:
            self.session.headers["Authorization"] = f"Bearer {api_token}"
        self.session.headers["Accept"] = "application/json"

    def get_page(self, page_id: str) -> dict:
        resp = self.session.get(
            f"{self.base}/rest/api/content/{page_id}",
            params={"expand": "body.storage,space,version"},
            timeout=30,
        )
        if resp.status_code == 404:
            raise _not_found(page_id)
        resp.raise_for_status()
        return resp.json()

    def search(self, cql: str, limit: int = 20) -> list[dict]:
        resp = self.session.get(
            f"{self.base}/rest/api/search",
            params={"cql": cql, "expand": "content.body.storage", "limit": limit},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])

    def get_children(self, page_id: str, limit: int = 50) -> list[dict]:
        resp = self.session.get(
            f"{self.base}/rest/api/content/{page_id}/child/page",
            params={"limit": limit, "expand": "body.storage,space,version"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])


def _not_found(page_id: str):
    from errors import NotFoundError
    return NotFoundError(f"page not found: {page_id}", code="page_not_found")


def html_to_markdown(html: str) -> str:
    try:
        from markdownify import markdownify
    except ImportError:
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "lxml" if False else "html.parser").get_text()
    return markdownify(html or "", heading_style="ATX")


def create_client() -> ConfluenceClient:
    cfg = load_settings_config()
    creds = require_credentials(["CONFLUENCE_API_TOKEN"], cfg)
    vals, _ = __import__("settings").resolve_runtime_settings(cfg)
    base = vals.get("CONFLUENCE_BASE_URL") or ""
    if not base:
        from errors import UsageError
        raise UsageError("CONFLUENCE_BASE_URL is not configured", code="confluence_no_base_url")
    username = ""
    try:
        u = require_credentials(["CONFLUENCE_USERNAME"], cfg)
        username = u.get("CONFLUENCE_USERNAME", "")
    except Exception:
        pass  # username is optional
    return ConfluenceClient(base, username, creds["CONFLUENCE_API_TOKEN"])


# Test injection point
_test_client: ConfluenceClient | None = None


def get_client() -> ConfluenceClient:
    global _test_client
    if _test_client is not None:
        return _test_client
    return create_client()


def set_test_client(client: ConfluenceClient | None) -> None:
    global _test_client
    _test_client = client
