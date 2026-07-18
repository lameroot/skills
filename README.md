# Skills

Agent skills — self-contained CLI-backed tools for AI agents (Pi, Codex, etc.).

## Skills in this repo

### [okf-index](okf-index/)

A universal knowledge-base builder. Ingests content from Confluence, websites, documents, Telegram, and personal notes into an [OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) bundle — plain markdown browsable in Obsidian, searchable with SQLite FTS5, enriched with LLM-generated tags and summaries.

```bash
cd okf-index
uv run --script scripts/run.py schema get --json
```

See [okf-index/README.md](okf-index/README.md) for full docs, resource table, and configuration guide.
