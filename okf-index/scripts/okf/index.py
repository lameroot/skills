"""OKF index.md generator (SPEC §6). No frontmatter except bundle-root okf_version."""
from __future__ import annotations


def generate_index(items: list[dict], okf_version: str | None = None) -> str:
    """items: [{title, description, rel, type}]. Groups by type; root may carry okf_version."""
    by_type: dict[str, list[dict]] = {}
    for it in items:
        by_type.setdefault(it.get("type", "Other"), []).append(it)
    lines: list[str] = []
    if okf_version:
        lines += ["---", f'okf_version: "{okf_version}"', "---", ""]
    lines.append(f"# Index ({len(items)} concept{'s' if len(items) != 1 else ''})")
    for typ in sorted(by_type):
        lines += ["", f"## {typ}"]
        for it in sorted(by_type[typ], key=lambda x: x.get("title", "")):
            desc = f" - {it['description']}" if it.get("description") else ""
            lines.append(f"* [{it['title']}]({it['rel']}){desc}")
    return "\n".join(lines) + "\n"
