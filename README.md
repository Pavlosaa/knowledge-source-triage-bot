# AI Knowledge Source Triage Bot

Personal Telegram bot that triages AI-related links shared in a group chat. Analyzes content via a multi-phase Claude pipeline and creates structured records in Notion.

## What it does

1. Someone shares a link in a Telegram group (tweet, GitHub repo, article)
2. Bot fetches the content (ScrapFly / Playwright / GitHub API / httpx+BS4)
3. Claude analyzes it:
   - Phase 1: Credibility check (fast model, Haiku 5.5) — score < 2 rejects the source
   - Phase 3A: Full analysis (analysis model, Sonnet 5.5) for everything that passes
   - Phase 3B: Short rejection summary (fast model) for low-credibility sources
4. Accepted sources get a Notion record with summary, key principles, use cases, real-world example and project relevance
5. GitHub repos linked from an article/tweet are analyzed as separate records (discovery), and related records are cross-linked in Notion
6. Bot replies with the result and a link to the Notion page(s)

Rejected the wrong link? Reply `/accept` to the bot's rejection message to force a re-analysis (adds a "Manual Override" tag).

Models are configurable via `CLAUDE_FAST_MODEL` / `CLAUDE_ANALYSIS_MODEL` (see [docs/ENV.md](docs/ENV.md)).

## Supported content types

| URL pattern | Fetcher |
|-------------|---------|
| `x.com/*/status/*` | ScrapFly HTTP API (tweet text, author, followers) — optional, requires API key |
| `x.com/i/article/*` | ScrapFly HTTP API — optional, requires API key |
| `github.com/owner/repo` | GitHub REST API (README, stars, language) |
| anything else | httpx + BS4, Playwright fallback |

## Tech stack

Python 3.12 | python-telegram-bot v21 | httpx | Playwright | BeautifulSoup4 | anthropic 1.x | notion-client | loguru

## CI/CD

GitHub Actions pipeline runs on every push/PR to `main`:

| Job | Tool | What it checks |
|-----|------|----------------|
| **lint** | ruff | Code style + import sorting |
| **typecheck** | mypy | Static type analysis |
| **test** | pytest | Unit tests with coverage |
| **security** | pip-audit + TruffleHog | CVE scanning + secret detection |

Auto-deploy to Oracle Cloud on successful CI, or manually via Actions → Deploy → Run workflow (requires GitHub Secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`). The deploy fails if `triage-bot.service` is not active after restart.

Branch protection on `main`: PR required, all CI checks must pass, no force push.

## Quick start

### Prerequisites

Complete all manual setup steps before deploying:

1. Create Telegram bot via @BotFather, add to a group, make it admin
2. Get Anthropic API key from console.anthropic.com
3. Get Notion API key, share your R&D and Projects pages with the integration
4. (Optional) Get ScrapFly API key for X.com tweet/article support

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
git clone https://github.com/Pavlosaa/knowledge-source-triage-bot.git
cd knowledge-source-triage-bot

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
  analyzer/       # Claude pipeline (pipeline.py, prompts.py, claude.py, extractor.py)
  fetcher/        # Content fetchers (twitter, playwright, article, github)
  notion/         # Notion writer, cross-references, projects cache
  telegram/       # Message handler + formatter
  config.py       # Env var loading with fail-fast validation
main.py           # Entry point
scripts/          # backfill_references.py (one-time cross-ref backfill)
tests/            # pytest test suite + fixtures
.github/workflows/ # CI (lint, typecheck, test, security) + deploy
pyproject.toml    # ruff, mypy, pytest config
systemd/          # triage-bot.service unit file
docs/             # Design doc, runbook, codemaps, plans
tasks/            # todo.md, ISSUES.md, lessons.md
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
- [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) — local development, code style, testing
- [docs/CODEMAPS/INDEX.md](docs/CODEMAPS/INDEX.md) — codebase navigation
- [docs/plans/2026-03-01-ai-knowledge-triage-design.md](docs/plans/2026-03-01-ai-knowledge-triage-design.md) — original design doc
