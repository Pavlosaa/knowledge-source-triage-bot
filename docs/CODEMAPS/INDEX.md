<!-- Generated: 2026-03-02 | Updated: 2026-04-04 | Files scanned: 29 | Token estimate: ~900 -->

# AI Knowledge Source Triage Bot — Codebase Overview

## What This Bot Does

1. **Receives** URLs shared in a Telegram group
2. **Fetches** content (tweets, articles, GitHub repos)
3. **Analyzes** with Claude (4-phase pipeline: credibility → value → full analysis)
4. **Discovers** GitHub repos embedded in articles/tweets → analyzes each separately
5. **Creates** Notion pages for valuable sources
6. **Cross-references** related records via Notion Relations
7. **Replies** with formatted summary + Notion link(s)

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
│   │   ├── handler.py            # Message handler + queue processor
│   │   └── formatter.py          # Result formatting (single + multi-record)
│   ├── fetcher/
│   │   ├── twitter.py            # X.com tweets/articles (ScrapFly API)
│   │   ├── article.py            # Generic articles (httpx + BS4)
│   │   ├── github.py             # GitHub repos (REST API)
│   │   └── playwright.py         # Headless browser fallback
│   ├── analyzer/
│   │   ├── pipeline.py           # Analysis orchestration + discovery
│   │   ├── prompts.py            # All Claude system prompts (5 prompts)
│   │   ├── extractor.py          # GitHub URL extraction from content
│   │   └── json_utils.py         # JSON parsing from Claude responses
│   └── notion/
│       ├── writer.py             # Notion DB + page creation
│       ├── references.py         # Cross-referencing logic
│       └── projects.py           # Project context cache
├── scripts/
│   └── backfill_references.py    # One-time cross-reference backfill
├── tests/                        # 50 tests (47 pass, 3 skip)
├── main.py                       # Entry point
├── .github/workflows/            # CI (lint, typecheck, test, security) + deploy
└── docs/
    ├── CODEMAPS/                  # This directory
    └── plans/                    # Feature implementation plans
```

---

## Architecture at a Glance

```
Telegram User
    ↓ (shares URL)
Handler → Queue → run_pipeline_with_discovery(url)
├─ run_pipeline(url)
│  ├─ Detect + Fetch content
│  ├─ Phase 1 (Haiku): credibility
│  ├─ Phase 2 (Haiku): value
│  ├─ Phase 3A/B (Sonnet/Haiku): full analysis or rejection
│  ├─ Notion Writer: create page
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
| Python files | 29 |
| Total lines | ~3,200 |
| Test count | 50 (47 pass, 3 skip) |
| Claude prompts | 5 (credibility, value, analysis, rejection, cross-reference) |
| External APIs | 6 (Telegram, Claude, Notion, ScrapFly, GitHub, Playwright) |

---

## Recent Changes (2026-04-04)

- **F1: Cross-referencing** — "Related Sources" Notion Relation, semantic matching via Claude Haiku, backfill script
- **F2: GitHub repo discovery** — Extract GitHub URLs from articles/tweets, analyze each, cross-reference siblings
- **Extracted** `json_utils.py` from pipeline.py (break circular import)
- **New** `extractor.py`, `references.py`, `backfill_references.py`
- **Updated** formatter for multi-record replies, handler for list[AnalysisResult]
