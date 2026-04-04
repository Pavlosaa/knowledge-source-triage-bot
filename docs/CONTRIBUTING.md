# Contributing Guide

This document covers local development setup, running the bot, testing procedures, and code style.

**Last Updated:** 2026-04-04

---

## Prerequisites

Before you start, ensure you have:

- **Python 3.12+** (check with `python3 --version`)
- **pip** (usually comes with Python)
- **Git** (for version control)
- **Playwright dependencies** (we'll install Chromium in setup)

### macOS

```bash
# Install Python 3.12 via Homebrew
brew install python@3.12

# Verify
python3.12 --version
```

### Ubuntu/Debian

```bash
# Install Python 3.12
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip

# Verify
python3.12 --version
```

### Windows

Download from https://www.python.org/downloads/ (Python 3.12+)

---

<!-- AUTO-GENERATED: Setup Instructions -->

## Local Setup

### 1. Clone the Repository

```bash
cd /path/to/projects
git clone https://github.com/Pavlosaa/knowledge-source-triage-bot.git
cd knowledge-source-triage-bot
```

### 2. Create a Virtual Environment

```bash
python3.12 -m venv venv
source venv/bin/activate       # On macOS/Linux
# OR
venv\Scripts\activate.bat      # On Windows
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install Playwright Browsers

```bash
playwright install chromium
```

This downloads a headless Chromium browser (used for JS-heavy pages).

### 5. Configure Environment Variables

```bash
cp .env.example .env
```

Now open `.env` and fill in your actual values. See `docs/ENV.md` for details.

**At minimum, you need:**
- `TELEGRAM_BOT_TOKEN` — from @BotFather
- `TELEGRAM_GROUP_ID` — your private test group
- `ANTHROPIC_API_KEY` — from https://console.anthropic.com
- `NOTION_API_KEY`, `NOTION_RND_PAGE_ID`, `NOTION_PROJECTS_PAGE_ID` — from Notion

**Optional:**
- `SCRAPFLY_API_KEY` — for X.com tweet/article support (free tier: 1000 req/month)

<!-- END AUTO-GENERATED: Setup Instructions -->

---

## Running the Bot Locally

### Start the Bot

```bash
python main.py
```

Expected output:
```
2026-03-02 14:23:45 | INFO | Configuration loaded.
2026-03-02 14:23:46 | INFO | Bot started. Listening for messages...
```

The bot will now listen for messages in your Telegram group. Leave it running.

### Test It

1. Open Telegram and go to your configured group
2. Share a link (e.g., `https://twitter.com/elonmusk/status/123456`)
3. Bot will acknowledge receipt and begin processing
4. Check logs:
   - `logs/bot.log` — all events
   - `logs/errors.log` — errors only

### Stop the Bot

Press `Ctrl+C` in the terminal.

---

## Code Style & Conventions

This project follows the conventions in `CLAUDE.md`. Key principles:

### 1. Immutability (CRITICAL)

Always create new objects, never mutate existing ones:

```python
# WRONG
def update_config(config, field, value):
    config.field = value  # Mutates!
    return config

# CORRECT
from dataclasses import replace
def update_config(config, field, value):
    return replace(config, **{field: value})  # New instance
```

### 2. File Organization

- Keep files focused: **200–400 lines typical, 800 max**
- Organize by feature/domain, not by type
- Extract utilities from large modules

Example structure:
```
bot/
├── config.py          # Configuration (small)
├── telegram/
│   ├── handler.py     # Message handling (focused)
│   └── formatter.py   # Result formatting (focused)
├── fetcher/
│   ├── twitter.py     # Twitter-specific
│   ├── article.py     # Generic articles
│   └── __init__.py
└── analyzer/
    ├── pipeline.py    # Orchestration
    └── prompts.py     # Claude prompts
```

### 3. Error Handling

Always handle errors comprehensively:

```python
# WRONG
try:
    result = fetch_url(url)
except:
    pass  # Silent failure!

# CORRECT
try:
    result = await fetch_url(url)
except httpx.TimeoutException as e:
    logger.error(f"Timeout fetching {url}: {e}")
    return AnalysisResult(
        url=url,
        success=False,
        error="Timeout: took too long to fetch"
    )
except httpx.HTTPError as e:
    logger.error(f"HTTP error fetching {url}: {e}")
    return AnalysisResult(
        url=url,
        success=False,
        error=f"HTTP error: {e.status_code}"
    )
```

### 4. Input Validation

Always validate at system boundaries:

```python
# WRONG
def analyze(url: str) -> Result:
    return do_analysis(url)  # No validation!

# CORRECT
def analyze(url: str) -> Result:
    if not url or not url.startswith(("http://", "https://")):
        raise ValueError(f"Invalid URL: {url}")
    return do_analysis(url)
```

### 5. Code Quality Checklist

Before committing, verify:

- [ ] Code is readable and well-named
- [ ] Functions are small (<50 lines)
- [ ] Files are focused (<800 lines)
- [ ] No deep nesting (>4 levels)
- [ ] Proper error handling
- [ ] No hardcoded values (use constants or config)
- [ ] No mutation (immutable patterns used)

---

## Testing Procedures

### Manual Testing

1. **Setup a test Telegram group** with your bot
2. **Share test URLs:**
   - Twitter: `https://x.com/username/status/123456`
   - GitHub: `https://github.com/owner/repo`
   - Article: `https://example.com/article`
3. **Check the response:**
   - Bot should acknowledge receipt
   - Should create a Notion page in "AI Sources" database
   - Should reply with a summary and Notion link

### Automated Testing

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=bot --cov-report=term-missing

# Run specific test file
pytest tests/test_config.py -v
```

Coverage goal: **80%+**

Test fixtures are in `tests/conftest.py` (mock env vars, etc.).

**Existing test files:**
- `tests/test_twitter.py` — 14 unit tests for X.com fetcher (94% coverage)
- `tests/test_references.py` — 14 tests for cross-referencing logic (3 skip without notion_client)
- `tests/test_extractor.py` — 10 tests for GitHub URL extraction
- `tests/test_pipeline_discovery.py` — 5 tests for discovery orchestrator
- `tests/test_formatter.py` — 4 tests for multi-result Telegram formatting

### Debugging

Enable debug logging:

```python
# In main.py, change logger level:
logger.add(sys.stderr, level="DEBUG", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
```

Then run:
```bash
python main.py 2>&1 | grep DEBUG
```

---

## Making Changes

### 1. Create a Feature Branch

```bash
git checkout -b feat/your-feature-name
```

### 2. Make Your Changes

- Write code following the style guide above
- Keep commits atomic and focused
- Include clear commit messages

### 3. Test Your Changes

- Run the bot locally and verify behavior
- Check logs for errors
- Make sure no hardcoded values leak in

### 4. Commit

```bash
git add .
git commit -m "feat(module): clear description of change"
```

Use conventional commit format: `type(scope): description`

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`

### 5. Verify Locally

Before pushing, run the CI checks locally:

```bash
ruff check . && ruff format --check . && mypy bot/ && pytest --cov=bot
```

### 6. Push and Create a PR

```bash
git push origin feat/your-feature-name
```

Then create a pull request on GitHub. CI pipeline (lint, typecheck, test, security) must pass before merging.

---

## Project Structure Reference

```
knowledge-source-triage-bot/
├── bot/                          # Main application
│   ├── __init__.py
│   ├── config.py                 # Configuration loading + validation
│   ├── telegram/
│   │   ├── handler.py            # Message handler + queue processor
│   │   └── formatter.py          # Result formatting for Telegram
│   ├── fetcher/
│   │   ├── twitter.py            # X.com tweets/articles (ScrapFly HTTP API)
│   │   ├── article.py            # Generic articles (httpx + BS4)
│   │   ├── github.py             # GitHub repos (REST API)
│   │   └── playwright.py         # Headless browser fallback
│   ├── analyzer/
│   │   ├── pipeline.py           # Analysis orchestration + discovery
│   │   ├── prompts.py            # All Claude system prompts (5)
│   │   ├── extractor.py          # GitHub URL extraction from content
│   │   └── json_utils.py         # JSON parsing from Claude responses
│   └── notion/
│       ├── writer.py             # Notion DB + page creation
│       ├── references.py         # Cross-referencing logic (F1)
│       └── projects.py           # Project context cache
├── scripts/
│   └── backfill_references.py    # One-time cross-reference backfill
├── tests/                         # pytest test suite (50 tests)
│   ├── __init__.py
│   └── conftest.py               # Shared fixtures (mock env, etc.)
├── .github/workflows/             # CI/CD pipelines
│   ├── ci.yml                    # lint, typecheck, test, security
│   └── deploy.yml                # Auto-deploy to Oracle Cloud
├── main.py                        # Entry point
├── pyproject.toml                 # ruff, mypy, pytest config
├── requirements.txt               # Python dependencies (prod + dev)
├── .env.example                   # Env var template
├── .env                           # (local, not committed)
├── logs/
│   ├── bot.log                    # All events
│   └── errors.log                 # Errors only
├── docs/
│   ├── ENV.md                     # Environment variables
│   ├── CONTRIBUTING.md            # This file
│   ├── RUNBOOK.md                 # Deployment guide
│   ├── plans/
│   │   └── 2026-03-01-ai-knowledge-triage-design.md
│   └── CODEMAPS/
│       ├── INDEX.md
│       ├── architecture.md
│       ├── backend.md
│       ├── data.md
│       └── dependencies.md
├── tasks/
│   ├── todo.md                    # Task backlog
│   └── lessons.md                 # Lessons learned
├── systemd/
│   └── triage-bot.service         # systemd unit file
└── CLAUDE.md                       # Project-specific instructions

```

---

## Useful Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Install a new dependency
pip install package-name
pip freeze > requirements.txt

# Run the bot with debug output
python main.py

# View recent logs
tail -f logs/bot.log

# Clear old logs
rm logs/*.log

# Lint (check for issues)
ruff check .

# Auto-fix lint issues
ruff check --fix .

# Format code
ruff format .

# Type check
mypy bot/

# Run tests
pytest --cov=bot

# Dependency vulnerability scan
pip-audit
```

---

## Getting Help

- **Architecture question?** Read `docs/CODEMAPS/architecture.md`
- **Data structure question?** Read `docs/CODEMAPS/data.md`
- **Deployment question?** Read `docs/RUNBOOK.md`
- **Environment setup?** Read `docs/ENV.md`
- **Design decisions?** Read `docs/plans/2026-03-01-ai-knowledge-triage-design.md`

---

## Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'bot'` | Make sure you're in the project root and venv is activated |
| `TELEGRAM_BOT_TOKEN not found` | Run `cp .env.example .env` and fill in your values |
| `playwright install chromium` hangs | Try `playwright install --with-deps chromium` |
| Bot doesn't receive messages | Check `TELEGRAM_GROUP_ID` is correct and bot is admin in the group |
| "Claude API error: invalid_api_key" | Verify your `ANTHROPIC_API_KEY` is correct |

---

## Next Steps

1. Follow setup above
2. Configure `.env`
3. Run `python main.py`
4. Share a test link in your Telegram group
5. Watch the logs in `logs/bot.log`

Good luck!
