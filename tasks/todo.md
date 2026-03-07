# Task Backlog

## ✅ Phase 0: Project Setup — DONE
- [x] Initialize git repo
- [x] Create .gitignore, .env.example, requirements.txt
- [x] Create folder structure (bot/, docs/, tasks/, systemd/)
- [x] config.py — validate all required env vars at startup with fail-fast
- [ ] Add claude.md project specifics section (carry-over, low priority)

## ✅ Phase 1: Telegram Bot Skeleton — DONE (code ready, needs live bot token)
- [x] Implement handler.py — receive messages, extract URLs
- [x] Implement asyncio.Queue for sequential processing
- [x] Send "⏳ Analyzuji..." placeholder reply + delete on completion
- [x] formatter.py — valuable / low-value / error templates (HTML)
- [x] main.py — entry point, wires config + queue + bot
- [ ] Create Telegram bot via @BotFather + fill .env (manual step)
- [ ] Smoke test: bot receives message and echoes URL back

## ✅ Phase 4: Notion Integration — DONE (code ready, needs API token in .env)
- [x] projects.py — ProjectsCache: load project pages from Notion, 24h TTL
- [x] writer.py — NotionWriter: find-or-create "AI Sources" database on first run
- [x] writer.py — database properties: Topic, Score, Tags, URL, Author, Date, Projects
- [x] writer.py — page body blocks: Summary, Principles, Use Cases, Project Recs (toggles), Source bookmark
- [x] prompts.py — topic classification added to Phase 3A (6 predefined categories)
- [ ] Integration test against live Notion (needs API token)

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

## ✅ Phase 7: Deployment — mostly done
- [x] systemd/triage-bot.service unit file (created)
- [x] README.md — project overview + Oracle Cloud setup instructions
- [x] Playwright Chromium install documented in README + RUNBOOK
- [ ] End-to-end smoke test on VPS (needs live .env)

---

## DEV BREAKPOINT — 2026-03-02

**Git state:** clean, all work committed on `main`

**Last commit:** `feat(notion): database writer, project context cache, topic classification in prompts`

**What works (code-complete, not yet live-tested):**
- Project structure, config validation, .env.example
- Telegram handler + formatter + asyncio queue
- Notion writer (find-or-create DB + record creation)
- Notion projects cache (24h TTL)
- All 4 Claude prompts (incl. topic classification)

**What needs implementation next (Phase 2 first):**
- twikit fetcher (twitter.py)
- Playwright fallback (playwright.py)
- Article scraper (article.py)
- GitHub API fetcher (github.py)
- Claude pipeline orchestration (pipeline.py)

**Manual prerequisites before any live testing:**
1. Create Telegram bot via @BotFather
2. Create Telegram group, add bot as admin
3. Fill in .env (all tokens: Telegram, Anthropic, Notion, Twitter credentials)
4. `pip install -r requirements.txt`
5. `playwright install chromium`
