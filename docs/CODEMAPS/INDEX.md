<!-- Generated: 2026-03-02 -->

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
| **Fetcher (Twitter)** | TODO | twikit session + tweet/article fetch |
| **Fetcher (Article)** | TODO | httpx + BS4 with Playwright fallback |
| **Fetcher (GitHub)** | TODO | REST API calls to get metadata + README |
| **Fetcher (Playwright)** | TODO | Headless Chromium for JS-rendered pages |
| **Analysis Pipeline** | TODO | Orchestrate 4 phases, call Claude, create Notion pages |

**Current blocker:** Pipeline orchestration not yet implemented. Once fetchers and pipeline are done, bot is ready to deploy.

---

## Directory Structure

```
ai-knowledge-source-triage/
├── bot/                          # Main application
│   ├── config.py                 # Config loading + validation
│   ├── telegram/
│   │   ├── handler.py            # Message handler + queue processor
│   │   └── formatter.py          # Result formatting for Telegram
│   ├── fetcher/
│   │   ├── twitter.py            # X.com tweets/articles (twikit)
│   │   ├── article.py            # Generic articles (httpx + BS4)
│   │   ├── github.py             # GitHub repos (REST API)
│   │   └── playwright.py         # Headless browser fallback
│   ├── analyzer/
│   │   ├── pipeline.py           # 4-phase analysis orchestration
│   │   └── prompts.py            # All Claude system prompts
│   └── notion/
│       ├── writer.py             # Notion page creation
│       └── projects.py           # Project context cache
├── main.py                        # Entry point
├── requirements.txt               # Python dependencies
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
│   ├── todo.md                   # Task backlog (DEV BREAKPOINT)
│   └── lessons.md                # Lessons learned (empty)
└── systemd/
    └── triage-bot.service        # systemd unit file
```

---

## Key Files to Know

| File | Purpose | Lines | Status |
|------|---------|-------|--------|
| main.py | Entry point, wiring, Telegram app setup | 69 | ✅ |
| bot/config.py | Load + validate env vars | 82 | ✅ |
| bot/telegram/handler.py | Message reception, URL extraction, queue | 98 | ✅ |
| bot/telegram/formatter.py | Result → Telegram HTML | 80 | ✅ |
| bot/analyzer/pipeline.py | 4-phase analysis (NOT YET) | 46 | ❌ |
| bot/analyzer/prompts.py | All Claude system prompts | 67 | ✅ |
| bot/fetcher/twitter.py | X.com fetch (NOT YET) | 58 | ❌ |
| bot/fetcher/article.py | Generic article fetch (NOT YET) | 22 | ❌ |
| bot/fetcher/github.py | GitHub repo fetch (NOT YET) | 34 | ❌ |
| bot/fetcher/playwright.py | Headless browser (NOT YET) | 22 | ❌ |
| bot/notion/writer.py | Notion page creation | 225 | ✅ |
| bot/notion/projects.py | Project context cache | 88 | ✅ |

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
   # Fill in secrets: Telegram, X.com, Claude, Notion, GitHub tokens
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
| **twikit + Playwright fallback** | Free (no API key), covers both simple + JS-heavy | Unofficial X.com client |
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

## Testing Strategy (TODO)

- Unit tests for: config loading, URL extraction, formatter
- Integration tests for: Notion writer, project context cache
- E2E tests (post-implementation): full pipeline with mock Claude API

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
| X.com tweet not fetching | X.com creds wrong or IP blocked | Check `TWITTER_*` env vars; retry or use VPN |
| Claude API error | Invalid key or rate limited | Check `ANTHROPIC_API_KEY`; wait before retrying |

---

## Documentation Freshness

- **Generated:** 2026-03-02
- **Source files scanned:** 17 (all Python modules)
- **Architecture matches:** Yes (verified against code)
- **All file paths verified:** Yes
- **Next update:** When major feature complete (fetchers, pipeline)

---

## Related Documents

- **Design Doc:** `/docs/plans/2026-03-01-ai-knowledge-triage-design.md`
- **Task Backlog:** `/tasks/todo.md`
- **Lessons Learned:** `/tasks/lessons.md`
- **Setup Template:** `/.env.example`
