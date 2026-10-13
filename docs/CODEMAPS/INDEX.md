<!-- Generated: 2026-03-02 | Updated: 2026-10-13 | Files scanned: 33 | Token estimate: ~950 -->

# AI Knowledge Source Triage Bot — Codebase Overview

## What This Bot Does

1. **Receives** URLs shared in a Telegram group
2. **Fetches** content (tweets, articles, GitHub repos)
3. **Analyzes** with Claude (credibility → full analysis, or rejection summary for low credibility)
4. **Discovers** GitHub repos embedded in articles/tweets → analyzes each separately
5. **Creates** Notion pages for accepted sources (`/accept` overrides a rejection)
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
│   │   ├── handler.py            # Message handler, queue processor, /accept command
│   │   └── formatter.py          # Result formatting (single + multi-record)
│   ├── fetcher/
│   │   ├── twitter.py            # X.com tweets/articles (ScrapFly API)
│   │   ├── article.py            # Generic articles (httpx + BS4)
│   │   ├── github.py             # GitHub repos (REST API)
│   │   └── playwright.py         # Headless browser fallback
│   ├── analyzer/
│   │   ├── pipeline.py           # Analysis orchestration + discovery
│   │   ├── prompts.py            # All Claude system prompts (4 prompts) + TOPICS
│   │   ├── claude.py             # Model defaults, request options, response parsing
│   │   ├── extractor.py          # GitHub URL extraction from content
│   │   └── json_utils.py         # JSON parsing from Claude responses
│   └── notion/
│       ├── writer.py             # Notion DB + page creation
│       ├── references.py         # Cross-referencing logic
│       └── projects.py           # Project context cache
├── scripts/
│   └── backfill_references.py    # One-time cross-reference backfill
├── tests/                        # 82 tests
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
│  ├─ Phase 1 (fast model): credibility — score < 2 → Phase 3B
│  ├─ Phase 3A (analysis model): full analysis
│  ├─ Phase 3B (fast model): rejection summary
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
| Python files | 33 (incl. tests) |
| Total lines | ~4,000 |
| Test count | 82 |
| Claude prompts | 4 (credibility, analysis, rejection, cross-reference) |
| Claude models | `claude-haiku-5-5` (fast), `claude-sonnet-5-5` (analysis) — env-configurable |
| External APIs | 6 (Telegram, Claude, Notion, ScrapFly, GitHub, Playwright) |

---

## Recent Changes (2026-10-13)

- **Deploy hardening** (#17) — manual `workflow_dispatch` deploy works, deploy fails if the service isn't active after restart
- **anthropic SDK 1.13** (#16) — `output_config` passed as a typed param
- **Claude Haiku 5.5 / Sonnet 5.5** (#15) — models via `CLAUDE_FAST_MODEL` / `CLAUDE_ANALYSIS_MODEL`; new `claude.py` (thinking-aware response parsing, effort, refusal fallback)
- **Tutorials topic** (#14) — 7 topic categories
- **Phase 2 removed + `/accept` override** (#13) — only credibility < 2 or fetch failure rejects; `/accept` reply re-runs the pipeline

## Earlier Changes (2026-04-04)

- **F1: Cross-referencing** — "Related Sources" Notion Relation, semantic matching via Claude (fast model), backfill script
- **F2: GitHub repo discovery** — Extract GitHub URLs from articles/tweets, analyze each, cross-reference siblings
- **Extracted** `json_utils.py` from pipeline.py (break circular import)
- **New** `extractor.py`, `references.py`, `backfill_references.py`
- **Updated** formatter for multi-record replies, handler for list[AnalysisResult]
