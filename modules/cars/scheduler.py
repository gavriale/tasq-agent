import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from telegram import Bot

from core.config import POLL_INTERVAL_HOURS
from core.db.database import is_car_seen, mark_car_seen
from modules.cars.scrapers.yad2 import fetch_listings
from modules.cars.agent.scorer import score_car

logger = logging.getLogger(__name__)


def _format_alert(car, assessment: dict) -> str:
    score = assessment["score"]
    verdict = assessment["verdict"]
    notes = assessment["notes"]

    score_emoji = "🟢" if score >= 7 else "🟡" if score >= 5 else "🔴"
    notes_text = "\n".join(f"  • {n}" for n in notes) if notes else ""

    return (
        f"{score_emoji} *{car.manufacturer} {car.model}* — {score}/10\n"
        f"_{verdict}_\n\n"
        f"📅 {car.year}  |  📍 {car.area}\n"
        f"💰 {car.price:,} ₪  |  🛣 {car.km:,} km\n"
        f"🎨 {car.color}  |  ✋ יד {car.hand}\n"
        f"⚙️ {car.sub_model}\n"
        + (f"\n{notes_text}\n" if notes_text else "")
        + f"\n🔗 [View listing]({car.url})"
    )


async def _poll_and_notify(bot: Bot, chat_id: int):
    logger.info("[Cars] Starting Yad2 scrape...")

    try:
        listings = await _run_sync(fetch_listings)
    except Exception as e:
        logger.error("[Cars] Scrape failed: %s", e)
        return

    new_listings = [c for c in listings if not is_car_seen(c.token)]
    logger.info("[Cars] %d new listings (out of %d filtered)", len(new_listings), len(listings))

    if not new_listings:
        return

    sent = 0
    for car in new_listings:
        mark_car_seen(car.token)

        assessment = score_car(car)
        if assessment is None:
            continue
        if assessment["score"] < 5:
            logger.info("[Cars] Skipping low score (%d): %s %s", assessment["score"], car.manufacturer, car.model)
            continue

        try:
            await bot.send_message(
                chat_id=chat_id,
                text=_format_alert(car, assessment),
                parse_mode="Markdown",
            )
            sent += 1
        except Exception as e:
            logger.error("[Cars] Failed to send alert: %s", e)

    if sent:
        logger.info("[Cars] Sent %d car alerts", sent)


async def _run_sync(fn):
    """Run a blocking function in a thread pool (Playwright is sync)."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fn)


def register_jobs(scheduler: AsyncIOScheduler, bot: Bot, chat_id: int):
    scheduler.add_job(
        _poll_and_notify,
        trigger=IntervalTrigger(hours=POLL_INTERVAL_HOURS),
        args=[bot, chat_id],
        id="cars_poll",
        replace_existing=True,
        next_run_time=datetime.now(),
    )
