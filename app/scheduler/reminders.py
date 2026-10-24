from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]
from sqlalchemy import select

from app.config import get_settings
from app.database.models import UserSettings
from app.database.session import SessionLocal
from app.learning.lessons import lesson_summary


async def send_reminder(bot: Bot, owner_id: int, kind: str) -> None:
    with SessionLocal() as session:
        settings = session.get(UserSettings, owner_id)
        if not settings or not settings.reminders_enabled or settings.quiet_mode:
            return
        summary = lesson_summary(session, owner_id)
        if summary.get("content_granularity") == "weekly" and kind == "lesson":
            pending = [task for task in summary["tasks"] if task["available"] and not task["done"]]
            text = (
                f"📚 День {summary['day']}/210 · неделя {summary['week']}/30. "
                f"Тема: {summary['topic']}. "
                f"{pending[0]['title'] if pending else 'Занятия на сегодня завершены.'}"
            )
            await bot.send_message(owner_id, text)
            return
        text = {
            "lesson": f"📚 Пора начать учебный день {settings.current_day}/210.",
            "weekly": "📊 Откройте кнопку «📊 Мой прогресс» внизу чата.",
        }.get(kind, "🔁 Проверьте слова, ожидающие повторения.")
    await bot.send_message(owner_id, text)


async def sync_reminders(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    settings_cfg = get_settings()
    with SessionLocal() as session:
        rows = list(
            session.scalars(select(UserSettings).where(UserSettings.reminders_enabled.is_(True)))
        )
        enabled = [(row.owner_id, row.reminder_time) for row in rows if not row.quiet_mode]
    valid = set()
    for owner_id, reminder_time in enabled:
        try:
            hour, minute = map(int, reminder_time.split(":"))
        except ValueError:
            continue
        job_id = f"lesson:{owner_id}"
        valid.add(job_id)
        scheduler.add_job(
            send_reminder,
            CronTrigger(hour=hour, minute=minute, timezone=ZoneInfo(settings_cfg.timezone)),
            id=job_id,
            replace_existing=True,
            args=[bot, owner_id, "lesson"],
            misfire_grace_time=3600,
        )
        weekly_id = f"weekly:{owner_id}"
        valid.add(weekly_id)
        scheduler.add_job(
            send_reminder,
            CronTrigger(
                day_of_week="sun",
                hour=hour,
                minute=minute,
                timezone=ZoneInfo(settings_cfg.timezone),
            ),
            id=weekly_id,
            replace_existing=True,
            args=[bot, owner_id, "weekly"],
            misfire_grace_time=3600,
        )
    for job in scheduler.get_jobs():
        if job.id not in valid:
            scheduler.remove_job(job.id)
