import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from db.database import init_db
from bot.handlers import (
    cmd_start,
    cmd_track,
    cmd_pipeline,
    cmd_prep,
    cmd_quiz,
    handle_url,
)
from bot.scheduler import build_scheduler

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in .env")

    init_db()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("track", cmd_track))
    app.add_handler(CommandHandler("pipeline", cmd_pipeline))
    app.add_handler(CommandHandler("prep", cmd_prep))
    app.add_handler(CommandHandler("quiz", cmd_quiz))

    # URL paste handler — matches any text message containing a URL
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://"), handle_url))

    # Scheduler — needs chat_id to push proactive alerts
    # Read CHAT_ID from env (user gets this by messaging the bot once)
    import os
    chat_id_str = os.getenv("TELEGRAM_CHAT_ID")
    if chat_id_str:
        chat_id = int(chat_id_str)
        scheduler = build_scheduler(bot=app.bot, chat_id=chat_id)

        async def on_startup(application):
            scheduler.start()
            logger.info(f"[Scheduler] Started. RSS poll every 3h. Chat ID: {chat_id}")

        async def on_shutdown(application):
            scheduler.shutdown(wait=False)
            logger.info("[Scheduler] Stopped.")

        app.post_init = on_startup
        app.post_shutdown = on_shutdown
    else:
        logger.warning(
            "TELEGRAM_CHAT_ID not set — proactive RSS alerts disabled. "
            "Message your bot, then add your chat ID to .env."
        )

    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
