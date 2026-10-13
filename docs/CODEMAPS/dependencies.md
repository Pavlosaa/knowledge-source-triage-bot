<!-- Generated: 2026-03-02 | Updated: 2026-10-13 | Files scanned: 33 | Token estimate: ~600 -->

# External Dependencies & Services Codemap

---

## Python Packages

### Production
| Package | Version | Purpose |
|---------|---------|---------|
| python-telegram-bot | 21.10 | Telegram bot framework |
| anthropic | 1.13.0 | Claude API client |
| notion-client | 2.3.0 | Notion API (async) |
| httpx | 0.28.1 | Async HTTP client |
| beautifulsoup4 | 4.13.3 | HTML parsing |
| lxml | 6.1.0 | XML/HTML parsing backend |
| playwright | 1.50.0 | Headless browser (JS pages) |
| python-dotenv | 1.2.2 | .env loading |
| loguru | 0.7.3 | Structured logging |

### Development
| Package | Version | Purpose |
|---------|---------|---------|
| pytest | 9.0.3 | Test framework |
| pytest-asyncio | 1.3.0 | Async test support |
| pytest-cov | 6.0.0 | Coverage |
| ruff | 0.9.7 | Lint + format |
| mypy | 1.15.0 | Type checking |
| pip-audit | 2.8.0 | Security scanning |

---

## External Service Integrations

### Telegram (python-telegram-bot v21)
- **Auth:** TELEGRAM_BOT_TOKEN
- **Usage:** Receive group messages, send replies (HTML), delete placeholders
- **Rate limit:** Unlimited for receiving; 30 msg/sec sending

### Claude API (anthropic v1.13)
- **Auth:** ANTHROPIC_API_KEY
- **Models:** Haiku 5.5 (phases 1, 3B, cross-ref), Sonnet 5.5 (phase 3A) — overridable via `CLAUDE_FAST_MODEL` / `CLAUDE_ANALYSIS_MODEL`, defaults in `bot/analyzer/claude.py`
- **Calls per URL:** 3 (credibility + analysis + cross-ref), 2 for a rejection (credibility + rejection summary)
- **With discovery:** Up to 3 × (1 + N repos) calls per message (max 5 repos)
- **Request options:** `output_config.effort` (low for fast calls, medium for analysis), `max_tokens` 16k, server-side refusal fallback on Sonnet 5.5
- **Retry:** Exponential backoff, 3 attempts

### Notion API (notion-client v2.3, async)
- **Auth:** NOTION_API_KEY
- **Rate limit:** 3 req/sec (backfill script uses 0.35s delay)
- **Operations:** DB search/create, page create/update/query, relation write
- **Database:** "AI Sources" under NOTION_RND_PAGE_ID

### ScrapFly (httpx)
- **Auth:** SCRAPFLY_API_KEY (optional)
- **Usage:** X.com tweet + article fetching (residential proxy + JS render)
- **Free tier:** 1000 req/month
- **Without key:** X.com URLs return friendly error

### GitHub REST API (httpx)
- **Auth:** GITHUB_TOKEN (optional)
- **Usage:** Repo metadata + README fetch
- **Rate limit:** 60 req/h (unauthenticated), 5000 req/h (with token)

### Playwright (v1.50)
- **Auth:** None (local)
- **Usage:** Fallback for JS-heavy article pages
- **Requires:** `playwright install chromium`

---

## CI/CD Pipeline

```
GitHub Actions (.github/workflows/)
├─ ci.yml: ruff check → mypy → pytest → pip-audit + TruffleHog
└─ deploy.yml: SSH deploy to Oracle Cloud after CI on main passes (or workflow_dispatch);
   git pull → pip install → restart → systemctl is-active check
```

**Branch protection:** PR required, CI must pass, no force push.
