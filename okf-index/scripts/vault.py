"""Vault resolution + safety. Reject vault inside skill dir; ensure .okf/ gitignored.

NEVER git init/commit. Creates the vault dir if its parent is writable.
"""
from __future__ import annotations

from pathlib import Path

from errors import UsageError
from settings import resolve_runtime_settings

SKILL_ROOT = Path(__file__).resolve().parents[1]


def resolve_vault(path: str | Path | None = None, skill_root: str | Path | None = None, create: bool = True) -> Path:
    if path is None:
        values, _sources = resolve_runtime_settings()
        path = values.get("OKF_VAULT_PATH", "~/okf-vault")
    p = Path(path).expanduser().resolve()
    root = Path(skill_root) if skill_root is not None else SKILL_ROOT
    try:
        p.relative_to(root)
    except ValueError:
        pass  # outside skill dir -> ok
    else:
        raise UsageError(
            f"vault must not be inside the skill directory: {p}",
            code="vault_in_skill_dir",
            hint="set OKF_VAULT_PATH to a directory outside the skill",
        )
    if not create:
        return p
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise UsageError(f"cannot create/use vault path {p}: {exc}", code="vault_not_writable") from exc
    gi = p / ".gitignore"
    current = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if ".okf/" not in current:
        with gi.open("a", encoding="utf-8") as fh:
            fh.write(("\n" if current and not current.endswith("\n") else "") + ".okf/\n")
    return p
