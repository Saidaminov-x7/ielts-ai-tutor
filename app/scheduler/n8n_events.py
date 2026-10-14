from datetime import UTC, date, datetime
from html import escape
from typing import Any, cast

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.database.models import AIUsage, ScheduledEvent, TaskProgress, UserSettings
from app.learning.lessons import TASKS
from app.learning.reports import weekly_progress_report
from app.learning.vocabulary import due_words

EVENT_TYPES = {
    "vocabulary_revision",
    "daily_mini_test",
    "smart_reminders",
    "weekly_ielts_exam",
    "weekly_progress_report",
    "application_health_monitoring",
    "ai_budget_monitoring",
}


def event_message(
    session: Session, event_type: str, owner_id: int, settings: Settings
) -> tuple[str | None, str]:
    user_settings = session.get(UserSettings, owner_id)
    if event_type not in {"application_health_monitoring", "ai_budget_monitoring"}:
        if user_settings and (not user_settings.reminders_enabled or user_settings.quiet_mode):
            return None, "skipped"

    current_day = user_settings.current_day if user_settings else 1
    if event_type == "vocabulary_revision":
        words = due_words(session, limit=10, owner_id=owner_id)
        if not words:
            return "Сегодня нет слов для повторения. Добавьте слова или откройте /menu.", "sent"
        lines = ["🔁 <b>Пора повторить слова</b>"]
        lines.extend(f"• {escape(word.english)} — {escape(word.translation)}" for word in words)
        lines.append("Начните тренировку: /review")
        return "\n".join(lines), "sent"
    if event_type == "daily_mini_test":
        return "📝 Ежедневный мини-тест готов. Начните его командой /test.", "sent"
    if event_type == "smart_reminders":
        completed = set(
            session.scalars(
                select(TaskProgress.task_key).where(
                    TaskProgress.owner_id == owner_id,
                    TaskProgress.day_number == current_day,
                    TaskProgress.completed.is_(True),
                    TaskProgress.task_key.in_([key for key, _, _ in TASKS]),
                )
            )
        )
        remaining = [(key, title) for key, title, _ in TASKS if key not in completed]
        if not remaining:
            return None, "skipped"
        titles = ", ".join(title for _, title in remaining[:3])
        extra = f" и ещё {len(remaining) - 3}" if len(remaining) > 3 else ""
        return (
            f"⏰ Осталось блоков: {len(remaining)} — {titles}{extra}. Откройте /lesson.",
            "sent",
        )
    if event_type == "weekly_ielts_exam":
        week = min(26, (current_day - 1) // 7 + 1)
        return (
            f"📋 Пора пройти контрольный экзамен недели {week}/26. "
            "Откройте /menu и выберите «Экзамен».",
            "sent",
        )
    if event_type == "weekly_progress_report":
        return (
            "📊 <b>Еженедельный отчёт</b>\n" + escape(weekly_progress_report(session, owner_id)),
            "sent",
        )
    if event_type == "application_health_monitoring":
        return "⚠️ Мониторинг подтвердил проблему доступности приложения.", "sent"
    if event_type == "ai_budget_monitoring":
        month = datetime.now(UTC).strftime("%Y-%m")
        spent = (
            session.scalar(
                select(func.coalesce(func.sum(AIUsage.actual_usd + AIUsage.reserved_usd), 0)).where(
                    AIUsage.owner_id == owner_id, AIUsage.month == month
                )
            )
            or 0
        )
        budget = settings.monthly_ai_budget_usd
        if budget <= 0 or float(spent) < budget * 0.8:
            return None, "skipped"
        return (
            f"💳 Использовано около ${float(spent):.2f} из лимита AI ${budget:.2f} за этот месяц.",
            "sent",
        )
    raise ValueError("Unsupported scheduled event")


def reserve_event(
    session: Session, event_type: str, event_day: date
) -> tuple[ScheduledEvent, bool]:
    event_key = f"{event_type}:{event_day.isoformat()}"
    event = session.scalar(select(ScheduledEvent).where(ScheduledEvent.event_key == event_key))
    if event is None:
        event = ScheduledEvent(event_key=event_key, event_type=event_type, status="sending")
        session.add(event)
        try:
            session.commit()
            session.refresh(event)
            return event, True
        except IntegrityError:
            session.rollback()
            event = session.scalar(
                select(ScheduledEvent).where(ScheduledEvent.event_key == event_key)
            )
    if event is None:
        raise RuntimeError("Scheduled event could not be reserved")
    if event.status in {"sent", "skipped", "sending"}:
        return event, False
    result = cast(
        Any,
        session.execute(
            update(ScheduledEvent)
            .where(
                ScheduledEvent.id == event.id,
                ScheduledEvent.status.in_(("pending", "failed")),
            )
            .values(status="sending")
        ),
    )
    session.commit()
    if result.rowcount != 1:
        session.refresh(event)
        return event, False
    session.refresh(event)
    return event, True


def finish_event(session: Session, event: ScheduledEvent, status: str) -> None:
    event.status = status
    event.delivered_at = datetime.now(UTC) if status in {"sent", "skipped"} else None
    session.commit()
