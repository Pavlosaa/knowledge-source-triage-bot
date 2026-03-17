# Operations Runbook

This document covers production deployment, systemd service management, logging, troubleshooting, and manual prerequisites for the AI Knowledge Source Triage Bot.

**Last Updated:** 2026-03-17

---

## Quick Reference

**Service management:**
```bash
sudo systemctl start triage-bot       # Start
sudo systemctl stop triage-bot        # Stop
sudo systemctl restart triage-bot     # Restart
sudo systemctl status triage-bot      # Status
```

**Logs:**
```bash
journalctl -u triage-bot -f           # Live tail (systemd)
tail -f logs/bot.log                  # Application log (if running directly)
tail -f logs/errors.log               # Error log only
```

---

## Deployment to Oracle Cloud (systemd)

### Prerequisites

Before deploying, ensure you have completed these manual setup steps:

#### 1. Create Telegram Bot (@BotFather)

1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Follow prompts to create a new bot
4. BotFather will return:
   ```
   Congratulations on your new bot. You will find it at
   t.me/your_bot_name. You can now add a description, about
   section and profile picture for your bot, see /help for a list
   of commands.

   Use this token to access the HTTP API:
   123456:ABCDefGHIJKLMN...
   ```
5. Save the token as `TELEGRAM_BOT_TOKEN`

#### 2. Create & Setup Telegram Group

1. Create a new private group in Telegram
2. Add your bot to the group (search for your bot name, add it)
3. Make sure the bot is an admin (so it can send messages)
4. Get the group ID:
   - **Desktop:** Right-click group → "Copy Invite Link", extract ID, prepend `-100`
   - **Via API:** Send a test message in the group, then:
     ```bash
     curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates" | grep chat_id
     ```
5. Save the ID as `TELEGRAM_GROUP_ID` (should be negative, e.g., `-100123456789`)

#### 3. Setup Notion Database

1. Go to https://www.notion.so and log in
2. Navigate to your R&D Resources page
3. Copy the page ID from the URL:
   ```
   https://notion.so/MY_WORKSPACE/PageTitle-<PAGE_ID>?...
   ```
   Save as `NOTION_RND_PAGE_ID`

4. Similarly, find your Projects page and copy its ID
   Save as `NOTION_PROJECTS_PAGE_ID`

5. Create a Notion integration:
   - Go to https://www.notion.so/my-integrations
   - Click "Create new integration"
   - Give it a name (e.g., "AI Triage Bot")
   - Copy the API key (starts with `secret_`)
   - Save as `NOTION_API_KEY`

6. Share pages with the integration:
   - Go to your R&D Resources page
   - Click `...` (top right) → "Add connections"
   - Select your integration
   - Repeat for Projects page

#### 4. Get Claude API Key

1. Go to https://console.anthropic.com
2. Click "API keys" in the left sidebar
3. Click "Create Key"
4. Copy the key (starts with `sk-ant-`)
5. Save as `ANTHROPIC_API_KEY`

#### 5. (Optional) Get ScrapFly API Key for X.com Support

X.com URLs are supported optionally via ScrapFly:

1. Go to https://scrapfly.io
2. Sign up for a free account (1000 requests/month included)
3. Copy your API key from the dashboard
4. Save as `SCRAPFLY_API_KEY`

**Without ScrapFly:** Bot gracefully skips X.com URLs. GitHub and article URLs work fine.
**With ScrapFly:** Full support for tweet/article fetching with automatic IP rotation and JavaScript rendering.

#### 6. (Optional) Get GitHub Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `public_repo`
4. Copy and save as `GITHUB_TOKEN`

---

<!-- AUTO-GENERATED: Deployment Steps -->

### Step 1: Prepare Server

SSH into your Oracle Cloud instance:

```bash
ssh ubuntu@<YOUR_SERVER_IP>
```

Update system packages:

```bash
sudo apt update
sudo apt upgrade -y
```

Install Python 3.12 and dependencies:

```bash
sudo apt install -y python3.12 python3.12-venv python3-pip git
```

Verify:

```bash
python3.12 --version
```

### Step 2: Clone Repository

```bash
cd /home/ubuntu
git clone https://github.com/Pavlosaa/knowledge-source-triage-bot.git
cd knowledge-source-triage-bot
```

### Step 3: Setup Virtual Environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### Step 4: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
```

### Step 5: Configure Environment

```bash
cp .env.example .env
nano .env  # Edit with your values from manual prerequisites above
```

Required values:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_GROUP_ID`
- `ANTHROPIC_API_KEY`
- `NOTION_API_KEY`, `NOTION_RND_PAGE_ID`, `NOTION_PROJECTS_PAGE_ID`

Optional:
- `SCRAPFLY_API_KEY` — for X.com tweet/article support
- `GITHUB_TOKEN` — to increase API rate limits

Save with `Ctrl+X`, then `Y`, then `Enter` (if using nano).

### Step 6: Test Locally (Optional)

```bash
python main.py
```

Expected output:
```
2026-03-02 14:23:45 | INFO | Configuration loaded.
2026-03-02 14:23:46 | INFO | Bot started. Listening for messages...
```

If you see errors, fix them now before continuing. Press `Ctrl+C` to stop.

### Step 7: Install systemd Service

```bash
sudo cp systemd/triage-bot.service /etc/systemd/system/
```

Verify the service file:

```bash
sudo cat /etc/systemd/system/triage-bot.service
```

It should show:
```ini
[Unit]
Description=AI Knowledge Source Triage Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/knowledge-source-triage-bot
ExecStart=/home/ubuntu/knowledge-source-triage-bot/.venv/bin/python main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Step 8: Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable triage-bot
sudo systemctl start triage-bot
```

### Step 9: Verify Service is Running

```bash
sudo systemctl status triage-bot
```

Expected output (snippet):
```
● triage-bot.service - AI Knowledge Source Triage Bot
     Loaded: loaded (/etc/systemd/system/triage-bot.service; enabled; vendor preset: enabled)
     Active: active (running) since Mon 2026-03-02 14:30:00 UTC; 10s ago
   Main PID: 1234 (python)
      Tasks: 5
     Memory: 123.4M
```

### Step 10: Test the Bot

1. Open Telegram and go to your configured group
2. Share a test link (e.g., `https://x.com/elonmusk/status/123456`)
3. Bot should acknowledge the message
4. Check systemd logs (next section)

<!-- END AUTO-GENERATED: Deployment Steps -->

---

## Managing the Service

### Start the Service

```bash
sudo systemctl start triage-bot
```

### Stop the Service

```bash
sudo systemctl stop triage-bot
```

### Restart the Service

Use this after updating code or configuration:

```bash
sudo systemctl restart triage-bot
```

### Check Service Status

```bash
sudo systemctl status triage-bot
```

Output:
```
● triage-bot.service - AI Knowledge Source Triage Bot
     Loaded: loaded (/etc/systemd/system/triage-bot.service; enabled; ...)
     Active: active (running) since Mon 2026-03-02 14:30:00 UTC; 2min 5s ago
   Main PID: 12345 (python)
```

### Disable Service (so it doesn't auto-start)

```bash
sudo systemctl disable triage-bot
```

Then:

```bash
sudo systemctl status triage-bot
```

Output:
```
● triage-bot.service - AI Knowledge Source Triage Bot
     Loaded: loaded (/etc/systemd/system/triage-bot.service; disabled; ...)
     Active: inactive (dead)
```

---

## Viewing Logs

### Live Tail (systemd)

```bash
sudo journalctl -u triage-bot -f
```

Press `Ctrl+C` to exit.

Example output:
```
Mar 02 14:30:00 oracle-ubuntu python[12345]: 2026-03-02 14:30:00 | INFO | Configuration loaded.
Mar 02 14:30:01 oracle-ubuntu python[12345]: 2026-03-02 14:30:01 | INFO | Bot started. Listening for messages...
Mar 02 14:30:15 oracle-ubuntu python[12345]: 2026-03-02 14:30:15 | INFO | Message received: https://x.com/...
```

### Recent Logs (Last N Lines)

```bash
sudo journalctl -u triage-bot -n 50  # Last 50 lines
```

### Logs Since Last Restart

```bash
sudo journalctl -u triage-bot --since "1 hour ago"
```

### Error-Only Logs

```bash
sudo journalctl -u triage-bot -p err
```

### Local Logs (if running directly)

If you're running the bot with `python main.py` (not systemd), logs go to:

```bash
tail -f logs/bot.log        # All events
tail -f logs/errors.log     # Errors only
```

---

## Common Issues & Fixes

### Issue: Service fails to start

Check the logs:
```bash
sudo journalctl -u triage-bot -p err
```

Common causes:

| Error | Fix |
|-------|-----|
| `Module not found: bot` | Virtual environment path wrong in .service file. Check `ExecStart` path. |
| `FileNotFoundError: /home/ubuntu/knowledge-source-triage-bot` | Working directory doesn't exist. Check `WorkingDirectory` in .service file. |
| `Missing required env var: TELEGRAM_BOT_TOKEN` | `.env` file missing or incomplete. Copy `.env.example` and fill in values. |

### Issue: Bot receives messages but doesn't respond

Check logs:
```bash
sudo journalctl -u triage-bot -f
```

Common causes:

| Symptom | Cause | Fix |
|---------|-------|-----|
| `"Configuration loaded"` then no messages | Bot not listening to correct group | Verify `TELEGRAM_GROUP_ID` in `.env` matches your group. Get correct ID from BotFather. |
| Message logged but no Notion page created | Pipeline not implemented yet | This is expected — fetchers and pipeline are TODO. Check `tasks/todo.md`. |
| `Notion API error: invalid_page_id` | `NOTION_RND_PAGE_ID` wrong | Get correct ID from https://www.notion.so, copy from URL. |

### Issue: X.com content not fetching

**Default behavior (no ScrapFly key):** X.com URLs are gracefully skipped with a user-friendly error message. Bot continues processing other URLs normally.

**With ScrapFly enabled (SCRAPFLY_API_KEY set):** Check if API key is valid and has requests available.

Check logs:
```bash
sudo journalctl -u triage-bot | grep -i "twitter\|scrapfly"
```

Common causes and fixes:

| Symptom | Cause | Fix |
|---------|-------|-----|
| Bot skips X.com URLs silently | `SCRAPFLY_API_KEY` not set | Set the env var to enable X.com support, or leave unset (default) |
| `ScrapFly API error: invalid key` | API key wrong or expired | Verify key in `.env` at https://scrapfly.io/dashboard |
| `ScrapFly returned 402` | Monthly request quota exceeded | Upgrade plan or wait for reset |
| `ScrapFly returned 422` or `Invalid URL` | Malformed X.com URL | Must be `https://x.com/user/status/ID` or `https://x.com/i/article/...` |

### Issue: Claude API errors

Check logs:
```bash
sudo journalctl -u triage-bot | grep -i claude
```

Common causes:

| Error | Fix |
|-------|-----|
| `invalid_api_key` | Check `ANTHROPIC_API_KEY` in `.env`. Get new key from https://console.anthropic.com |
| `rate_limit_error` | Rate limited (default: 2 req/min). Space out requests or wait. |
| `unknown_model: claude-opus-4.6` | Model name wrong in prompts.py. Should be `claude-opus-4-6`. |

### Issue: Notion pages not created

Check logs:
```bash
sudo journalctl -u triage-bot | grep -i notion
```

Common causes:

| Error | Fix |
|-------|-------|
| `invalid_grant: unauthorized` | `NOTION_API_KEY` wrong or integration not shared with page. Re-create integration and share pages. |
| `object_not_found` | `NOTION_RND_PAGE_ID` wrong. Copy correct ID from Notion URL. |
| `invalid_database` | Database doesn't exist yet. It auto-creates on first successful analysis. |

---

## Updates & Code Changes

### CI/CD Auto-Deploy (preferred)

Push to `main` triggers GitHub Actions CI pipeline. After all checks pass (lint, typecheck, test, security), the deploy workflow SSHs to Oracle Cloud and runs:

```bash
cd ~/knowledge-source-triage-bot
git pull origin main
pip install -r requirements.txt
sudo systemctl restart triage-bot.service
```

**Required GitHub Secrets:** `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`

### Manual Deploy

If CI/CD is not configured or you need to deploy manually:

```bash
cd /home/ubuntu/knowledge-source-triage-bot
git pull origin main
```

### Reinstall Dependencies (if requirements.txt changed)

```bash
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### Restart Service

```bash
sudo systemctl restart triage-bot
```

### Verify Update

```bash
sudo journalctl -u triage-bot -f
# Should show "Bot started. Listening for messages..."
```

---

## Monitoring Health

### Check if Service Crashed

```bash
sudo systemctl is-active triage-bot
```

Output: `active` (good) or `inactive` (bad)

If inactive, restart it:
```bash
sudo systemctl start triage-bot
```

### Watch for Errors

```bash
sudo journalctl -u triage-bot -p err -f
```

This will show only errors in real-time. Good to run in a monitoring window.

### Check Resource Usage

```bash
ps aux | grep "[p]ython main.py"
```

Example output:
```
ubuntu  12345  0.5  2.1  234000  45000 ?  Sl  14:30  0:15 /home/ubuntu/.../.venv/bin/python main.py
```

Columns:
- `%CPU` — CPU usage (0.5% = good)
- `%MEM` — Memory usage (2.1% of 12GB = ~250MB, acceptable)
- `RSS` — Resident set (45MB, good)

---

## Backup & Recovery

### Backup .env

Your `.env` file contains secrets. Back it up securely:

```bash
sudo cp /home/ubuntu/knowledge-source-triage-bot/.env ~/backup/.env.backup
sudo chmod 600 ~/backup/.env.backup
```

### Restore from Backup

```bash
sudo cp ~/backup/.env.backup /home/ubuntu/knowledge-source-triage-bot/.env
sudo systemctl restart triage-bot
```

---

## Troubleshooting Workflow

1. **Check service status:**
   ```bash
   sudo systemctl status triage-bot
   ```

2. **Review recent logs:**
   ```bash
   sudo journalctl -u triage-bot -n 100
   ```

3. **Search for specific errors:**
   ```bash
   sudo journalctl -u triage-bot | grep -i "error\|exception\|failed"
   ```

4. **Test configuration:**
   ```bash
   cd /home/ubuntu/knowledge-source-triage-bot
   source .venv/bin/activate
   python -c "from bot.config import load_config; load_config()"
   ```
   Should print no errors.

5. **Restart service:**
   ```bash
   sudo systemctl restart triage-bot
   ```

6. **Watch for new errors:**
   ```bash
   sudo journalctl -u triage-bot -f
   ```

---

## Support

**For setup issues:** See `docs/ENV.md` and `docs/CONTRIBUTING.md`

**For design questions:** Read `docs/CODEMAPS/INDEX.md` and `docs/plans/2026-03-01-ai-knowledge-triage-design.md`

**For code issues:** Check application logs in `logs/` or systemd logs

Good luck!
