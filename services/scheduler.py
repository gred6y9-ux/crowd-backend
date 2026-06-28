import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from database import AsyncSessionLocal
from models import Question
from services.ai_generator import generate_daily_question

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler(timezone="UTC")


async def _generate_and_save() -> None:
    today = datetime.now(timezone.utc).date()
    logger.info("[scheduler] Starting daily question generation for %s", today)

    async with AsyncSessionLocal() as db:
        try:
            existing = await db.execute(select(Question).where(Question.date == today))
            if existing.scalar_one_or_none():
                logger.info("[scheduler] Question for %s already exists — skipping", today)
                return

            generated = generate_daily_question()

            question = Question(
                text=generated.text,
                option_a=generated.option_a,
                option_b=generated.option_b,
                emoji_a=generated.emoji_a,
                emoji_b=generated.emoji_b,
                date=today,
                votes_a=0,
                votes_b=0,
            )
            db.add(question)
            await db.commit()
            logger.info(
                "[scheduler] Saved question id=%s for %s: '%s'",
                question.id,
                today,
                question.text,
            )
        except Exception:
            await db.rollback()
            logger.exception("[scheduler] Failed to save generated question for %s", today)


def start_scheduler() -> None:
    _scheduler.add_job(
        _generate_and_save,
        trigger=CronTrigger(hour=0, minute=0, second=0, timezone="UTC"),
        id="daily_question",
        replace_existing=True,
        misfire_grace_time=3600,  # run up to 1h late if server was down
    )
    _scheduler.start()
    logger.info("[scheduler] APScheduler started — daily question job registered (00:00 UTC)")


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[scheduler] APScheduler stopped")
