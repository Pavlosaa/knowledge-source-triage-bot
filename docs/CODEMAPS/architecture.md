<!-- Generated: 2026-03-02 | Files scanned: 17 | Token estimate: ~650 -->

# Architecture Codemap

**Project:** AI Knowledge Source Triage Bot
**Type:** Python 3.12 async application
**Entry Point:** `/bot/main.py`
**Updated:** 2026-03-11

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ Telegram User Group                                             │
│ (User shares/forwards links to group)                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │ TEXT + URL
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ bot/telegram/handler.py                                         │
│ ├─ handle(update, context)                                      │
│ │  ├─ extract_urls(text) → list[str]                            │
│ │  ├─ message.reply_text("⏳ Analyzuji...")                      │
│ │  └─ queue.put((message, placeholder, urls))                   │
│ └─ process_queue(queue, pipeline_fn, format_fn)                 │
│    └─ run forever: dequeue → pipeline_fn → format_fn → reply    │
└──────────────────────┬──────────────────────────────────────────┘
                       │ asyncio.Queue
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ bot/analyzer/pipeline.py                                        │
│ ├─ run_pipeline(url) → AnalysisResult                           │
│ │  ├─ Fetcher (content type detection)                          │
│ │  ├─ Phase 1: Credibility (Haiku)                              │
│ │  ├─ Phase 2: Value Check (Haiku)                              │
│ │  ├─ Phase 3: Full Analysis (Sonnet) or Rejection (Haiku)      │
│ │  └─ Notion Writer (if valuable)                               │
│ └─ @dataclass AnalysisResult                                    │
│    ├─ url, has_value, title, core_summary                       │
│    ├─ key_principles, use_cases, discovery_score, tags          │
│    ├─ project_recommendations, notion_url                       │
│    ├─ brief_summary, rejection_reason (if rejected)             │
│    ├─ topic, credibility_score                                  │
│    └─ credibility_reason                                        │
└──────────┬───────────────────────┬────────────────────┬─────────┘
           │                       │                    │
    FETCH  │              ANALYZE  │         WRITE      │
           ▼                       ▼                    ▼
    ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
    │ bot/fetcher/    │   │ bot/analyzer/   │   │ bot/notion/     │
    ├─ twitter.py    │   ├─ pipeline.py    │   ├─ writer.py      │
    ├─ article.py    │   ├─ prompts.py     │   └─ projects.py    │
    ├─ github.py     │   └─ [Claude API]   │   └─ [Notion API]   │
    └─ playwright.py │                     │                     │
                     │                     │                     │
                     └─────────────────────┴─────────────────────┘
                               │
                               ▼
                     ┌──────────────────┐
                     │ Telegram Reply   │
                     │ formatter.py     │
                     │ ✅ or ❌ + details│
                     └──────────────────┘
```

---

## Data Flow: Full Request Lifecycle

```
1. USER shares URL in Telegram group
   └─ "Check this: https://x.com/user/status/123"

2. HANDLER receives message
   ├─ Extracts URL via regex
   ├─ Sends placeholder: "⏳ Analyzuji..."
   └─ Enqueues (message, placeholder, [url])

3. QUEUE PROCESSOR (background, sequential)
   └─ Dequeues first message-batch

4. PIPELINE orchestrates analysis
   ├─ DETECT content type (x.com, github, article, etc.)
   │
   ├─ FETCH content
   │  ├─ x.com/*/status/* → twikit.get_tweet()
   │  │  └─ [TweetContent: author, text, verified, followers]
   │  │
   │  ├─ x.com/i/article/* → Playwright fallback
   │  │  └─ [ArticleContent: title, body]
   │  │
   │  ├─ github.com/*/*  → GitHub REST API
   │  │  └─ [RepoContent: description, stars, language, README]
   │  │
   │  └─ other URL → httpx + BS4
   │     └─ [ArticleContent: title, body]
   │
   ├─ PHASE 1: Credibility (Haiku)
   │  Input:  author metadata + text snippet
   │  Output: { credibility_score: 1-5, reason: str }
   │
   ├─ PHASE 2: Value Check (Haiku)
   │  Input:  full content
   │  Output: { has_value: bool, rejection_reason?: str }
   │
   ├─ PHASE 3A: Full Analysis (Sonnet) if has_value=true
   │  Input:  full content + project_context (from cache)
   │  Output: { title, summary, principles, use_cases, score,
   │            tags, project_recs, topic }
   │
   └─ PHASE 3B: Rejection Summary (Haiku) if has_value=false
      Input:  content
      Output: { brief_summary, rejection_reason }

5. NOTION WRITER (if has_value=true only)
   ├─ Load or create "AI Sources" database
   ├─ Create record with properties:
   │  - Title, Topic, Discovery Score, Source URL
   │  - Content Type, Author, Tags, Date Added, Relevant Projects
   ├─ Build page body from analysis
   └─ Return notion_url

6. FORMAT RESULT for Telegram
   ├─ If valuable:
   │  ✅ Hodnotný zdroj | ★★★★☆ (4/5)
   │  📌 Obsah: ...
   │  🔑 Klíčové body: ...
   │  🎯 Relevantní pro: Project A, B
   │  📖 Notion: [link]
   │
   └─ If rejected:
      ❌ Nízká hodnota
      💭 Shrnutí: ...
      🚫 Proč: ...

7. SEND REPLY
   ├─ Delete placeholder message
   └─ Post final reply with HTML formatting

8. QUEUE COMPLETE
   └─ task_done() → ready for next message
```

---

## Module Dependency Graph

```
main.py
├─ bot.config::load_config() → Config
├─ bot.telegram.handler::MessageHandler(queue)
│  └─ bot.telegram.handler::process_queue(queue, run_pipeline, format_result)
├─ bot.analyzer.pipeline::run_pipeline(url) → AnalysisResult
│  ├─ bot.fetcher.twitter (if x.com)
│  ├─ bot.fetcher.github (if github.com)
│  ├─ bot.fetcher.article (if article)
│  ├─ bot.fetcher.playwright (fallback)
│  ├─ [anthropic API] for Phase 1, 2, 3
│  ├─ bot.analyzer.prompts (system prompts)
│  ├─ bot.notion.projects::ProjectsCache.get_context()
│  └─ bot.notion.writer::NotionWriter.create_source_page()
└─ bot.telegram.formatter::format_result(result, url) → str

External APIs:
├─ Telegram (python-telegram-bot v21)
├─ Claude (anthropic v0.49)
├─ Notion (notion-client v2.3)
├─ X.com / twikit (v2.3.3)
├─ GitHub REST API (httpx v0.28.1)
├─ Playwright (v1.50.0)
└─ BeautifulSoup4 (v4.13.3)
```

---

## Key Async Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| `asyncio.Queue` | main.py, handler.py | Async message buffer (producer: handler, consumer: queue processor) |
| `asyncio.create_task()` | main.py | Background queue processing task |
| `asyncio.Lock` | projects.py | Protect ProjectsCache refresh |
| `async/await` | All modules | Non-blocking I/O for Telegram, Notion, Claude, HTTP |

---

## Configuration & Secrets

**File:** `bot/config.py`
**Class:** `Config` (frozen dataclass)

Required env vars (fail-fast at startup):
- `TELEGRAM_BOT_TOKEN` — BotFather token
- `TELEGRAM_GROUP_ID` — Integer group ID
- `TWITTER_USERNAME`, `TWITTER_PASSWORD`, `TWITTER_EMAIL` — twikit login
- `ANTHROPIC_API_KEY` — Claude API key
- `NOTION_API_KEY` — Notion integration token
- `NOTION_RND_PAGE_ID` — Parent page ID (ICT Project R&D Resources)
- `NOTION_PROJECTS_PAGE_ID` — Projects page ID (for context cache)

Optional:
- `GITHUB_TOKEN` — For higher API rate limit (default: None → 60 req/h)

All loaded at startup via `load_config()` → raises SystemExit if missing.

---

## Logging

**Setup:** `main.py` lines 14-18

```python
logger.remove()  # clear defaults
logger.add(sys.stderr, level="INFO")
logger.add("logs/bot.log", rotation="10 MB", retention="7 days", level="DEBUG")
logger.add("logs/errors.log", rotation="10 MB", retention="7 days", level="ERROR")
```

**Scope:** All modules use `from loguru import logger`

---

## Notion Database Schema

**Name:** "AI Sources"
**Parent:** ICT Project R&D Resources page

**Properties:**
| Property | Type | Values |
|----------|------|--------|
| Title | title | *string* |
| Topic | select | AI Tools & Libraries, Educational Content, Tips & Tricks, Best Practices, News & Updates, Interesting Findings |
| Discovery Score | number | 1–5 |
| Source URL | url | *URL* |
| Content Type | select | Tweet, X Article, GitHub, Article |
| Author | rich_text | *string* |
| Tags | multi_select | *open tags* |
| Date Added | date | *YYYY-MM-DD* |
| Relevant Projects | multi_select | *user's projects* |

**Page Body:**
- Heading 2: 📌 Core Summary
- Paragraph: core_summary text
- Heading 2: 🔑 Key Principles
- Bullet list: key_principles
- Heading 2: 💡 Use Cases
- Bullet list: use_cases
- Heading 2: 🎯 Relevance for Projects
- Toggles: project_name → how_to_apply
- Heading 2: 🔗 Source
- Bookmark: source_url

---

## Deployment

**Service:** `/systemd/triage-bot.service`
**Host:** Oracle Cloud Free Forever — VM.Standard.E5.Flex (AMD x86), 1 OCPU, 12GB RAM
**OS:** Ubuntu
**Python:** 3.12
**CI/CD:** GitHub Actions (lint, typecheck, test, security) → auto-deploy via SSH

Systemd unit manages:
- Auto-restart on failure
- Log rotation via journalctl
- Environment file sourcing (.env)
