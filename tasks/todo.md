# Task Backlog

## ✅ Phase 0: Project Setup — DONE
- [x] Initialize git repo
- [x] Create .gitignore, .env.example, requirements.txt
- [x] Create folder structure (bot/, docs/, tasks/, systemd/)
- [x] config.py — validate all required env vars at startup with fail-fast
- [ ] Add claude.md project specifics section (carry-over, low priority)

## ✅ Phase 1: Telegram Bot Skeleton — DONE
- [x] Implement handler.py — receive messages, extract URLs
- [x] Implement asyncio.Queue for sequential processing
- [x] Send "⏳ Analyzuji..." placeholder reply + delete on completion
- [x] formatter.py — valuable / low-value / error templates (HTML)
- [x] main.py — entry point, wires config + queue + bot
- [x] Create Telegram bot via @BotFather + fill .env (done manually)
- [x] Smoke test: bot receives messages and processes URLs ✅ live

## ✅ Phase 4: Notion Integration — DONE
- [x] projects.py — ProjectsCache: load project pages from Notion, 24h TTL
- [x] writer.py — NotionWriter: find-or-create "AI Sources" database on first run
- [x] writer.py — database properties: Topic, Score, Tags, URL, Author, Date, Projects
- [x] writer.py — page body blocks: Shrnutí, Klíčové poznatky, Využití, Relevance pro projekty (toggles), Zdroj bookmark
- [x] prompts.py — topic classification added to Phase 3A (6 predefined categories)
- [x] All output in Czech (prompts, Notion headings) ✅ live

## ✅ Phase 2: Fetchers — DONE
- [x] twitter.py — twikit session management (login, cookie persistence to cookies.json)
- [x] twitter.py — fetch_tweet(tweet_id): text, author, follower count, verified
- [x] twitter.py — detect_content_type(url): tweet vs X Article
- [x] twitter.py — fetch_article(url): Playwright fallback (twikit doesn't support X Articles)
- [x] playwright.py — headless Chromium setup + fetch_with_playwright(url)
- [x] article.py — httpx + BS4 generic HTML scraper → Playwright fallback
- [x] github.py — GitHub REST API: README, stars, description, language
- [ ] Unit tests for each fetcher (mock HTTP responses)

## ✅ Phase 3: Claude Analyzer — DONE
- [x] prompts.py — all 4 prompts defined (credibility, value, full analysis, rejection)
- [x] pipeline.py — orchestrate 3-phase Claude calls (Haiku → Haiku → Sonnet/Haiku)
- [x] pipeline.py — JSON response parsing + validation
- [x] pipeline.py — exponential backoff retry logic (max 3, 2^n seconds)
- [ ] Unit tests for pipeline with mocked Claude responses

## ✅ Phase 5: Wire Everything Together — DONE
- [x] pipeline.py — integrate fetchers + Claude + Notion into run_pipeline()
- [x] main.py — NotionWriter + ProjectsCache instantiated at startup via functools.partial
- [ ] End-to-end local test with real URL

## ✅ Phase 6: Error Handling & Logging — DONE
- [x] config.py — env var validation (done in Phase 0)
- [x] Loguru setup: bot.log + errors.log with rotation (main.py)
- [x] Per-request structured log line: url | content_type | has_value | score | duration_ms
- [x] All error paths covered (fetch fail, credibility reject, value reject, Phase 3A fail, Notion fail)

## ✅ Phase 7: Deployment — DONE
- [x] systemd/triage-bot.service unit file (fixed path: knowledge-source-triage-bot)
- [x] README.md — project overview + Oracle Cloud setup instructions
- [x] Playwright Chromium install documented in README + RUNBOOK
- [x] End-to-end smoke test on VPS ✅ live (GitHub → Claude → Notion → Telegram)
- [x] All output in Czech ✅

---

## LIVE STATE — 2026-03-07

**Server:** Oracle Cloud 130.61.130.58 — `triage-bot.service` active, auto-restart on failure

**What works end-to-end (verified live):**
- GitHub URLs → fetch repo + README → 3-phase Claude → Notion record + Telegram reply
- Article URLs → httpx+BS4 → Playwright fallback → 3-phase Claude → Notion + Telegram
- All Claude output in Czech (summaries, principles, use cases)
- Notion "AI Sources" database auto-created on first run
- Structured log line per URL: `url | type | has_value | score | duration_ms`

**Known limitation — X.com / Twitter:**
- Oracle Cloud datacenter IPs are blocked by X.com at network level
- twikit login fails (Cloudflare), browser cookies also return 401
- Bot gracefully reports fetch error for tweet URLs
- Fix: residential proxy or Twitter API v2 (paid) — **not yet implemented**

## ⏳ Remaining / Future Work

- [ ] X.com fetching — residential proxy or Twitter API v2
- [ ] Unit tests for fetchers (mocked HTTP)
- [ ] Unit tests for pipeline (mocked Claude responses)
