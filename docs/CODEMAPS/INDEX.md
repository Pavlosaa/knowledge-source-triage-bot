<!-- Generated: 2026-03-02 | Updated: 2026-03-17 -->

# AI Knowledge Source Triage Bot — Codebase Overview

Quick navigation for understanding the bot architecture, data flow, dependencies, and implementation status.

---

## What This Bot Does

1. **Receives** URLs shared in a Telegram group
2. **Fetches** content (tweets, articles, GitHub repos)
3. **Analyzes** with Claude (4-phase pipeline: credibility → value → full analysis)
4. **Creates** Notion pages for valuable sources
5. **Replies** with formatted summary + Notion link

---

## Codemaps

### Architecture ([architecture.md](./architecture.md))
System-level overview: data flow diagram, module dependency graph, async patterns, configuration, logging, Notion schema, deployment notes.

**Best for:** Understanding how components fit together, request lifecycle, overall design.

### Backend Modules ([backend.md](./backend.md))
Code-level module breakdown: entry point, config, Telegram handler, fetchers, analyzer pipeline, Notion integration.

**Best for:** Finding specific module signatures, understanding code organization, error handling patterns.

### Data & Configuration ([data.md](./data.md))
Configuration validation, analysis dataclasses, Claude prompts (all 4 phases), Notion database schema, fetcher data structures, context caching.

**Best for:** Understanding data structures, prompt engineering, database design, lifecycle of an analysis request.

### External Dependencies ([dependencies.md](./dependencies.md))
Python packages, external service integrations (Telegram, Claude, Notion, X.com, GitHub, articles, Playwright), authentication, rate limits, risk assessment.

**Best for:** Setup/deployment, understanding service dependencies, troubleshooting API issues.

---

## Current Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| **Telegram Handler** | DONE | Receives messages, enqueues URLs, sends placeholder + reply |
| **Config** | DONE | Load + validate all env vars, fail-fast at startup |
| **Data Structures** | DONE | AnalysisResult, fetcher dataclasses, Config |
| **Claude Prompts** | DONE | All 4 system prompts defined (credibility, value, analysis, rejection) |
| **Telegram Formatter** | DONE | HTML formatting for valuable + rejected sources |
| **Notion Writer** | DONE | DB creation, record creation with properties + body blocks |
| **Project Context Cache** | DONE | Async-safe cache, 24h TTL, Notion page description fetching |
| **Fetcher (Twitter)** | DONE | ScrapFly HTTP API + tweet/article fetch (httpx + BS4) |
| **Fetcher (Article)** | DONE | httpx + BS4 with Playwright fallback |
| **Fetcher (GitHub)** | DONE | REST API: metadata + README |
| **Fetcher (Playwright)** | DONE | Headless Chromium for JS-rendered pages |
| **Analysis Pipeline** | DONE | 3-phase orchestration (Haiku×2 → Sonnet), retry, JSON extraction |
| **Tests (Twitter)** | DONE | 14 unit tests for twitter.py, 94% coverage |
| **CI/CD Pipeline** | DONE | GitHub Actions: lint, typecheck, test, security + auto-deploy |

**Bot is LIVE** on Oracle Cloud since 2026-03-07. GitHub, article, and X.com URLs work end-to-end via ScrapFly API.

---

## Directory Structure

```
knowledge-source-triage-bot/
├── bot/                          # Main application
│   ├── config.py                 # Config loading + validation
│   ├── telegram/
│   │   ├── handler.py            # Message handler + queue processor
│   │   └── formatter.py          # Result formatting for Telegram
│   ├── fetcher/
│   │   ├── twitter.py            # X.com tweets/articles (ScrapFly API)
│   │   ├── article.py            # Generic articles (httpx + BS4)
│   │   ├── github.py             # GitHub repos (REST API)
│   │   └── playwright.py         # Headless browser fallback
│   ├── analyzer/
│   │   ├── pipeline.py           # 3-phase analysis orchestration
│   │   └── prompts.py            # All Claude system prompts
│   └── notion/
│       ├── writer.py             # Notion page creation
│       └── projects.py           # Project context cache
├── tests/                         # pytest test suite
│   ├── __init__.py
│   ├── conftest.py               # Shared fixtures
│   └── test_twitter.py           # Twitter fetcher tests (14 tests, 94% coverage)
├── .github/workflows/             # CI/CD
│   ├── ci.yml                    # lint, typecheck, test, security
│   └── deploy.yml                # Auto-deploy to Oracle Cloud
├── main.py                        # Entry point
├── pyproject.toml                 # ruff, mypy, pytest config
├── requirements.txt               # Python dependencies (prod + dev)
├── .env.example                   # Env var template
├── docs/
│   ├── plans/
│   │   └── 2026-03-01-ai-knowledge-triage-design.md
│   └── CODEMAPS/
│       ├── INDEX.md              # This file
│       ├── architecture.md       # System overview
│       ├── backend.md            # Module breakdown
│       ├── data.md               # Data structures + prompts
│       └── dependencies.md       # External services
├── tasks/
│   ├── todo.md                   # Task backlog
│   └── lessons.md                # Lessons learned
└── systemd/
    └── triage-bot.service        # systemd unit file
```

---

## Key Files to Know

| File | Purpose | Status |
|------|---------|--------|
| main.py | Entry point, wiring, Telegram app setup | ✅ |
| bot/config.py | Load + validate env vars | ✅ |
| bot/telegram/handler.py | Message reception, URL extraction, queue | ✅ |
| bot/telegram/formatter.py | Result → Telegram HTML | ✅ |
| bot/analyzer/pipeline.py | 3-phase analysis orchestration | ✅ |
| bot/analyzer/prompts.py | All Claude system prompts | ✅ |
| bot/fetcher/twitter.py | X.com fetch (ScrapFly API) | ✅ |
| bot/fetcher/article.py | Generic article (httpx+BS4) | ✅ |
| bot/fetcher/github.py | GitHub repo (REST API) | ✅ |
| bot/fetcher/playwright.py | Headless browser fallback | ✅ |
| bot/notion/writer.py | Notion page creation | ✅ |
| bot/notion/projects.py | Project context cache | ✅ |
| pyproject.toml | ruff, mypy, pytest config | ✅ |
| .github/workflows/ci.yml | CI pipeline (lint, typecheck, test, security) | ✅ |
| .github/workflows/deploy.yml | Auto-deploy to Oracle Cloud | ✅ |
| tests/conftest.py | Shared test fixtures | ✅ |

---

## Quick Start (Development)

1. **Clone & setup:**
   ```bash
   cd ai-knowledge-source-triage
   python3.12 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Configure:**
   ```bash
   cp .env.example .env
   # Fill in secrets: Telegram, Claude, Notion, GitHub tokens, ScrapFly (optional)
   ```

3. **Run:**
   ```bash
   python main.py
   ```

4. **Test:**
   - Share a link in the configured Telegram group
   - Bot will reply with analysis (once pipeline is implemented)

---

## Architecture at a Glance

```
Telegram User
    ↓ (shares URL)
Handler (extract_urls) → Queue (asyncio.Queue)
    ↓
Pipeline Orchestrator
├─ Detect content type (x.com, github, article)
├─ Fetch content (fetcher/*)
├─ Phase 1 (Haiku): credibility check
├─ Phase 2 (Haiku): value assessment
├─ Phase 3A/B (Sonnet/Haiku): full analysis or rejection
└─ Notion Writer: create page (if valuable)
    ↓
Formatter → HTML message
    ↓
Telegram Reply
```

---

## Key Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **Async throughout** | Non-blocking I/O for multiple concurrent requests | More complex code |
| **Sequential queue processing** | Simpler rate limiting, easier debugging | One URL at a time (not parallel) |
| **Haiku (phase 1, 2, 3B) + Sonnet (phase 3A)** | Cost efficiency + best analysis quality | 3 Claude calls per URL |
| **Project context cache (24h TTL)** | Reduce Notion API calls, faster phase 3A | Stale context for 24h |
| **ScrapFly + Playwright fallback** | Residential proxy/rotation (optional), covers X.com + JS-heavy | Paid tier, free tier 1000 req/mo |
| **frozen Config dataclass** | Immutable config, fail-fast validation | Must create new instance to modify |

---

## Common Tasks

### Add a new content type fetcher
1. Create `bot/fetcher/newtype.py` with `async def fetch_*(url) → ContentType`
2. Add `@dataclass class ContentType` with fields: url, title, body, author
3. Update `bot/analyzer/pipeline.py` to detect and call new fetcher
4. Update formatter if new content type needs special handling

### Modify Claude prompts
1. Edit `bot/analyzer/prompts.py`
2. Update the `*_SYSTEM` constant
3. Update expected JSON schema in docstring
4. Test with `anthropic.Anthropic(...).messages.create(...)`

### Change Notion database schema
1. Edit `bot/notion/writer.py` → `_create_database()` properties
2. Restart bot (will use existing DB if found, only create if missing)
3. Add property colors to `_TOPIC_COLORS` or `_CONTENT_TYPE_COLORS` if select option

### Deploy to systemd
1. Fill `.env` with production secrets
2. Copy `systemd/triage-bot.service` to `/etc/systemd/system/`
3. `sudo systemctl daemon-reload`
4. `sudo systemctl enable triage-bot`
5. `sudo systemctl start triage-bot`

---

## Testing & CI

**CI Pipeline (GitHub Actions):** lint (ruff) → typecheck (mypy) → test (pytest) → security (pip-audit + TruffleHog)

**Test infrastructure:** `tests/conftest.py` with shared fixtures (mock env vars).

**Remaining test work:**
- Unit tests for: fetchers (mocked HTTP), pipeline (mocked Claude responses)
- Integration tests for: Notion writer, project context cache
- E2E tests: full pipeline with mock Claude API

---

## Support & Troubleshooting

**Log files:**
- `logs/bot.log` — all events (DEBUG+)
- `logs/errors.log` — errors only
- `journalctl -u triage-bot -f` — systemd logs

**Common issues:**
| Issue | Cause | Fix |
|-------|-------|-----|
| "Missing required env var" | Config incomplete | Fill `.env` with all vars from `.env.example` |
| Telegram not responding | Bot token invalid or group ID wrong | Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_GROUP_ID` |
| Notion page not created | API key invalid or parent page ID wrong | Verify `NOTION_API_KEY` and page IDs in `.env` |
| X.com tweet not fetching | ScrapFly API key missing or rate limited | Check `SCRAPFLY_API_KEY` env var; free tier 1000 req/mo |
| Claude API error | Invalid key or rate limited | Check `ANTHROPIC_API_KEY`; wait before retrying |

---

## Documentation Freshness

- **Generated:** 2026-03-02, **Updated:** 2026-03-11
- **Architecture matches:** Yes (verified against live deployment)
- **All file paths verified:** Yes
- **Next update:** When integration tests and remaining fetcher tests are implemented

---

## Related Documents

- **Design Doc:** `/docs/plans/2026-03-01-ai-knowledge-triage-design.md`
- **Task Backlog:** `/tasks/todo.md`
- **Lessons Learned:** `/tasks/lessons.md`
- **Setup Template:** `/.env.example`
