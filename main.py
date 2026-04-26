"""
Entry point for the Daily Planner Telegram Bot.
"""
import logging
import os

from dotenv import load_dotenv
from telegram.ext import Application

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    from src import storage
    from src.bot import create_application
    from src.scheduler import reschedule_from_settings, setup_scheduler

    storage.init_db()

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set. Check your .env file.")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Check your .env file.")

    app = create_application(token)

    chat_id_str = os.environ.get("TELEGRAM_CHAT_ID") or storage.get_setting("chat_id")

    async def post_init(application: Application) -> None:
        cid = os.environ.get("TELEGRAM_CHAT_ID") or storage.get_setting("chat_id")
        if cid:
            setup_scheduler(application.bot, int(cid))

            async def reschedule():
                await reschedule_from_settings(application.bot, int(cid))

            application.bot_data["reschedule_callback"] = reschedule
            logger.info("Scheduler initialized for chat_id=%s", cid)
        else:
            logger.info(
                "No TELEGRAM_CHAT_ID set. Send /start to the bot to register your chat ID."
            )

    app.post_init = post_init

    logger.info("Starting bot (polling mode)…")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
