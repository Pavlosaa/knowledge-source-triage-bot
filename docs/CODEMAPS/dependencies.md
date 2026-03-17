<!-- Generated: 2026-03-02 | Files scanned: 18 | Token estimate: ~520 -->

# External Dependencies & Services Codemap

**Deps scanned:** 18 files | **External services:** 6 | **Python packages:** 16 | **Updated:** 2026-03-17

---

## Python Package Dependencies

**File:** `requirements.txt`

| Package | Version | Purpose | Usage |
|---------|---------|---------|-------|
| **python-telegram-bot** | 21.10 | Telegram Bot API client (async) | main.py, handler.py |
| **playwright** | 1.50.0 | Headless browser (Chromium) | fetcher/playwright.py (fallback) |
| **httpx** | 0.28.1 | Async HTTP client | fetcher/twitter.py (ScrapFly), fetcher/article.py, fetcher/github.py |
| **beautifulsoup4** | 4.13.3 | HTML parsing | fetcher/twitter.py (ScrapFly), fetcher/article.py |
| **lxml** | 5.3.1 | XML/HTML parser (BS4 backend) | fetcher/twitter.py, fetcher/article.py |
| **anthropic** | 0.49.0 | Claude API client | analyzer/pipeline.py |
| **notion-client** | 2.3.0 | Notion SDK (async) | notion/writer.py, notion/projects.py |
| **python-dotenv** | 1.0.1 | Environment variable loading | config.py (startup) |
| **loguru** | 0.7.3 | Structured logging | all modules |

### Dev / CI Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **pytest** | 8.3.4 | Test framework |
| **pytest-cov** | 6.0.0 | Coverage reporting |
| **pytest-asyncio** | 0.25.3 | Async test support |
| **ruff** | 0.9.7 | Linting + formatting |
| **mypy** | 1.15.0 | Static type checking |
| **pip-audit** | 2.8.0 | Dependency vulnerability scanning |

---

## External Service Integration

### Telegram Bot API

**Module:** `bot/telegram/handler.py`, `main.py`
**Library:** `python-telegram-bot` v21.10
**Protocol:** HTTPS long-polling

**Authentication:**
- `TELEGRAM_BOT_TOKEN` — via @BotFather

**Rate Limits:**
- Unlimited for personal use
- No per-message limits for small groups

**Usage:**
```python
ApplicationBuilder()
  .token(config.telegram_bot_token)
  .build()

MessageHandler(filters.Chat(config.telegram_group_id) & filters.TEXT, handler.handle)
  → receive incoming messages from specific group

message.reply_text(text, parse_mode="HTML")
  → send HTML-formatted replies

message.delete()
  → delete placeholder message
```

**Data exchanged:**
- Message text (URL extraction)
- Message metadata (id, chat_id, user_id)
- Replies (HTML-formatted analysis results)

---

### Claude API (Anthropic)

**Module:** `bot/analyzer/pipeline.py` (not yet implemented)
**Library:** `anthropic` v0.49.0
**Protocol:** HTTPS REST

**Authentication:**
- `ANTHROPIC_API_KEY` — from console.anthropic.com

**Models used:**
| Phase | Model | Inputs | Expected Output |
|-------|-------|--------|-----------------|
| 1 (Credibility) | claude-haiku-4-5 | author + text | JSON: credibility_score, reason |
| 2 (Value Check) | claude-haiku-4-5 | full content | JSON: has_value, rejection_reason? |
| 3A (Full Analysis) | claude-sonnet-4-6 | content + projects | JSON: title, summary, recs, topic |
| 3B (Rejection) | claude-haiku-4-5 | content | JSON: brief_summary, reason |

**Rate Limits:**
- Per-model RPM limits (consult Anthropic pricing page)
- Token-based billing

**Usage pattern (planned):**
```python
client = anthropic.Anthropic(api_key=config.anthropic_api_key)
message = await client.messages.create(
  model="claude-haiku-4-5",
  max_tokens=1024,
  system=CREDIBILITY_SYSTEM,
  messages=[{"role": "user", "content": content}]
)
response_json = json.loads(message.content[0].text)
```

**Data exchanged:**
- Content text (tweets, articles, READMEs)
- Project context (cached, user's projects from Notion)
- Structured JSON responses (analysis results)

---

### Notion API

**Modules:** `bot/notion/writer.py`, `bot/notion/projects.py`
**Library:** `notion-client` v2.3.0
**Protocol:** HTTPS REST (with async support)

**Authentication:**
- `NOTION_API_KEY` — from notion.so/my-integrations
- Integration must have access to parent page

**Endpoints used:**

| Endpoint | Method | Module | Purpose |
|----------|--------|--------|---------|
| `/search` | POST | writer.py | Find existing "AI Sources" database |
| `/databases` | POST | writer.py | Create "AI Sources" database |
| `/pages` | POST | writer.py | Create analysis record page |
| `/blocks/{page_id}/children` | GET | projects.py | Fetch project pages + descriptions |

**Rate Limits:**
- 3 requests/second
- ~500,000 blocks/month quota

**Usage patterns:**

```python
# Create async client
client = AsyncClient(auth=config.notion_api_key)

# Search for database
response = await client.search(query="AI Sources", filter={"property": "object", "value": "database"})

# Create database with properties
db = await client.databases.create(
  parent={"type": "page_id", "page_id": notion_rnd_page_id},
  title=[{"type": "text", "text": {"content": "AI Sources"}}],
  properties={...}
)

# Create page (record)
page = await client.pages.create(
  parent={"database_id": db_id},
  properties={...},
  children=[...]  # blocks
)

# Fetch blocks
response = await client.blocks.children.list(block_id=projects_page_id)
```

**Data exchanged:**
- Database metadata (name, properties, schema)
- Page properties (title, topic select, score, URL, etc.)
- Page body blocks (headings, paragraphs, bullets, toggles, bookmarks)
- Project descriptions (plain text extraction)

---

### X.com / Twitter (ScrapFly API)

**Module:** `bot/fetcher/twitter.py`
**Library:** `httpx` v0.28.1 + `beautifulsoup4` v4.13.3
**Protocol:** HTTPS REST (ScrapFly proxy service)

**Authentication:**
- Optional: `SCRAPFLY_API_KEY` — from scrapfly.io
- Free tier: 1000 requests/month, no authentication
- Paid tier: residential proxies, IP rotation, CAPTCHA handling

**Rate Limits:**
- Free: 1000 req/month (unlimited once quota exhausted, rate-limited)
- Paid: based on plan (~$19/month for basic)

**Content types detected:**
```python
# Tweet: x.com/@user/status/123456789
detect_content_type(url) → "tweet"
fetch_tweet(tweet_id, scrapfly_api_key) → TweetContent(
  tweet_id, author_name, author_username, follower_count,
  is_verified, text, embedded_urls
)

# X Article: x.com/i/article/123456789
detect_content_type(url) → "article"
fetch_article(url, scrapfly_api_key) → ArticleContent(url, title, author_name, body)
```

**Data extracted:**
- Tweet metadata (author, follower count, verified status)
- Tweet text + embedded URLs
- Article title, author, body

**Fallback:** Playwright (fetcher/playwright.py) if ScrapFly call fails

---

### GitHub REST API

**Module:** `bot/fetcher/github.py` (not yet implemented)
**Library:** `httpx` v0.28.1
**Protocol:** HTTPS REST

**Authentication:**
- Optional: `GITHUB_TOKEN` — from github.com/settings/tokens
- Unauthenticated: 60 requests/hour
- Authenticated: 5,000 requests/hour

**Endpoints used:**

```
GET https://api.github.com/repos/{owner}/{repo}
  ├─ Returns: description, stargazers_count, language, topics
  └─ Used in: fetch_repo()

GET https://api.github.com/repos/{owner}/{repo}/readme
  ├─ Returns: download_url (or 404)
  └─ Used in: fetch_repo() (optional)
```

**Data extracted:**
```python
RepoContent(
  owner="username",
  repo="repo-name",
  description="...",
  stars=12345,
  language="Python",
  readme="# README\n..."
)
```

**Usage pattern (planned):**
```python
async with httpx.AsyncClient(headers={"Authorization": f"token {token}"}) as client:
  response = await client.get(f"https://api.github.com/repos/{owner}/{repo}")
  data = response.json()
  repo = RepoContent(...)
```

---

### Generic Articles (httpx + BeautifulSoup4)

**Module:** `bot/fetcher/article.py` (not yet implemented)
**Libraries:** `httpx` v0.28.1, `beautifulsoup4` v4.13.3, `lxml` v5.3.1
**Protocol:** HTTPS

**Authentication:** None (public web)

**Rate Limits:** Per-site; respected via User-Agent

**Flow:**
```
1. Fetch URL via httpx
2. Parse HTML via BeautifulSoup4 + lxml
3. Extract: title (from <title> or <h1>), body (all <p> and <article> text)
4. Return ArticleContent(url, title, body)

If JavaScript-rendered (empty body):
  → Fallback to Playwright (fetcher/playwright.py)
```

**Data extracted:**
```python
ArticleContent(
  url="https://...",
  title="Article Title",
  body="Full article text..."
)
```

---

### Playwright (JavaScript-Heavy Pages)

**Module:** `bot/fetcher/playwright.py` (not yet implemented)
**Library:** `playwright` v1.50.0
**Protocol:** Local headless browser

**Authentication:** None (local automation)

**Browser:** Chromium (headless)

**Usage pattern (planned):**
```python
async with async_playwright() as p:
  browser = await p.chromium.launch()
  page = await browser.new_page()
  await page.goto(url, wait_until="networkidle")
  title = await page.title()
  body = await page.locator("body").text_content()
  await page.close()
  await browser.close()
```

**Data extracted:**
```python
PageContent(
  url="https://...",
  title="Page Title",
  body="Visible page text..."
)
```

**Timeouts:** 30 seconds (configurable)

---

## Dependency Cascade

```
main.py
├─ bot.config (python-dotenv)
├─ bot.telegram.handler (python-telegram-bot)
│  ├─ asyncio (stdlib)
│  ├─ re (stdlib)
│  ├─ loguru
│  └─ telegram.ext (python-telegram-bot)
├─ bot.analyzer.pipeline (anthropic)
│  ├─ dataclasses (stdlib)
│  ├─ loguru
│  ├─ bot.fetcher.* (httpx, playwright, beautifulsoup4)
│  ├─ anthropic (anthropic)
│  ├─ bot.analyzer.prompts
│  ├─ bot.notion.projects (notion-client)
│  └─ bot.notion.writer (notion-client)
├─ bot.telegram.formatter
└─ loguru

Total external packages: 11
Total import paths: ~30
Async dependencies: python-telegram-bot, notion-client, anthropic, httpx, playwright
```

---

## Hosting Environment

**Platform:** Oracle Cloud Free Forever — VM.Standard.E5.Flex (AMD x86), 1 OCPU, 12GB RAM
**OS:** Ubuntu
**Python:** 3.12
**Process Manager:** systemd
**Service File:** `systemd/triage-bot.service`

**System dependencies** (not in requirements.txt):
- Python 3.12 (interpreter)
- libssl, libcrypto (for HTTPS)
- pkg-config (for building some packages)
- Chromium/Chromium-browser binary (for Playwright, can be installed via `playwright install chromium`)

---

## Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│ Oracle Cloud Free Forever (AMD x86, 12GB RAM)               │
│ ├─ Python 3.12 process (bot)                                │
│ └─ systemd service manager                                  │
└────┬──────────────────────────────────────────────────────────┘
     │
     ├─→ https://api.telegram.org (polling)
     │   └─ Message reception, reply sending
     │
     ├─→ https://api.anthropic.com
     │   └─ Claude analysis (4 phases per URL)
     │
     ├─→ https://api.notion.com
     │   └─ Database search, record creation, project context
     │
     ├─→ https://x.com (twikit)
     │   └─ Tweet/article fetching
     │
     ├─→ https://api.github.com
     │   └─ Repository metadata & README
     │
     ├─→ https://* (article fetching)
     │   └─ Generic web articles
     │
     └─→ Chromium headless (Playwright)
         └─ JavaScript-heavy pages (local subprocess)
```

---

## Dependency Risk Assessment

| Package | Maturity | Risk | Notes |
|---------|----------|------|-------|
| python-telegram-bot | High | Low | Official Telegram client, well-maintained |
| anthropic | High | Low | Official Claude SDK, well-maintained |
| notion-client | Medium | Medium | Official but less mature than Telegram; handles API changes well |
| httpx | High | Low | Modern HTTP client; better than requests for async |
| playwright | High | Low | Official Microsoft project; cross-platform browser automation |
| beautifulsoup4 | High | Low | Standard HTML parser; very stable |
| python-dotenv | High | Low | Simple, widely-used env var loader |
| loguru | High | Low | Popular structured logging library |
| lxml | High | Low | C-based parser; fast and stable |

**Key improvements:**
- Replaced twikit (unofficial X client) with ScrapFly API
- ScrapFly handles IP blocking, CAPTCHA, rate-limiting for X.com
- Free tier 1000 req/mo sufficient for casual use
- Fallback: Playwright still available for resilience
- All other dependencies are official or widely-used open-source projects

---

## Deployment Checklist

Before running in production:

1. **System packages:**
   ```bash
   sudo apt-get install python3.12 python3.12-venv libssl-dev
   playwright install chromium  # ~200MB download
   ```

2. **Python environment:**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Secrets (.env file):**
   ```bash
   cp .env.example .env
   # Fill in all required vars (ScrapFly API key is optional)
   chmod 600 .env
   ```

4. **Systemd service:**
   ```bash
   sudo cp systemd/triage-bot.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable triage-bot
   sudo systemctl start triage-bot
   ```

5. **Verify:**
   ```bash
   sudo systemctl status triage-bot
   sudo journalctl -u triage-bot -f  # follow logs
   ```
