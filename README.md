# Skills

Agent skills — self-contained CLI-backed tools for Pi, Codex, and other AI coding agents.

## okf-index

A universal knowledge-base builder. Ingests content from multiple sources into an [Open Knowledge Format (OKF) v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) bundle — plain markdown + YAML frontmatter, browsable in Obsidian, searchable with SQLite FTS5.

### Quick start

```bash
cd okf-index
uv run --script scripts/run.py schema get --json   # see all commands
uv run --script scripts/run.py doctor --json        # check readiness
```

### Ingest from anywhere

```bash
# Personal notes
uv run --script scripts/run.py note add "Meeting notes..." --title "Weekly" --yes --json

# Local documents (md, txt, pdf, docx, pptx, html)
uv run --script scripts/run.py doc ingest ./docs --recursive --yes --json

# Confluence pages
uv run --script scripts/run.py confluence ingest 123456 --yes --json

# Websites
uv run --script scripts/run.py web fetch https://example.com --yes --json
uv run --script scripts/run.py web crawl https://docs.example.com --max-depth 2 --max-pages 10 --yes --json

# Telegram channels
uv run --script scripts/run.py telegram ingest channel_name --yes --json

# Declarative batch (sources.yaml)
uv run --script scripts/run.py bundle build --from sources.yaml --yes --json
```

### Search and browse

```bash
# Full-text search with tag/type filters
uv run --script scripts/run.py search "query" --tag important --type Note --json

# Browse tags
uv run --script scripts/run.py tag list --json

# Interactive graph (self-contained HTML)
uv run --script scripts/run.py bundle visualize --out vault/viz.html
```

Open `OKF_VAULT_PATH` (default `~/okf-vault`) in Obsidian as a vault — cross-links, tags, and graph view work natively.

### Resources

| Resource | Actions |
|----------|---------|
| `schema` | get |
| `doctor` | check |
| `auth` | status, setup, check, delete |
| `note` | add |
| `doc` | ingest |
| `bundle` | validate, index, stats, visualize, build |
| `search` | search (FTS5) |
| `tag` | list, show |
| `confluence` | get, search, ingest |
| `web` | fetch, crawl |
| `telegram` | ingest |

### Key env vars

| Variable | Default | Purpose |
|----------|---------|---------|
| `OKF_VAULT_PATH` | `~/okf-vault` | Bundle root directory |
| `OKF_INDEX_AUTO_CONFIRM` | — | Skip mutation prompts (`=1`) |

Credentials are stored in the OS keyring via `uv run --script scripts/run.py auth setup` (never in files).

### OKF format

Every concept is a markdown file with YAML frontmatter:

```markdown
---
type: Note
title: My Note
description: A summary
tags: [tag1, tag2]
timestamp: 2026-07-18T00:00:00Z
source: note
---

Body in standard markdown with [cross-links](/path/to/other.md).
```

OKF bundles are git-friendly, Obsidian-native, and agent-readable without SDKs. Full spec: [OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md).

### Requirements

- Python ≥ 3.11
- `uv` (installs dependencies automatically via PEP 723)
- `keyring` for credential storage (macOS Keychain, Windows Credential Locker, Linux Secret Service)
- Optional, per connector:
  - `google-generativeai` — LLM enrichment (Gemini)
  - `crawl4ai` + `playwright` — web crawl
  - `markitdown` — office formats (pdf, docx, pptx)
  - `markdownify` + `beautifulsoup4` — Confluence HTML→markdown
  - `telethon` — Telegram (real client)

### Tests

```bash
cd okf-index
uv run --with pytest --with pyyaml --with unidecode --with requests --with beautifulsoup4 --with markdownify pytest -q
# 85 tests, ~0.8s
```
