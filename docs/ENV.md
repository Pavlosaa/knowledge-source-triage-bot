# Environment Variables

This document describes all environment variables required and optional for the AI Knowledge Source Triage Bot.

**Last Updated:** 2026-03-11

<!-- AUTO-GENERATED -->

## Overview

The bot reads configuration from a `.env` file in the project root. Use `.env.example` as a template:

```bash
cp .env.example .env
# Then fill in your actual values
```

---

## Required Variables

| Variable | Purpose | Format | Example |
|----------|---------|--------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot API token from @BotFather | String | `123456:ABCDefGH...` |
| `TELEGRAM_GROUP_ID` | Telegram group chat ID (must be negative for groups) | Integer (negative) | `-100123456789` |
| `TWITTER_USERNAME` | X.com (formerly Twitter) username for content scraping | String | `your_username` |
| `TWITTER_PASSWORD` | X.com password (used by twikit client) | String | `your_password` |
| `TWITTER_EMAIL` | X.com email address (used by twikit client) | String | `user@example.com` |
| `ANTHROPIC_API_KEY` | Claude API key from Anthropic | String (starts with `sk-ant-`) | `sk-ant-...` |
| `NOTION_API_KEY` | Notion integration API key | String (starts with `secret_`) | `secret_...` |
| `NOTION_RND_PAGE_ID` | Notion page ID for R&D resources (parent of "AI Sources" database) | UUID | `316c70a6c8c8806c9bc4f3fd04213a89` |
| `NOTION_PROJECTS_PAGE_ID` | Notion page ID for projects (used in analysis context) | UUID | `90ae7fd720c246bb945524f439ea10e3` |

---

## Optional Variables

| Variable | Purpose | Format | Example | Default |
|----------|---------|--------|---------|---------|
| `GITHUB_TOKEN` | GitHub API token (increases rate limit from 60 to 5000 req/h) | String (starts with `ghp_`) | `ghp_...` | Not set (60 req/h limit) |

---

## Getting Your Values

### Telegram

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow prompts to create a new bot
3. BotFather will give you a token: `TELEGRAM_BOT_TOKEN`
4. Create a private group, add your bot as admin
5. Get the group ID:
   - In Telegram Desktop: right-click group → Copy Invite Link, extract the numeric ID, prepend `-100`
   - Via bot: send a message in the group, call Telegram API: `https://api.telegram.org/bot<TOKEN>/getUpdates`

### X.com (Twitter)

1. Visit https://x.com and log in with your account
2. Get your username, password, and registered email
3. **Warning:** twikit is an unofficial client. X.com may block or rate-limit your account. Use a dedicated test account if possible.

### Claude API

1. Visit https://console.anthropic.com
2. Create an API key and copy it (format: `sk-ant-...`)
3. Keep this secret — it costs money per request

### Notion

1. Go to https://www.notion.so/my-integrations
2. Click "Create new integration"
3. Copy the API key (format: `secret_...`)
4. In Notion, find your R&D Resources page:
   - Copy the page ID from URL: `https://notion.so/MY_WORKSPACE_NAME/<PAGE_ID>?...`
   - This becomes `NOTION_RND_PAGE_ID`
5. Similarly, get your Projects page ID for `NOTION_PROJECTS_PAGE_ID`
6. Share both pages with your integration (click `...` → "Add connections" → select your integration)

### GitHub (Optional)

1. Visit https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `public_repo`, `repo` (read-only)
4. Copy and save as `GITHUB_TOKEN`

---

## Configuration Validation

The bot validates all required variables at startup (in `bot/config.py`):

- **Missing required var?** Bot will crash with a clear error message
- **Invalid format?** Bot will validate and reject on startup
- **Empty values?** Treated as missing

Example startup check:
```
Configuration loaded.  ✓ All required env vars present
Connecting to Notion...  ✓ API key valid
Connecting to Claude...  ✓ API key valid
```

---

## Security Notes

- **Never commit `.env` to git** — it contains secrets
- **`.env.example` is committed** — it has placeholder values only
- **Rotate your keys periodically** if exposed (delete old key, create new one)
- **Use `.env.local` for local overrides** — add to `.gitignore`

<!-- END AUTO-GENERATED -->
