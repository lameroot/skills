---
name: okf-index
description: >-
  Use when the user wants to build, fill, or search an Open Knowledge Format (OKF)
  knowledge base from Confluence, websites, local documents, or own notes, and browse
  it in Obsidian. Produces OKF v0.1 markdown bundles and searches them via SQLite FTS5.
version: 0.1.0
schema_command: uv run --script scripts/run.py schema get --json
launcher:
  cwd: skill-root
  command: uv run --script scripts/run.py
metadata:
  tags: knowledge, okf, obsidian, search
allowed-tools: Read, Bash(uv run --script scripts/run.py *)
---

# okf-index (stub)

OKF knowledge-base builder. Scaffold in progress — see `schema get --json` for the
live command surface.

```bash
cd okf-index
uv run --script scripts/run.py schema get --json
```
