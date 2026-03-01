# Task Backlog

## Phase 0: Project Setup
- [ ] Initialize git repo
- [ ] Create .gitignore, .env.example, requirements.txt
- [ ] Create folder structure (bot/, docs/, tasks/, systemd/)
- [ ] Add claude.md project specifics section

## Phase 1: Telegram Bot Skeleton
- [ ] Create Telegram bot via @BotFather
- [ ] Implement handler.py — receive messages, extract URLs
- [ ] Implement asyncio.Queue for sequential processing
- [ ] Send "⏳ Analyzuji..." placeholder reply
- [ ] Smoke test: bot receives message and echoes URL back

## Phase 2: Fetchers
- [ ] twitter.py — twikit session management (login, cookie persistence)
- [ ] twitter.py — fetch_tweet(tweet_id): text, author, follower count, verified
- [ ] twitter.py — detect_content_type(url): tweet vs X Article
- [ ] twitter.py — fetch_article(url): twikit attempt
- [ ] playwright.py — headless Chromium setup
- [ ] playwright.py — fetch_with_playwright(url): full page content
- [ ] article.py — httpx + BS4 generic HTML scraper
- [ ] github.py — GitHub REST API: README, stars, description, language
- [ ] Unit tests for each fetcher (mock HTTP responses)

## Phase 3: Claude Analyzer
- [ ] prompts.py — Phase 1 credibility check prompt
- [ ] prompts.py — Phase 2 value assessment prompt
- [ ] prompts.py — Phase 3A full analysis prompt (with projects_context)
- [ ] prompts.py — Phase 3B rejection summary prompt
- [ ] pipeline.py — orchestrate 3-phase Claude calls
- [ ] pipeline.py — JSON response parsing + validation
- [ ] pipeline.py — exponential backoff retry logic
- [ ] Unit tests for pipeline with mocked Claude responses

## Phase 4: Notion Integration
- [ ] projects.py — load project descriptions from Notion (with 24h cache)
- [ ] writer.py — create subpage under ICT R&D Resources
- [ ] writer.py — page properties (score, tags, date, author, content type)
- [ ] writer.py — page body blocks (summary, principles, use cases, project recs)
- [ ] Integration test against Notion sandbox

## Phase 5: Telegram Formatter & Reply
- [ ] formatter.py — valuable source template
- [ ] formatter.py — low-value source template
- [ ] formatter.py — error template
- [ ] handler.py — delete "⏳" message, send formatted reply with quote

## Phase 6: Error Handling & Logging
- [ ] config.py — validate all required env vars at startup
- [ ] Loguru setup: bot.log + errors.log with rotation
- [ ] Per-request structured log line
- [ ] All error paths covered (never silent failure)

## Phase 7: Deployment
- [ ] systemd/triage-bot.service unit file
- [ ] Oracle Cloud setup instructions (README)
- [ ] Playwright Chromium install on VPS
- [ ] End-to-end smoke test on VPS
