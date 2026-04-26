# Personal Daily Planner — Telegram Bot

A Telegram bot powered by Google Gemini AI (free tier) that generates prioritized daily task lists, integrates with Google Calendar, and sends scheduled morning/evening briefings.

---

## Features

- **AI-generated task plans** — Gemini analyzes your calendar events and creates a prioritized task list each morning
- **Google Calendar integration** — fetches today's and this week's events; flags tasks that may conflict with meetings
- **Morning & evening briefings** — automated messages at configurable times via APScheduler
- **Task management** — add, complete, and skip tasks via Telegram commands
- **End-of-day summaries** — Gemini writes a short reflection on what you accomplished
- **Persistent storage** — tasks and settings survive restarts (SQLite)
- **Single-user security** — the bot only responds to the registered chat ID

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | Earlier versions untested |
| Telegram account | [telegram.org](https://telegram.org) |
| Google Gemini API key | Free at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) |
| Google Cloud account | Only needed for calendar integration |

---

## Quick Start

### 1. Clone and install

```bash
git clone <your-repo-url>
cd personal-daily-plan-agent
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Create a Telegram bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the token (looks like `123456:ABC-DEF1234...`)

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=          # optional — set automatically on first /start
GEMINI_API_KEY=AIza...
```

**How to find your chat ID:** Leave `TELEGRAM_CHAT_ID` blank. Start the bot (step 4), send `/start` to your bot in Telegram, and the bot will register your chat ID automatically.

### 4. Run the bot

```bash
python main.py
```

### 5. Send `/start` to your bot in Telegram

The bot will register your chat ID and display the available commands.

### 6. Generate your first plan

Send `/plan` to generate today's task list.

---

## Google Calendar Integration

This step is optional. Without it, the bot works fully — it just won't fetch calendar events.

### Step 1 — Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click **Select a project** → **New Project**
3. Give it a name (e.g., `daily-planner`) and click **Create**

### Step 2 — Enable the Google Calendar API

1. In your project, go to **APIs & Services → Library**
2. Search for **Google Calendar API**
3. Click it and press **Enable**

### Step 3 — Create OAuth 2.0 credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. If prompted, configure the OAuth consent screen first:
   - User type: **External**
   - Fill in app name and your email; save
   - Under **Scopes**, add `https://www.googleapis.com/auth/calendar.readonly`
   - Add your Google account email under **Test users**
4. Back in Credentials, create the OAuth client:
   - Application type: **Desktop App**
   - Name it anything (e.g., `DailyPlannerBot`)
5. Click **Download JSON** — save this file as `credentials.json` in the project root

### Step 4 — Authorize the bot

Run the one-time setup script **on a machine with a browser** (your laptop, not a headless server):

```bash
python setup_calendar.py
```

This opens a browser window asking you to sign in with Google and grant read-only calendar access. After approval, a `token.json` file is created in the project root. The bot uses this file automatically — no repeated logins needed (the token auto-refreshes).

### Step 5 — Verify

Restart the bot and send `/week`. You should see your upcoming calendar events.

> **Running on a headless server?** Run `setup_calendar.py` locally first, then copy `token.json` to the server alongside the bot.

---

## Commands Reference

| Command | Description |
|---|---|
| `/start` | Register your chat ID and display the command list |
| `/plan` | Generate (or display) today's prioritized task list |
| `/plan --refresh` | Force Gemini to regenerate the task list |
| `/add [description]` | Add a new task for today |
| `/done [#]` | Mark task number `#` as complete ✅ |
| `/skip [#]` | Mark task number `#` as skipped ⏩ |
| `/review` | Generate an end-of-day summary with Gemini |
| `/week` | Show this week's Google Calendar events |
| `/settime [morning\|evening] [HH:MM]` | Change the briefing time |
| `/timezone [tz]` | Set your timezone (e.g. `America/New_York`) |

### Examples

```
/add Submit expense report
/done 3
/skip 7
/settime morning 07:30
/timezone Europe/London
```

---

## Scheduled Briefings

The bot sends two automatic messages each day:

| Briefing | Default time | Contents |
|---|---|---|
| Morning | 08:00 | Calendar events + AI-generated task plan |
| Evening | 20:00 | Task status summary + Gemini's end-of-day reflection |

Change the times at any time with `/settime`:

```
/settime morning 07:00
/settime evening 21:30
```

Times are stored in the database and survive restarts. The scheduler reloads immediately — no restart needed.

---

## Configuration

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | Token from BotFather |
| `GEMINI_API_KEY` | Yes | Google Gemini API key (free) |
| `TELEGRAM_CHAT_ID` | No | Pre-register your chat ID (otherwise set via `/start`) |
| `GOOGLE_CREDENTIALS_FILE` | No | Path to OAuth credentials JSON (default: `credentials.json`) |

### Bot settings (stored in SQLite)

| Setting | Default | Changed via |
|---|---|---|
| `chat_id` | — | `/start` |
| `timezone` | `UTC` | `/timezone` |
| `morning_time` | `08:00` | `/settime morning` |
| `evening_time` | `20:00` | `/settime evening` |

### Timezone names

Use IANA timezone database names. Common examples:

| Region | Timezone |
|---|---|
| US Eastern | `America/New_York` |
| US Pacific | `America/Los_Angeles` |
| UK | `Europe/London` |
| Central Europe | `Europe/Berlin` |
| India | `Asia/Kolkata` |
| Japan | `Asia/Tokyo` |
| Australia (Sydney) | `Australia/Sydney` |

Full list: [en.wikipedia.org/wiki/List_of_tz_database_time_zones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

---

## Project Structure

```
personal-daily-plan-agent/
├── main.py                 # Entry point — starts the bot
├── setup_calendar.py       # One-time Google OAuth setup
├── requirements.txt
├── .env                    # Your secrets (not committed)
├── .env.example            # Template
├── credentials.json        # Google OAuth client credentials (not committed)
├── token.json              # Google OAuth token, auto-created (not committed)
├── planner.db              # SQLite database, auto-created
└── src/
    ├── __init__.py
    ├── bot.py              # Telegram command handlers
    ├── calendar_client.py  # Google Calendar API client
    ├── planner.py          # Gemini AI integration
    ├── scheduler.py        # APScheduler morning/evening jobs
    └── storage.py          # SQLite persistence layer
```

---

## Running as a Background Service

### Option A — systemd (Linux servers)

Create `/etc/systemd/system/daily-planner.service`:

```ini
[Unit]
Description=Personal Daily Planner Telegram Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/personal-daily-plan-agent
ExecStart=/path/to/personal-daily-plan-agent/.venv/bin/python main.py
Restart=always
RestartSec=10
EnvironmentFile=/path/to/personal-daily-plan-agent/.env

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable daily-planner
sudo systemctl start daily-planner
sudo systemctl status daily-planner
```

View logs:

```bash
journalctl -u daily-planner -f
```

### Option B — nohup (quick and dirty)

```bash
nohup python main.py > bot.log 2>&1 &
echo $! > bot.pid          # save PID to stop it later
```

Stop it:

```bash
kill $(cat bot.pid)
```

### Option C — screen / tmux

```bash
screen -S daily-planner
python main.py
# Detach: Ctrl+A, D
# Reattach: screen -r daily-planner
```

---

## Security Notes

- **Single-user bot** — the bot only responds to the chat ID registered via `/start`. Anyone else who messages the bot receives no response.
- **Keep `.env` private** — never commit it to version control. The `.gitignore` should exclude it.
- **Keep `credentials.json` and `token.json` private** — these grant read access to your Google Calendar.
- **Principle of least privilege** — the Google Calendar scope is `calendar.readonly`; the bot cannot modify your calendar.
- **Gemini API key** — treat it like a password. Rotate it immediately if exposed.

---

## Troubleshooting

### Bot doesn't respond

- Check that `TELEGRAM_BOT_TOKEN` is correct
- Ensure the bot is running (`python main.py` shows no errors)
- Make sure you sent `/start` first so your chat ID is registered
- Confirm you're messaging the right bot username

### "TELEGRAM_BOT_TOKEN is not set"

Your `.env` file is missing or not being loaded. Ensure `.env` exists in the project root and contains the token.

### Google Calendar not working

- Confirm `credentials.json` is in the project root
- Run `python setup_calendar.py` — if it says the token is valid, the issue is elsewhere
- Check that the Google Calendar API is enabled in your Cloud project
- Ensure your Google account is listed as a test user on the OAuth consent screen
- Delete `token.json` and re-run `setup_calendar.py` to force re-authorization

### Scheduled briefings not arriving

- Verify your timezone is set correctly: `/timezone` shows the current value
- Check that the bot process is still running
- Confirm morning/evening times with `/settime` (no arguments shows current values)
- Check the bot logs for APScheduler errors

### "No tasks generated" in morning briefing

- Send `/plan` manually to test plan generation
- Check that `GEMINI_API_KEY` is valid and not expired
- Look for error messages in the bot logs (`logging.ERROR` entries)

### Tasks duplicated after `/plan`

- Use `/plan --refresh` only when you want to regenerate; plain `/plan` reuses existing tasks

---

## AI Model

This bot uses **Google Gemini 1.5 Flash** (`gemini-1.5-flash`) — a free model via Google AI Studio — for:

- Generating prioritized daily task lists from your calendar events and goals
- Writing end-of-day summaries that reflect on completed, skipped, and pending tasks

Get your free API key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey). The free tier allows up to 15 requests per minute and 1 million tokens per day — more than enough for a personal planner.

---

## License

MIT — do whatever you want with this.
