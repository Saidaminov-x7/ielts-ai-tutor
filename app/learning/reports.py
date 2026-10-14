from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import Activity, UserSettings, Vocabulary, WritingAttempt


def progress_report(session: Session, owner_id: int) -> str:
    settings = session.get(UserSettings, owner_id)
    if settings is None:
        settings = UserSettings(
            owner_id=owner_id, current_day=1, streak=0, max_streak=0, completed_days=0
        )
    words = (
        session.scalar(
            select(func.count(Vocabulary.id)).where(
                (Vocabulary.owner_id == owner_id) | Vocabulary.owner_id.is_(None)
            )
        )
        or 0
    )
    score = session.scalar(select(func.avg(Activity.score)).where(Activity.owner_id == owner_id))
    writing = session.scalars(
        select(WritingAttempt.estimated_band)
        .where(WritingAttempt.owner_id == owner_id)
        .order_by(WritingAttempt.created_at.desc())
        .limit(5)
    ).all()
    week = min(26, (settings.current_day - 1) // 7 + 1)
    return (
        f"📊 Неделя {week}/26 · день {settings.current_day}/182\n"
        f"Завершено учебных дней: {settings.completed_days}\nСерия: {settings.streak} дн. "
        f"(рекорд {settings.max_streak})\nСлов в словаре: {words}\n"
        "Средний результат объективных заданий: "
        f"{round(float(score), 1) if score is not None else 'пока нет данных'}%\n"
        "Writing (последние оценки ИИ): "
        f"{', '.join(map(str, writing)) if writing else 'пока нет данных'}\n"
        f"Выполнение программы: {round(settings.completed_days / 182 * 100, 1)}%\n"
        "Оценка не является официальным IELTS Band Score."
    )
