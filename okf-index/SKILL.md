---
name: okf-index
description: >-
  Use when the user wants to build, fill, or search an Open Knowledge Format (OKF)
  knowledge base from Confluence, websites, local documents, or own notes, and browse
  it in Obsidian. Produces OKF v0.1 markdown bundles and searches them via SQLite FTS5.
version: 0.1.0
schema_command: uv run --quiet --script scripts/run.py schema get --json
launcher:
  cwd: skill-root
  command: uv run --quiet --script scripts/run.py
auth:
  type: api_key
  precedence: [keyring, environment]
  docs: references/runtime.md
settings:
  manifest: config/settings.json
  precedence: [environment, default]
capabilities:
  - schema get for CLI introspection
  - auth status/setup/check/delete with OS keyring and env fallback
  - doctor atomic readiness check
  - note add for personal markdown notes
  - doc ingest for local .md/.txt files as OKF concepts
  - bundle validate OKF v0.1 conformance
  - bundle index SQLite FTS5 with WAL and incremental updates
  - bundle stats by type and source
  - search with FTS5, tag/type filters, Cyrillic-aware tokenizer
  - tag list/show with concept counts
metadata:
  tags: knowledge, okf, obsidian, search
  readonly: "false"
allowed-tools: >-
  Read, Bash(uv run --script scripts/run.py *)
---

# okf-index

Build, fill, and search OKF knowledge bases. Browse in Obsidian — plain markdown + YAML frontmatter.

```bash
cd okf-index
uv run --quiet --script scripts/run.py schema get --json
uv run --quiet --script scripts/run.py <resource> [subresource] <action> --help
```

## Required behavior

- **Never use `curl` or direct HTTP** — work only through this skill's CLI (`schema get --json` for full command list).
- Use `--json` in non-interactive agent contexts.
- `--help` prints `Current time (Europe/Moscow): <ISO-8601> · Unix: <ts>` at every level; JSON stdout/commannd output has no time.
- Credentials are keyring-first, env fallback. Never store tokens in repo.
- Mutations require `--dry-run --json` then `--yes --json`, or `OKF_INDEX_AUTO_CONFIRM=1`.
- Reads are bounded (`--limit`, `--tag`, `--type`).

## Decision tree

1. **Inspect available commands** → `schema get --json`.
2. **Check readiness** → `doctor --json`. Returns settings sources + keyring backend.
3. **Which credentials, never values** → `auth status --json`.
4. **Store a credential** → `auth setup --dry-run --json` then `--yes --json`.
5. **Write a personal note** → `note add "text" --title T [--file f] --yes --json`.
6. **Ingest local documents** → `doc ingest <FILE|DIR> [--recursive] --yes --json`.
7. **Validate an OKF vault** → `bundle validate --bundle <path> --json`.
8. **(Re)build the FTS5 index** → `bundle index [--rebuild] --yes --json`.
9. **See bundle stats** → `bundle stats --json`.
10. **Search** → `search "query" [--tag t] [--type t] [--limit N] --json`.
11. **Browse tags** → `tag list --json`, `tag show <tag> --json`.

## Read when needed

- Env vars, exit codes, JSON piping → [references/runtime.md](references/runtime.md)
- Mutation gate, secrets, vault safety → [references/safety.md](references/safety.md)
- OKF v0.1 format at a glance → [references/okf.md](references/okf.md)
