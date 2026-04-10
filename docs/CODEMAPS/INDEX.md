<!-- Generated: 2026-03-02 | Updated: 2026-04-10 | Files scanned: 31 | Token estimate: ~900 -->

# AI Knowledge Source Triage Bot — Codebase Overview

## What This Bot Does

1. **Receives** URLs shared in a Telegram group
2. **Fetches** content (tweets, articles, GitHub repos)
3. **Analyzes** with Claude (2-phase pipeline: credibility → full analysis)
4. **Discovers** GitHub repos embedded in articles/tweets → analyzes each separately
5. **Creates** Notion pages for sources (nearly all accepted — only spam/unreachable rejected)
6. **Cross-references** related records via Notion Relations
7. **Replies** with formatted summary + Notion link(s)
8. **Override:** User can reply `/accept` to any rejection to force reprocessing

---

## Codemaps

| File | Best for |
|------|----------|
| [architecture.md](./architecture.md) | System overview, data flow, module dependencies, deployment |
| [backend.md](./backend.md) | Module signatures, code organization, error handling |
| [data.md](./data.md) | Data structures, Claude prompts, Notion schema |
| [dependencies.md](./dependencies.md) | External services, packages, rate limits |

---

## Directory Structure

```
knowledge-source-triage-bot/
├── bot/
│   ├── config.py                 # Config loading + validation
│   ├── telegram/
│   │   ├── handler.py            # Message handler + /accept command + queue
│   │   └── formatter.py          # Result formatting (single + multi-record)
│   ├── fetcher/
│   │   ├── twitter.py            # X.com tweets/articles (ScrapFly API)
│   │   ├── article.py            # Generic articles (httpx + BS4)
│   │   ├── github.py             # GitHub repos (REST API)
│   │   └── playwright.py         # Headless browser fallback
│   ├── analyzer/
│   │   ├── pipeline.py           # Analysis orchestration + discovery + override
│   │   ├── prompts.py            # All Claude system prompts (4 prompts)
│   │   ├── extractor.py          # GitHub URL extraction from content
│   │   └── json_utils.py         # JSON parsing from Claude responses
│   └── notion/
│       ├── writer.py             # Notion DB + page creation (+ Manual Override tag)
│       ├── references.py         # Cross-referencing logic
│       └── projects.py           # Project context cache
├── scripts/
│   └── backfill_references.py    # One-time cross-reference backfill
├── tests/                        # 74 tests (74 pass, 3 skip)
├── main.py                       # Entry point
├── .github/workflows/            # CI (lint, typecheck, test, security) + deploy
└── docs/
    ├── CODEMAPS/                  # This directory
    ├── brainstorms/               # Requirements documents
    ├── ideation/                  # Ideation artifacts
    └── plans/                     # Feature implementation plans
```

---

## Architecture at a Glance

```
Telegram User
    ↓ (shares URL)                  ↓ (replies /accept)
Handler → Queue                  accept_command()
    ↓                               ↓
run_pipeline_with_discovery(url, skip_credibility?, is_override?)
├─ run_pipeline(url)
│  ├─ Detect + Fetch content
│  ├─ Phase 1 (Haiku): credibility — reject if score < 2
│  │  └─ Phase 3B: rejection summary (on reject only)
│  ├─ Phase 3A (Sonnet): full analysis → Notion record
│  └─ Cross-reference: find related sources
├─ extract_github_urls() from fetched content
├─ For each discovered repo: run_pipeline(repo_url, source_context=...)
└─ Batch cross-reference all sibling pages
    ↓
format_results() → Telegram HTML Reply
```

---

## Key Stats

| Metric | Value |
|--------|-------|
| Python files | 31 |
| Total lines | ~3,700 |
| Test count | 74 (74 pass, 3 skip) |
| Claude prompts | 4 (credibility, analysis, rejection, cross-reference) |
| External APIs | 6 (Telegram, Claude, Notion, ScrapFly, GitHub, Playwright) |

---

## Recent Changes (2026-04-10)

- **Phase 2 removed** — VALUE_ASSESSMENT gate deleted. Bot no longer rejects links as "low value". Only credibility < 2 and fetch failures cause rejection.
- **/accept command** — Reply-based override for rejected links. Credibility rejections skip Phase 1; fetch failures retry.
- **"Manual Override" tag** — Overridden Notion records tagged for audit.
- **Phase 3B wired to Phase 1** — Credibility rejections now get brief_summary context.
- **Rejection label** — "Nízká hodnota" → "Nízká věrohodnost".
