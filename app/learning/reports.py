from datetime import UTC, datetime, timedelta

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


def weekly_progress_report(session: Session, owner_id: int, *, now: datetime | None = None) -> str:
    """Summarize real learner activity in the trailing seven-day UTC window."""
    end = now or datetime.now(UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    start = end - timedelta(days=7)
    # SQLite stores the UTC timestamps as naive datetimes.
    start_naive = start.astimezone(UTC).replace(tzinfo=None)
    end_naive = end.astimezone(UTC).replace(tzinfo=None)

    activities = list(
        session.scalars(
            select(Activity).where(
                Activity.owner_id == owner_id,
                Activity.completed_at >= start_naive,
                Activity.completed_at < end_naive,
            )
        )
    )
    lessons = sum(activity.kind == "lesson" for activity in activities)
    reviews = [activity for activity in activities if activity.kind == "review"]
    tests = [activity for activity in activities if activity.kind in {"quiz", "weekly_exam"}]
    avg_test = sum(activity.score for activity in tests) / len(tests) if tests else None
    topic_scores: dict[str, list[float]] = {}
    for activity in tests:
        if activity.topic:
            topic_scores.setdefault(activity.topic, []).append(activity.score)
    weakest = min(
        ((sum(scores) / len(scores), topic) for topic, scores in topic_scores.items()),
        default=None,
    )

    new_words = (
        session.scalar(
            select(func.count(Vocabulary.id)).where(
                Vocabulary.owner_id == owner_id,
                Vocabulary.learned_at >= start_naive,
                Vocabulary.learned_at < end_naive,
            )
        )
        or 0
    )
    writing = session.scalar(
        select(WritingAttempt)
        .where(
            WritingAttempt.owner_id == owner_id,
            WritingAttempt.created_at >= start_naive,
            WritingAttempt.created_at < end_naive,
        )
        .order_by(WritingAttempt.created_at.desc())
        .limit(1)
    )
    lines = [
        "📊 Статистика за последние 7 дней",
        f"Завершено учебных дней: {lessons}",
        f"Добавлено личных слов: {new_words}",
        f"Повторений слов: {len(reviews)}"
        + (
            f" · средняя точность {round(sum(a.score for a in reviews) / len(reviews))}%"
            if reviews
            else ""
        ),
        f"Объективных тестов: {len(tests)}"
        + (f" · средний результат {round(avg_test)}%" if avg_test is not None else ""),
        (
            f"Writing: {writing.estimated_band}/9 (ориентировочно)"
            if writing
            else "Writing: за эту неделю нет оценок"
        ),
        (
            f"Тема для повторения: {weakest[1]} ({round(weakest[0])}%)"
            if weakest
            else "Тема для повторения: пока недостаточно результатов"
        ),
        "Оценки учебные и не являются официальным IELTS Band Score.",
    ]
    return "\n".join(lines)
