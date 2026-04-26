import logging
from datetime import date, datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import calendar_client, planner, storage

logger = logging.getLogger(__name__)


# ─── helpers ──────────────────────────────────────────────────────────────────


def today() -> str:
    return date.today().isoformat()


def _authorized(update: Update) -> bool:
    """Return True if the message comes from the registered user."""
    registered = storage.get_setting("chat_id")
    if registered is None:
        return True  # not registered yet — allow first contact
    return str(update.effective_chat.id) == registered


def _task_list_html(tasks: list[dict]) -> str:
    if not tasks:
        return "No tasks yet. Use /plan to generate or /add to create one."
    icons = {"pending": "🔲", "done": "✅", "skipped": "⏩"}
    lines = [f"{icons.get(t['status'], '🔲')} {t['number']}. {t['description']}" for t in tasks]
    return "\n".join(lines)


def _calendar_html(events: list[dict]) -> str:
    if not events:
        return ""
    lines = [f"• {e['time']} — <b>{e['title']}</b>" for e in events]
    return "📅 <b>Calendar:</b>\n" + "\n".join(lines) + "\n\n"


# ─── /start ───────────────────────────────────────────────────────────────────


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    registered = storage.get_setting("chat_id")

    if registered is None:
        storage.set_setting("chat_id", chat_id)
        await update.message.reply_text(
            f"✅ Registered. Chat ID: <code>{chat_id}</code>\n\n"
            "<b>Daily Planner</b> ready.\n\n"
            "/plan — Generate today's task list\n"
            "/add [task] — Add a task\n"
            "/done [#] — Mark complete\n"
            "/skip [#] — Skip task\n"
            "/review — End-of-day summary\n"
            "/week — This week's calendar\n"
            "/settime [morning|evening] [HH:MM] — Set briefings\n"
            "/timezone [tz] — Set timezone (e.g. America/New_York)",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            "<b>Daily Planner</b>\n\n"
            "/plan — Today's tasks\n"
            "/add [task] — Add task\n"
            "/done [#] — Mark done\n"
            "/skip [#] — Skip\n"
            "/review — Day summary\n"
            "/week — Week view",
            parse_mode=ParseMode.HTML,
        )


# ─── /plan ────────────────────────────────────────────────────────────────────


async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    tz = storage.get_setting("timezone", "UTC")
    date_str = today()

    await update.message.reply_text("⏳ Building your plan…")

    events = calendar_client.get_today_events(tz)
    existing = storage.get_tasks(date_str)

    # Regenerate if forced (--refresh arg) or no tasks exist yet
    force = context.args and context.args[0] == "--refresh"
    if not existing or force:
        user_task_descs = [t["description"] for t in existing] if existing else []
        planned = planner.generate_daily_plan(events, user_task_descs)
        if planned:
            storage.bulk_add_tasks(date_str, planned)

    tasks = storage.get_tasks(date_str)
    cal_text = _calendar_html(events)
    task_text = _task_list_html(tasks)

    hint = ""
    if not calendar_client.is_calendar_configured():
        hint = "\n\n<i>💡 Connect Google Calendar for conflict detection — see README.</i>"

    await update.message.reply_text(
        f"{cal_text}<b>📋 Today's Plan:</b>\n{task_text}{hint}",
        parse_mode=ParseMode.HTML,
    )


# ─── /add ─────────────────────────────────────────────────────────────────────


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    if not context.args:
        await update.message.reply_text("Usage: /add [task description]")
        return

    description = " ".join(context.args)
    date_str = today()
    number = storage.add_task(date_str, description)

    await update.message.reply_text(
        f"🔲 {number}. {description}\n<i>Added.</i>",
        parse_mode=ParseMode.HTML,
    )


# ─── /done ────────────────────────────────────────────────────────────────────


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /done [task number]")
        return

    number = int(context.args[0])
    date_str = today()
    task = storage.get_task(date_str, number)

    if not task:
        await update.message.reply_text(f"Task {number} not found.")
        return

    storage.update_task_status(date_str, number, "done")
    await update.message.reply_text(
        f"✅ {number}. {task['description']}\n<i>Marked complete.</i>",
        parse_mode=ParseMode.HTML,
    )


# ─── /skip ────────────────────────────────────────────────────────────────────


async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /skip [task number]")
        return

    number = int(context.args[0])
    date_str = today()
    task = storage.get_task(date_str, number)

    if not task:
        await update.message.reply_text(f"Task {number} not found.")
        return

    storage.update_task_status(date_str, number, "skipped")
    await update.message.reply_text(
        f"⏩ {number}. {task['description']}\n<i>Skipped.</i>",
        parse_mode=ParseMode.HTML,
    )


# ─── /review ──────────────────────────────────────────────────────────────────


async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    date_str = today()
    tasks = storage.get_tasks(date_str)

    if not tasks:
        await update.message.reply_text("No tasks for today. Use /plan to get started.")
        return

    await update.message.reply_text("⏳ Generating summary…")

    completed = [t["description"] for t in tasks if t["status"] == "done"]
    skipped = [t["description"] for t in tasks if t["status"] == "skipped"]
    pending = [t["description"] for t in tasks if t["status"] == "pending"]

    summary = planner.generate_evening_summary(completed, skipped, pending)
    storage.save_daily_log(date_str, summary, len(completed), len(skipped), len(pending))

    task_text = _task_list_html(tasks)
    await update.message.reply_text(
        f"<b>📊 Daily Review:</b>\n{task_text}\n\n<i>{summary}</i>",
        parse_mode=ParseMode.HTML,
    )


# ─── /week ────────────────────────────────────────────────────────────────────


async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    if not calendar_client.is_calendar_configured():
        await update.message.reply_text(
            "Google Calendar not connected.\nSee the README to set up calendar integration."
        )
        return

    tz = storage.get_setting("timezone", "UTC")
    events_by_day = calendar_client.get_week_events(tz)

    if not events_by_day:
        await update.message.reply_text("No events this week.")
        return

    lines = ["<b>📅 This Week:</b>"]
    for day_key in sorted(events_by_day):
        day_label = datetime.strptime(day_key, "%Y-%m-%d").strftime("%a %b %d")
        lines.append(f"\n<b>{day_label}</b>")
        for e in events_by_day[day_key]:
            lines.append(f"• {e['time']} — {e['title']}")

    # Telegram messages have a 4096 char limit
    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n<i>…truncated</i>"

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ─── /settime ─────────────────────────────────────────────────────────────────


async def settime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    if len(context.args) < 2:
        morning = storage.get_setting("morning_time", "08:00")
        evening = storage.get_setting("evening_time", "20:00")
        await update.message.reply_text(
            f"Current: morning={morning}, evening={evening}\n"
            "Usage: /settime [morning|evening] [HH:MM]"
        )
        return

    period = context.args[0].lower()
    time_str = context.args[1]

    if period not in ("morning", "evening"):
        await update.message.reply_text("Period must be 'morning' or 'evening'.")
        return

    # Validate time format
    try:
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        await update.message.reply_text("Invalid time format. Use HH:MM (e.g. 08:30).")
        return

    storage.set_setting(f"{period}_time", time_str)

    # Trigger scheduler to reload
    if context.bot_data.get("reschedule_callback"):
        await context.bot_data["reschedule_callback"]()

    await update.message.reply_text(
        f"✅ {period.capitalize()} briefing set to <b>{time_str}</b>.",
        parse_mode=ParseMode.HTML,
    )


# ─── /timezone ────────────────────────────────────────────────────────────────


async def timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    if not context.args:
        tz = storage.get_setting("timezone", "UTC")
        await update.message.reply_text(
            f"Current timezone: <code>{tz}</code>\n"
            "Usage: /timezone [timezone]\n"
            "Example: /timezone America/New_York",
            parse_mode=ParseMode.HTML,
        )
        return

    tz_str = context.args[0]
    try:
        import pytz
        pytz.timezone(tz_str)
    except Exception:
        await update.message.reply_text(
            f"Invalid timezone: <code>{tz_str}</code>\n"
            "Find yours at: en.wikipedia.org/wiki/List_of_tz_database_time_zones",
            parse_mode=ParseMode.HTML,
        )
        return

    storage.set_setting("timezone", tz_str)
    await update.message.reply_text(
        f"✅ Timezone set to <code>{tz_str}</code>.",
        parse_mode=ParseMode.HTML,
    )


# ─── unknown commands ─────────────────────────────────────────────────────────


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    await update.message.reply_text(
        "Unknown command. Use /start to see available commands."
    )


# ─── application factory ──────────────────────────────────────────────────────


def create_application(token: str) -> Application:
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("plan", plan_command))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("skip", skip_command))
    app.add_handler(CommandHandler("review", review_command))
    app.add_handler(CommandHandler("week", week_command))
    app.add_handler(CommandHandler("settime", settime_command))
    app.add_handler(CommandHandler("timezone", timezone_command))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    return app
