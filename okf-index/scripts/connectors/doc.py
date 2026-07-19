"""doc resource: ingest local documents (.md/.txt/.pdf/.docx/.pptx/.html) as OKF Document concepts."""
from __future__ import annotations

import argparse
from pathlib import Path

from connectors import is_confirmed, is_dry_run
from enrich import enrich
from envelope import emit_error, emit_success
from errors import NotFoundError
from okf.concept import Concept
from okf.writer import list_concepts, write_concept
from registry import register
from vault import resolve_vault

MD_TEXT = {".md", ".txt"}
OFFICE = {".pdf", ".docx", ".pptx", ".html", ".htm"}
ALLOWED = MD_TEXT | OFFICE


def _convert_office(path: Path) -> str:
    """Convert office/pdf/html to markdown via markitdown."""
    try:
        from markitdown import MarkItDown

        return MarkItDown().convert(source=str(path)).text_content
    except ImportError:
        raise RuntimeError("markitdown not installed. Install: pip install 'markitdown[all]'")
    except Exception as exc:
        return f"[conversion failed: {exc}]"


def _collect(target: Path, recursive: bool) -> tuple[list[Path], list[Path]]:
    files: list[Path] = []
    skipped: list[Path] = []
    if target.is_dir():
        it = target.rglob("*") if recursive else target.glob("*")
        for f in it:
            if not f.is_file():
                continue
            (files if f.suffix.lower() in ALLOWED else skipped).append(f)
    elif target.is_file():
        (files if target.suffix.lower() in ALLOWED else skipped).append(target)
    else:
        raise NotFoundError("not_found", f"path not found: {target}")
    return files, skipped


@register("doc", "ingest")
def doc_ingest(args: argparse.Namespace, out, err) -> int:
    target = Path(args.path)
    files, skipped = _collect(target, args.recursive)
    vault = resolve_vault(create=not is_dry_run(args))

    if is_dry_run(args):
        emit_success(
            {"dry_run": True, "would_ingest": [str(f) for f in sorted(files)], "skipped": [s.name for s in skipped]},
            out,
        )
        return 0
    if not is_confirmed(args):
        emit_error("usage", "doc ingest requires --dry-run or --yes", err, hint="set OKF_INDEX_AUTO_CONFIRM=1")
        return 2

    created = []
    title_to_path = list_concepts(vault)
    for f in sorted(files):
        if f.suffix.lower() in MD_TEXT:
            body = f.read_text(encoding="utf-8", errors="replace")
        else:
            body = _convert_office(f)
        concept = Concept(type="Document", title=f.stem, body=body, source="doc", resource=str(f))
        enrich(concept, title_to_path)
        path = write_concept(vault, concept)
        created.append(str(path.relative_to(vault)))
    emit_success({"created": created, "skipped": [s.name for s in skipped]}, out)
    return 0
