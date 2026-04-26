import logging
from datetime import date

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from telegram.constants import ParseMode

from . import calendar_client, planner, storage

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler()


async def _send_morning_briefing(bot: Bot, chat_id: int):
    date_str = date.today().isoformat()
    tz = storage.get_setting("timezone", "UTC")

    logger.info("Sending morning briefing to %s", chat_id)
    events = calendar_client.get_today_events(tz)
    planned = planner.generate_daily_plan(events, [])

    if planned:
        storage.bulk_add_tasks(date_str, planned)

    tasks = storage.get_tasks(date_str)
    status_icons = {"pending": "🔲", "done": "✅", "skipped": "⏩"}

    cal_text = ""
    if events:
        cal_lines = [f"• {e['time']} — <b>{e['title']}</b>" for e in events]
        cal_text = "📅 <b>Calendar:</b>\n" + "\n".join(cal_lines) + "\n\n"

    task_lines = [
        f"{status_icons.get(t['status'], '🔲')} {t['number']}. {t['description']}"
        for t in tasks
    ]
    task_text = "\n".join(task_lines) if task_lines else "No tasks generated."

    await bot.send_message(
        chat_id=chat_id,
        text=f"Good morning! ☀️\n\n{cal_text}<b>📋 Today's Plan:</b>\n{task_text}",
        parse_mode=ParseMode.HTML,
    )


async def _send_evening_briefing(bot: Bot, chat_id: int):
    date_str = date.today().isoformat()
    tasks = storage.get_tasks(date_str)

    if not tasks:
        logger.info("No tasks for evening briefing — skipping")
        return

    logger.info("Sending evening briefing to %s", chat_id)

    completed = [t["description"] for t in tasks if t["status"] == "done"]
    skipped = [t["description"] for t in tasks if t["status"] == "skipped"]
    pending = [t["description"] for t in tasks if t["status"] == "pending"]

    summary = planner.generate_evening_summary(completed, skipped, pending)
    storage.save_daily_log(date_str, summary, len(completed), len(skipped), len(pending))

    status_icons = {"pending": "🔲", "done": "✅", "skipped": "⏩"}
    task_lines = [
        f"{status_icons.get(t['status'], '🔲')} {t['number']}. {t['description']}"
        for t in tasks
    ]
    task_text = "\n".join(task_lines)

    await bot.send_message(
        chat_id=chat_id,
        text=f"Evening check-in 🌙\n\n{task_text}\n\n<i>{summary}</i>",
        parse_mode=ParseMode.HTML,
    )


def setup_scheduler(bot: Bot, chat_id: int):
    """Configure and start the APScheduler with morning and evening jobs."""
    _reschedule(bot, chat_id)
    if not _scheduler.running:
        _scheduler.start()
        logger.info("Scheduler started")


def _reschedule(bot: Bot, chat_id: int):
    """(Re)schedule morning and evening briefings based on current settings."""
    tz_str = storage.get_setting("timezone", "UTC")
    morning = storage.get_setting("morning_time", "08:00")
    evening = storage.get_setting("evening_time", "20:00")

    morning_h, morning_m = map(int, morning.split(":"))
    evening_h, evening_m = map(int, evening.split(":"))

    tz = pytz.timezone(tz_str)

    for job_id in ("morning_briefing", "evening_briefing"):
        existing = _scheduler.get_job(job_id)
        if existing:
            existing.remove()

    _scheduler.add_job(
        _send_morning_briefing,
        CronTrigger(hour=morning_h, minute=morning_m, timezone=tz),
        args=[bot, chat_id],
        id="morning_briefing",
        replace_existing=True,
    )

    _scheduler.add_job(
        _send_evening_briefing,
        CronTrigger(hour=evening_h, minute=evening_m, timezone=tz),
        args=[bot, chat_id],
        id="evening_briefing",
        replace_existing=True,
    )

    logger.info(
        "Scheduled: morning=%s, evening=%s, tz=%s", morning, evening, tz_str
    )


async def reschedule_from_settings(bot: Bot, chat_id: int):
    """Async wrapper called after settings change to reload jobs."""
    _reschedule(bot, chat_id)
