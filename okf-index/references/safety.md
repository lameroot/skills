# Safety

## Mutation gate

Mutating commands (`note add`, `doc ingest`, `bundle index`, `auth setup`, `auth delete`) require one of:

1. `--dry-run --json` → preview target; no write.
2. `--yes --json` → execute after preview.
3. `OKF_INDEX_AUTO_CONFIRM=1` → skip confirmation (for trusted automation/eval).

If none of the above: exits 2 with a usage hint.

## Secrets

- Credentials live ONLY in the OS keyring (set by `auth setup`) or in environment variables (fallback).
- `auth status` never prints values.
- `doctor` reports sources only (configured/missing), no values.
- Setting default (non-secret) values: `config/settings.json` manifest. Env override for non-secrets only.

## Vault safety

- Vault IS checked: `OKF_VAULT_PATH` must NOT be inside the skill directory (rejected with exit 2).
- `.okf/` is written to the vault's `.gitignore` on first access.
- Skill NEVER runs `git init`/`git add`/`git commit`.

## Downloads / uploads

- All files are written into the configured vault directory.
- `doc ingest` reads local files; never writes outside the vault.
- No network calls in the core task (Confluence/web connectors are separate, later, modules).
