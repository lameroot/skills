# Open Knowledge Format (OKF) v0.1 at a glance

OKF is a universal markdown + YAML frontmatter format for knowledge bundles, browsable in Obsidian, diffable in git, agent-friendly without SDKs.

## Bundle layout

```
vault/
├── index.md          # progressive disclosure (no frontmatter except root okf_version)
├── log.md            # ISO 8601 date sections, newest first
├── note/             # concept directory (source: note)
│   └── concept.md
└── doc/              # concept directory (source: doc)
    └── another.md
```

## Concept document

```markdown
---
type: Note              # REQUIRED, non-empty
title: My Note
description: A summary
resource: file:///path  # optional
tags: [tag1, tag2]      # optional
timestamp: 2026-07-18T00:00:00Z
source: note            # producer key: which connector
source_id: ...          # stable content-derived id
content_hash: sha256... # for incremental indexing
okf_version: "0.1"
---

Body in standard markdown.
```

## Conformance (SPEC §9)

- Every non-reserved `.md` must have parseable YAML frontmatter.
- `type` field must be non-empty.
- `index.md` and `log.md` are reserved (exempt from concept rules).
- Consumers MUST NOT reject on unknown types/fields/broken links.

## Cross-links

Bundle-relative links: `[concept](/path/to/concept.md)` — recommended.

## Reserved filenames

| Name | Purpose |
|------|---------|
| `index.md` | Directory listing |
| `log.md` | Update history |
