<!-- Generated: 2026-03-02 | Updated: 2026-04-08 | Files scanned: 29 | Token estimate: ~600 -->

# External Dependencies & Services Codemap

---

## Python Packages

### Production
| Package | Version | Purpose |
|---------|---------|---------|
| python-telegram-bot | 21.10 | Telegram bot framework |
| anthropic | 0.49.0 | Claude API client |
| notion-client | 2.3.0 | Notion API (async) |
| httpx | 0.28.1 | Async HTTP client |
| beautifulsoup4 | 4.13.3 | HTML parsing |
| lxml | 5.3.1 | XML/HTML parsing backend |
| playwright | 1.50.0 | Headless browser (JS pages) |
| python-dotenv | 1.0.1 | .env loading |
| loguru | 0.7.3 | Structured logging |

### Development
| Package | Version | Purpose |
|---------|---------|---------|
| pytest | 8.3.4 | Test framework |
| pytest-asyncio | 0.25.3 | Async test support |
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

### Claude API (anthropic v0.49)
- **Auth:** ANTHROPIC_API_KEY
- **Models:** Haiku (phases 1, 2, 3B, cross-ref), Sonnet (phase 3A)
- **Calls per URL:** 3-4 (credibility + value + analysis + cross-ref)
- **With discovery:** Up to 4 × (1 + N repos) calls per message
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
└─ deploy.yml: SSH auto-deploy to Oracle Cloud after CI passes
```

**Branch protection:** PR required, CI must pass, no force push.
