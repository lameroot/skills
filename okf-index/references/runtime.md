# Runtime

Always `cd` into the skill directory first.

```bash
cd okf-index
uv run --script scripts/run.py schema get --json
uv run --script scripts/run.py <resource> [subresource] <action> --help
```

## Launcher

- `cwd`: skill root (`okf-index/`)
- `command`: `uv run --script scripts/run.py`
- `schema`: `uv run --script scripts/run.py schema get --json`

## Envelope

- Success: `{"success":true,"data":...}` on stdout, exit 0.
- Error: `{"success":false,"error":{"code","message","retriable"[,"hint"]}}` on stderr, semantic exit code.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Failure (runtime, provider, internal) |
| 2 | Usage error (unknown command/flag, missing required arg) |
| 3 | Not found (resource missing) |
| 4 | Permission denied (auth, keyring unavailable) |
| 5 | Conflict |

## Key env vars

| Var | Default | Purpose |
|-----|---------|---------|
| `OKF_VAULT_PATH` | `~/okf-vault` | Bundle root (non-secret) |
| `OKF_INDEX_AUTO_CONFIRM` | `0` | Skip mutation confirmation (`1`=`true`=`yes`) |
| `ENRICH_API_KEY` | — | LLM enrichment API key (credential; OpenAI-compatible protocol) |
| `ENRICH_BASE_URL` | — | Custom base URL for the enrichment endpoint (optional) |
| `OKF_ENRICH_MODEL` | — | Override model id |
| `CONFLUENCE_BASE_URL` | — | Confluence instance URL |
| `CONFLUENCE_API_TOKEN` | — | Confluence API token (credential) |
| `CONFLUENCE_USERNAME` | — | Confluence login (credential; optional — for Bearer-only leave empty) |

## CLI grammar

`resource [subresource] action [args...]`. Examples:

```bash
uv run --script scripts/run.py schema get --json
uv run --script scripts/run.py auth status --json
uv run --script scripts/run.py note add "text" --title "Title" --yes --json
uv run --script scripts/run.py search "query" --tag tag1 --limit 10 --json
```
