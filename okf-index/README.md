# okf-index

A universal knowledge-base builder for AI agents. Ingests content from Confluence, websites, documents, Telegram, and personal notes into an [Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) bundle — plain markdown + YAML frontmatter, browsable in Obsidian, searchable with SQLite FTS5.

```bash
cd okf-index
uv run --quiet --script scripts/run.py schema get --json
```

## Ingest from anywhere

```bash
# Personal notes
uv run --script scripts/run.py note add "Meeting notes..." --title "Weekly" --yes --json

# Local documents (md, txt, pdf, docx, pptx, html)
uv run --script scripts/run.py doc ingest ./docs --recursive --yes --json

# Confluence pages (single or tree with --depth)
uv run --script scripts/run.py confluence ingest 123456 --yes --json
uv run --script scripts/run.py confluence ingest 123456 --depth 2 --yes --json   # page + children + grandchildren
uv run --script scripts/run.py confluence ingest 'https://confluence.example.com/spaces/AI/pages/123456/Title' --depth -1 --yes --json  # URL + full tree

# Websites
uv run --script scripts/run.py web fetch https://example.com --yes --json
uv run --script scripts/run.py web crawl https://docs.example.com --max-depth 2 --max-pages 10 --yes --json

# Telegram channels
uv run --script scripts/run.py telegram ingest channel_name --yes --json

# Declarative batch (sources.yaml)
uv run --script scripts/run.py bundle build --from sources.yaml --yes --json
```

## Search and browse

```bash
uv run --script scripts/run.py search "query" --tag important --type Note --json
uv run --script scripts/run.py tag list --json
uv run --script scripts/run.py bundle visualize  # self-contained HTML graph
```

Always use `--quiet` with `uv run --script` to suppress uv's metadata on stderr (avoids breaking JSON pipes).

Open `OKF_VAULT_PATH` (default `~/okf-vault`) in [Obsidian](https://obsidian.md) as a vault.

## Resources

| Resource | Actions |
|----------|---------|
| `schema` | get |
| `doctor` | check |
| `auth` | status, setup, check, delete |
| `note` | add |
| `doc` | ingest (md/txt/pdf/docx/pptx/html) |
| `bundle` | validate, index, stats, visualize, build |
| `search` | search (FTS5 + tag/type/limit) |
| `tag` | list, show |
| `confluence` | get, search, ingest |
| `web` | fetch, crawl |
| `telegram` | ingest |

## Full configuration

### Core (always needed)

| Variable | Default | How to get |
|----------|---------|------------|
| `OKF_VAULT_PATH` | `~/okf-vault` | Keep default or point to your Obsidian vault |
| `OKF_INDEX_AUTO_CONFIRM` | — | Set to `1` for automation (CI/eval) |

### LLM enrichment (always-on, OpenAI-compatible protocol)

| Variable | How to get |
|----------|------------|
| `ENRICH_API_KEY` | Your API key (any OpenAI-compatible provider) |
| `ENRICH_BASE_URL` | Custom endpoint base URL (optional; empty = default) |
| `OKF_ENRICH_MODEL` | Model id (default: gpt-4.1-mini) |

### Confluence

| Variable | How to get |
|----------|------------|
| `CONFLUENCE_BASE_URL` | Your Confluence instance URL, e.g. `https://your-company.atlassian.net` |
| `CONFLUENCE_API_TOKEN` | Confluence → Profile → Personal Access Tokens → `Create token` |

### Telegram

| Variable | How to get |
|----------|------------|
| `TELEGRAM_API_ID` | [my.telegram.org](https://my.telegram.org) → API development tools |
| `TELEGRAM_API_HASH` | Same place |

### Storing credentials

```bash
cd okf-index
uv run --script scripts/run.py auth setup --dry-run --json  # preview
uv run --script scripts/run.py auth setup --yes --json       # store in OS keyring
```

Never put tokens in files, `.env`, or `settings.json`. Credentials live in the OS keyring (macOS Keychain, Windows Credential Locker, Linux Secret Service) and environment variables are a fallback.

## OKF format

Every concept is a markdown file with YAML frontmatter:

```markdown
---
type: Note
title: My Note
description: LLM-generated summary
tags: [tag1, tag2]
source: note
---
Body in standard markdown.
```

Spec: [OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md).

## Requirements

- Python ≥ 3.11 + `uv`
- Optional per connector: `google-generativeai`, `crawl4ai`+`playwright`, `markitdown`, `markdownify`+`beautifulsoup4`, `telethon` (all installed automatically by `uv run --script`)

## Tests

```bash
cd okf-index
uv run --with pytest --with pyyaml --with unidecode --with requests --with beautifulsoup4 --with markdownify pytest -q
# 85 tests, ~0.8s
```
