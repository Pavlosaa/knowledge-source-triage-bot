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

## 🔲 Phase 2: Fetchers — NEXT
- [ ] twitter.py — twikit session management (login, cookie persistence to cookies.json)
- [ ] twitter.py — fetch_tweet(tweet_id): text, author, follower count, verified
- [ ] twitter.py — detect_content_type(url): tweet vs X Article
- [ ] twitter.py — fetch_article(url): twikit attempt → Playwright fallback
- [ ] playwright.py — headless Chromium setup + fetch_with_playwright(url)
- [ ] article.py — httpx + BS4 generic HTML scraper → Playwright fallback
- [ ] github.py — GitHub REST API: README, stars, description, language
- [ ] Unit tests for each fetcher (mock HTTP responses)

## 🔲 Phase 3: Claude Analyzer
- [x] prompts.py — all 4 prompts defined (credibility, value, full analysis, rejection)
- [ ] pipeline.py — orchestrate 3-phase Claude calls (Haiku → Haiku → Sonnet/Haiku)
- [ ] pipeline.py — JSON response parsing + validation
- [ ] pipeline.py — exponential backoff retry logic (max 3, 2^n seconds)
- [ ] Unit tests for pipeline with mocked Claude responses

## 🔲 Phase 5: Wire Everything Together
- [ ] pipeline.py — integrate fetchers + Claude + Notion into run_pipeline()
- [ ] main.py — pass NotionWriter + ProjectsCache into pipeline at startup
- [ ] End-to-end local test with real URL

## 🔲 Phase 6: Error Handling & Logging
- [x] config.py — env var validation (done in Phase 0)
- [ ] Loguru setup: bot.log + errors.log with rotation (stubs in main.py, needs wiring)
- [ ] Per-request structured log line: timestamp | url | content_type | has_value | score | duration_ms
- [ ] All error paths covered (never silent failure)

## 🔲 Phase 7: Deployment
- [x] systemd/triage-bot.service unit file (created)
- [ ] README — Oracle Cloud setup instructions
- [ ] Playwright Chromium install on VPS: `playwright install chromium`
- [ ] End-to-end smoke test on VPS

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
