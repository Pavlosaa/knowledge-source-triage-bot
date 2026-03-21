<!-- Generated: 2026-03-02 | Files scanned: 18 | Token estimate: ~750 -->

# Backend Module Codemap

**Files:** 18 Python modules | **Entry:** main.py | **Updated:** 2026-03-20

---

## Layer 1: Entry Point & Config

### main.py
```python
async def main() → None
  ├─ load_config() → Config
  ├─ ApplicationBuilder().token(bot_token).build() → Application
  ├─ app.add_handler(TGMessageHandler(filters, handler.handle))
  ├─ asyncio.create_task(process_queue(...))
  └─ app.updater.start_polling()

Imports:
├─ bot.config::load_config
├─ bot.telegram.handler::{MessageHandler, process_queue}
├─ bot.telegram.formatter::format_result
├─ bot.analyzer.pipeline::run_pipeline
└─ telegram.ext::{ApplicationBuilder, MessageHandler}
```

### bot/config.py
```python
@dataclass(frozen=True)
class Config:
  telegram_bot_token: str
  telegram_group_id: int
  scrapfly_api_key: str | None
  anthropic_api_key: str
  notion_api_key: str
  notion_rnd_page_id: str
  notion_projects_page_id: str
  github_token: str | None

load_config() → Config
  └─ Validate all required env vars, exit if missing
```

---

## Layer 2: Telegram Integration

### bot/telegram/handler.py

**Functions:**
```python
extract_urls(text: str) → list[str]
  └─ Regex match: r"https?://[^\s]+"

class MessageHandler:
  __init__(queue: asyncio.Queue) → None

  async handle(update: Update, context: ContextTypes.DEFAULT_TYPE) → None
    ├─ Extract message from update
    ├─ Call extract_urls(message.text)
    ├─ Reply placeholder: "⏳ Analyzuji..."
    └─ await queue.put((message, placeholder, urls))

async process_queue(queue, pipeline_fn, format_fn) → None
  └─ while True:
    ├─ message, placeholder, urls = await queue.get()
    ├─ url = urls[0]  (first URL only, for now)
    ├─ result = await pipeline_fn(url)
    ├─ reply_text = format_fn(result, url)
    ├─ await placeholder.delete()
    ├─ await message.reply_text(reply_text)
    └─ queue.task_done()
```

**Constants:**
- `_URL_RE` — compiled regex for URL extraction

**Error Handling:**
- Try/except around pipeline (log exception, user-friendly error message)
- Try/except around reply send (log if fails, don't retry)

### bot/telegram/formatter.py

**Functions:**
```python
format_result(result: AnalysisResult, original_url: str) → str
  └─ Dispatch to _format_valuable() or _format_rejected()

_format_valuable(result, original_url) → str
  ├─ Build HTML message with:
  │  ├─ 🔗 Original source link
  │  ├─ ✅ Hodnotný zdroj | ★★★★☆ (score/5)
  │  ├─ 📌 Obsah: core_summary
  │  ├─ 🔑 Klíčové body: key_principles bullets
  │  ├─ 💡 Use cases: use_cases bullets
  │  ├─ 🎯 Relevantní pro: project_names (high/medium relevance only)
  │  └─ 📖 Notion link (or ⚠️ if failed)
  └─ Return joined string

_format_rejected(result, original_url) → str
  ├─ 🔗 Original source link
  ├─ if fetch_failed:
  │  ├─ ⚠️ Zdroj nedostupný
  │  └─ 🚫 Důvod: rejection_reason
  └─ else:
     ├─ ❌ Nízká hodnota
     ├─ 💭 Shrnutí: brief_summary
     └─ 🚫 Proč: rejection_reason

_stars(score: int) → str
  └─ _SCORE_STARS: {1: "★☆☆☆☆", 2: "★★☆☆☆", ..., 5: "★★★★★"}
```

**Constants:**
- `_SCORE_STARS` — 1–5 star emoji maps

---

## Layer 3: Content Fetching

### bot/fetcher/twitter.py
```python
@dataclass
class TweetContent:
  tweet_id: str
  author_name: str
  author_username: str
  text: str
  follower_count: int | None = None   # None = not available from HTML
  is_verified: bool | None = None     # None = not available from HTML
  embedded_urls: list[str]

@dataclass
class ArticleContent:
  url: str
  title: str | None
  author_name: str | None
  body: str

detect_content_type(url: str) → str
  └─ regex match → "tweet" | "article" | "unknown"

async fetch_tweet(tweet_id: str, scrapfly_api_key: str | None) → TweetContent
  └─ ScrapFly HTTP API call (free tier w/o key) + BS4 parse

async fetch_article(url: str, scrapfly_api_key: str | None) → ArticleContent
  └─ ScrapFly HTTP API call (free tier w/o key) + BS4 parse
```

**Regex patterns:**
- `_TWEET_URL_RE` — `r"x\.com/(\w+)/status/(\d+)"`
- `_ARTICLE_URL_RE` — `r"x\.com/i/article/"`

### bot/fetcher/article.py
```python
@dataclass
class ArticleContent:
  url: str
  title: str | None
  body: str

async fetch_article(url: str) → ArticleContent
  └─ TODO: httpx + BS4 with Playwright fallback
```

### bot/fetcher/github.py
```python
@dataclass
class RepoContent:
  owner: str
  repo: str
  description: str | None
  stars: int
  language: str | None
  readme: str | None

extract_repo_coords(url: str) → tuple[str, str] | None
  └─ regex match on github.com/([^/]+)/([^/?#]+)

async fetch_repo(owner: str, repo: str, token: str | None = None) → RepoContent
  └─ TODO: httpx calls to api.github.com
```

**Regex:**
- `_GITHUB_URL_RE` — `r"github\.com/([^/]+)/([^/?#]+)"`

### bot/fetcher/playwright.py
```python
@dataclass
class PageContent:
  url: str
  title: str | None
  body: str

async fetch_with_playwright(url: str, timeout_ms: int = 30_000) → PageContent
  └─ TODO: Playwright Chromium headless fetch + text extraction
```

---

## Layer 4: Analysis Pipeline

### bot/analyzer/pipeline.py

```python
@dataclass
class AnalysisResult:
  url: str
  has_value: bool

  # Valuable source fields
  title: str | None = None
  core_summary: str | None = None
  key_principles: list[str] = field(default_factory=list)
  use_cases: list[str] = field(default_factory=list)
  discovery_score: int | None = None
  tags: list[str] = field(default_factory=list)
  project_recommendations: list[dict] = field(default_factory=list)
  notion_url: str | None = None

  # Rejected source fields
  brief_summary: str | None = None
  rejection_reason: str | None = None

  # Common fields
  topic: str | None = None
  credibility_score: int | None = None
  credibility_reason: str | None = None

  # Fetch failure
  fetch_failed: bool = False          # True when fetcher failed completely

async run_pipeline(url, config, writer, projects) → AnalysisResult
  ├─ Dedup check (find_existing)
  ├─ Fetch content (_fetch dispatcher)
  ├─ Phase 1: Credibility (Haiku, max 150 tokens)
  ├─ Phase 2: Value Check (Haiku, max 150 tokens)
  ├─ Phase 3A: Full Analysis (Sonnet, max 2000 tokens) if has_value
  ├─ Phase 3B: Rejection Summary (Haiku, max 200 tokens) if !has_value
  └─ Notion Writer (if has_value)
```

**Flow:**
1. Detect content type (x.com, github, article)
2. Call appropriate fetcher
3. Phase 1: Claude Haiku credibility check
4. Phase 2: Claude Haiku value assessment
5. If has_value:
   - Phase 3A: Claude Sonnet full analysis
   - Notion Writer creates page
   - Return AnalysisResult with notion_url
6. Else:
   - Phase 3B: Claude Haiku rejection summary
   - Return AnalysisResult with rejection_reason

### bot/analyzer/prompts.py

**Constants (system prompts):**
```python
TOPICS: list[str]
  └─ ["AI Tools & Libraries", "Educational Content", "Tips & Tricks",
      "Best Practices", "News & Updates", "Interesting Findings"]

CREDIBILITY_SYSTEM: str
  └─ JSON schema: { credibility_score: 1–5, credibility_reason: str }

VALUE_ASSESSMENT_SYSTEM: str
  └─ JSON schema: { has_value: bool, value_score: 1–5, rejection_reason?: str }

FULL_ANALYSIS_SYSTEM: str
  └─ JSON schema: {
       title, topic, core_summary, key_principles, use_cases,
       discovery_score, tags, project_recommendations
     }

REJECTION_SUMMARY_SYSTEM: str
  └─ JSON schema: { brief_summary?: str, rejection_reason: str }
```

---

## Layer 5: Notion Integration

### bot/notion/writer.py

```python
DB_NAME = "AI Sources"

_TOPIC_COLORS: dict[str, str]
  └─ Maps topic names to Notion colors (blue, green, yellow, purple, red, orange)

_CONTENT_TYPE_COLORS: dict[str, str]
  └─ Maps content types to Notion colors

class NotionWriter:
  __init__(notion_api_key: str, rnd_page_id: str) → None
    ├─ self._client = AsyncClient(auth=notion_api_key)
    ├─ self._parent_page_id = rnd_page_id
    └─ self._database_id = None

  async create_source_page(result: AnalysisResult, source_url: str) → str
    ├─ db_id = await self._get_or_create_database()
    ├─ page = await self._create_record(db_id, result, source_url)
    └─ return page["url"]

  async _get_or_create_database() → str
    ├─ if self._database_id: return it
    ├─ db_id = await self._find_database()
    ├─ if not found: db_id = await self._create_database()
    └─ cache and return

  async _find_database() → str | None
    └─ Search Notion for "AI Sources" under parent page

  async _create_database() → str
    └─ Create "AI Sources" database with properties:
       Title, Topic, Discovery Score, Source URL, Content Type,
       Author, Tags, Date Added, Relevant Projects

  async _create_record(db_id, result, source_url) → dict
    ├─ Filter project_recommendations for high/medium relevance
    ├─ Build properties dict
    ├─ Build page body blocks
    └─ client.pages.create(...)

  _build_body(result, source_url) → list[dict]
    ├─ Heading: "📌 Core Summary" + paragraph
    ├─ Heading: "🔑 Key Principles" + bullets
    ├─ Heading: "💡 Use Cases" + bullets
    ├─ Heading: "🎯 Relevance for Projects" + toggles
    ├─ Heading: "🔗 Source" + bookmark
    └─ Return block list

  [Helper methods for block construction]
  _rich_text(content: str) → list[dict]
  _heading2(text: str) → dict
  _paragraph(text: str) → dict
  _bullet(text: str) → dict
  _toggle(text: str, children: list[dict]) → dict
  _bookmark(url: str) → dict
```

### bot/notion/projects.py

```python
class ProjectsCache:
  """In-memory cache of project descriptions. 24-hour refresh TTL."""

  TTL_SECONDS = 86_400

  __init__(notion_api_key: str, projects_page_id: str) → None
    ├─ self._client = AsyncClient(...)
    ├─ self._page_id = projects_page_id
    ├─ self._context = ""
    ├─ self._last_loaded = 0.0
    └─ self._lock = asyncio.Lock()

  async get_context() → str
    ├─ Acquire lock
    ├─ If stale (> 24h) or empty: await self._refresh()
    └─ Return self._context

  async _refresh() → None
    ├─ Fetch blocks from projects page
    ├─ Extract projects via _extract_projects()
    ├─ Build context string
    ├─ Update _last_loaded
    └─ Log count loaded

  async _extract_projects(blocks: list[dict]) → list[dict]
    └─ Filter child_page blocks, fetch description for each

  async _fetch_page_description(page_id: str) → str
    └─ Fetch first text block from page (capped 300 chars)

  _extract_text_from_block(block: dict) → str
    └─ Extract plain_text from paragraph/heading/callout blocks

  _build_context_string(projects: list[dict]) → str
    └─ Format: "User's existing projects:\n- Name: Description\n..."
```

---

## Module Imports Summary

| Module | Key Imports | Purpose |
|--------|-------------|---------|
| main.py | asyncio, loguru, telegram.ext, bot.* | Wiring + startup |
| config.py | os, dataclasses, dotenv, loguru | Env var validation |
| telegram/handler.py | asyncio, re, telegram, loguru | Message reception + queue |
| telegram/formatter.py | TYPE_CHECKING, bot.analyzer.pipeline | Result formatting |
| fetcher/twitter.py | dataclasses, re, httpx, bs4, loguru | Tweet/article types + ScrapFly API |
| fetcher/article.py | dataclasses | Article type |
| fetcher/github.py | dataclasses, re | Repo type + regex |
| fetcher/playwright.py | dataclasses | Page content type |
| analyzer/pipeline.py | dataclasses, field | AnalysisResult type |
| analyzer/prompts.py | *none (constants)* | Prompt strings |
| notion/writer.py | dataclasses, datetime, loguru, notion_client | Notion CRUD |
| notion/projects.py | asyncio, time, loguru, notion_client | Notion caching |

---

## External Service Integration Points

| Service | Module | Method | Auth | Rate Limit |
|---------|--------|--------|------|-----------|
| **Telegram** | handler, main | python-telegram-bot.ext | BOT_TOKEN | Unlimited |
| **Claude** | pipeline (future) | anthropic SDK | ANTHROPIC_API_KEY | Per-model |
| **Notion** | writer, projects | notion_client (async) | NOTION_API_KEY | 3 req/sec |
| **X.com** | fetcher/twitter | ScrapFly API (httpx) | optional scrapfly_api_key | Free tier 1000 req/mo |
| **GitHub** | fetcher/github (future) | REST API (httpx) | GITHUB_TOKEN (optional) | 60 req/h (60–5000 with token) |
| **Playwright** | fetcher/playwright (future) | Chromium headless | none | N/A (local) |

---

## Error Handling Patterns

| Location | Pattern | Recovery |
|----------|---------|----------|
| process_queue | Try/except around pipeline_fn | Log exception, send user error message |
| process_queue | Try/except around reply send | Log error, continue queue |
| NotionWriter._find_database | Try/except search | Log warning, return None (triggers creation) |
| NotionWriter._refresh | Try/except API call | Log error, keep stale context |
| load_config | Missing env var → SystemExit | Fail at startup (no silent failures) |

---

## Code Quality Notes

- **Frozen dataclasses** for immutable Config
- **TYPE_CHECKING guards** to avoid circular imports
- **Async throughout** for I/O-bound operations
- **Logging at every API boundary** (Telegram, Notion, Claude)
- **No secrets in logs** (filtered at caller)
- **Regex patterns compiled once** at module level
- **Lock protection** for ProjectsCache (thread-safe refresh)
