from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Activity, CourseDay, TaskProgress, UserSettings

TASKS = (
    ("review", "Повторение предыдущего материала", 20),
    ("grammar", "Новая грамматика", 45),
    ("vocabulary", "Новые слова и выражения", 40),
    ("exercises", "Практические упражнения", 45),
    ("reading", "Reading", 40),
    ("listening", "Listening по готовым материалам", 40),
    ("writing", "Writing", 45),
    ("quiz", "Проверка знаний и разбор ошибок", 30),
)


def current_day(session: Session, owner_id: int) -> int:
    settings = session.get(UserSettings, owner_id)
    return settings.current_day if settings else 1


def lesson_summary(session: Session, owner_id: int, day_number: int | None = None) -> dict:
    day = day_number or current_day(session, owner_id)
    course = session.scalar(select(CourseDay).where(CourseDay.day_number == day))
    progress = {
        p.task_key: p.completed
        for p in session.scalars(
            select(TaskProgress).where(
                TaskProgress.owner_id == owner_id, TaskProgress.day_number == day
            )
        )
    }
    rows = [
        {"key": key, "title": title, "minutes": minutes, "done": progress.get(key, False)}
        for key, title, minutes in TASKS
    ]
    return {
        "day": day,
        "week": (day - 1) // 7 + 1,
        "topic": course.topic if course else "Программа не импортирована",
        "grammar": course.grammar if course else "",
        "reading": course.reading if course else "Материал появится после импорта Excel.",
        "listening": course.listening if course else "Материал появится после импорта Excel.",
        "writing": course.writing if course else "Напишите короткий текст на тему дня.",
        "tasks": rows,
        "remaining": sum(not row["done"] for row in rows),
    }


def complete_task(session: Session, owner_id: int, day_number: int, task_key: str) -> bool:
    if task_key not in {task[0] for task in TASKS}:
        return False
    progress = session.scalar(
        select(TaskProgress).where(
            TaskProgress.owner_id == owner_id,
            TaskProgress.day_number == day_number,
            TaskProgress.task_key == task_key,
        )
    )
    if progress is None:
        progress = TaskProgress(owner_id=owner_id, day_number=day_number, task_key=task_key)
        session.add(progress)
    progress.completed = True
    progress.completed_at = datetime.now(UTC)
    session.commit()
    return True


def finish_day(session: Session, owner_id: int, day_number: int) -> bool:
    progress = list(
        session.scalars(
            select(TaskProgress).where(
                TaskProgress.owner_id == owner_id,
                TaskProgress.day_number == day_number,
                TaskProgress.completed.is_(True),
            )
        )
    )
    if not progress or len({p.task_key for p in progress}) < len(TASKS):
        return False
    from datetime import date, timedelta

    settings = session.get(UserSettings, owner_id)
    if settings is None:
        settings = UserSettings(
            owner_id=owner_id, current_day=1, streak=0, max_streak=0, completed_days=0
        )
    if settings.last_active_date != date.today():
        settings.streak = (
            settings.streak + 1
            if settings.last_active_date == date.today() - timedelta(days=1)
            else 1
        )
        settings.max_streak = max(settings.max_streak, settings.streak)
        settings.completed_days += 1
        settings.last_active_date = date.today()
    settings.current_day = min(182, max(settings.current_day, day_number + 1))
    session.add(settings)
    session.add(
        Activity(
            owner_id=owner_id,
            day_number=day_number,
            kind="lesson",
            topic="День обучения",
            score=100,
        )
    )
    session.commit()
    return True
