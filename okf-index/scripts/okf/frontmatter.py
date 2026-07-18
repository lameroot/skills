"""OKF frontmatter (YAML) emit/parse. Cyrillic-safe via allow_unicode."""
from __future__ import annotations

import re

import yaml

_FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.S)


def dump(meta: dict, body: str = "") -> str:
    fm = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, default_flow_style=False).strip()
    return f"---\n{fm}\n---\n\n{body}".rstrip() + "\n"


def parse(text: str) -> tuple[dict, str]:
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    if not isinstance(meta, dict):
        return {}, text
    return meta, m.group(2)
