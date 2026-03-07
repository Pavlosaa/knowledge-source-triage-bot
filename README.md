# AI Knowledge Source Triage Bot

Personal Telegram bot that triages AI-related links shared in a group chat. Analyzes content quality via a 3-phase Claude pipeline and creates structured records in Notion.

## What it does

1. Someone shares a link in a Telegram group (tweet, GitHub repo, article)
2. Bot fetches the content (twikit / Playwright / GitHub API / httpx+BS4)
3. Claude runs a 3-phase analysis:
   - Phase 1: Credibility check (Haiku)
   - Phase 2: Value assessment (Haiku)
   - Phase 3: Full analysis or rejection summary (Sonnet / Haiku)
4. Valuable sources get a Notion record with summary, key principles, use cases, and project relevance
5. Bot replies with the result and a link to the Notion page

## Supported content types

| URL pattern | Fetcher |
|-------------|---------|
| `x.com/*/status/*` | twikit (tweet text, author, followers) |
| `x.com/i/article/*` | Playwright headless Chromium |
| `github.com/owner/repo` | GitHub REST API (README, stars, language) |
| anything else | httpx + BS4, Playwright fallback |

## Tech stack

Python 3.12 | python-telegram-bot v21 | twikit | Playwright | httpx + BeautifulSoup4 | anthropic | notion-client | loguru

## Quick start

### Prerequisites

Complete all manual setup steps before deploying:

1. Create Telegram bot via @BotFather, add to a group, make it admin
2. Get Anthropic API key from console.anthropic.com
3. Get Notion API key, share your R&D and Projects pages with the integration
4. Have X.com account credentials (username, email, password)

See [docs/RUNBOOK.md](docs/RUNBOOK.md) for step-by-step instructions.

### Local run

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Edit .env with your credentials

python main.py
```

### Deploy to Oracle Cloud (systemd)

```bash
# On the server
git clone <repo-url>
cd ai-knowledge-source-triage

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
nano .env  # Fill in all values

sudo cp systemd/triage-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable triage-bot
sudo systemctl start triage-bot
sudo systemctl status triage-bot
```

Full deployment guide: [docs/RUNBOOK.md](docs/RUNBOOK.md)

## Project structure

```
bot/
  analyzer/       # Claude pipeline (prompts.py, pipeline.py)
  fetcher/        # Content fetchers (twitter, playwright, article, github)
  notion/         # Notion writer + projects cache
  telegram/       # Message handler + formatter
  config.py       # Env var loading with fail-fast validation
main.py           # Entry point
systemd/          # triage-bot.service unit file
docs/             # Design doc, runbook, codemaps
tasks/            # todo.md, lessons.md
```

## Environment variables

See [.env.example](.env.example) for all required variables and [docs/ENV.md](docs/ENV.md) for detailed documentation.

## Logs

```bash
sudo journalctl -u triage-bot -f          # Live (systemd)
tail -f logs/bot.log                      # Application log
tail -f logs/errors.log                   # Errors only
```

Log format per processed URL:
```
pipeline_done | url=... | type=Tweet | has_value=True | score=4 | duration_ms=8432
```

## Documentation

- [docs/RUNBOOK.md](docs/RUNBOOK.md) — deployment, operations, troubleshooting
- [docs/ENV.md](docs/ENV.md) — environment variables reference
- [docs/CODEMAPS/INDEX.md](docs/CODEMAPS/INDEX.md) — codebase navigation
- [docs/plans/2026-03-01-ai-knowledge-triage-design.md](docs/plans/2026-03-01-ai-knowledge-triage-design.md) — original design doc
