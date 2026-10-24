from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import (
    Activity,
    CourseDay,
    CourseDayVocabulary,
    CourseWeek,
    TaskProgress,
    UserSettings,
    Vocabulary,
)
from app.learning.vocabulary import (
    due_words,
    words_due_for_course_day,
    words_for_day,
)

DAY_COUNT = 210
WEEK_COUNT = 30


def week_for_day(day: int) -> int:
    return min(WEEK_COUNT, max(1, (day - 1) // 7 + 1))


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


def _task_availability(
    session: Session, owner_id: int, day: int, course: CourseDay | CourseWeek | None
) -> dict[str, bool]:
    if course is None:
        return {key: False for key, _title, _minutes in TASKS}

    previous_course = (
        session.scalar(select(CourseDay).where(CourseDay.day_number == day - 1))
        if day > 1
        else None
    )
    week_number = week_for_day(day)
    scheduled_count = 0
    if day % 7 != 0:
        scheduled_count = min(5, 30 - (((day - 1) % 7) * 5))
    if isinstance(course, CourseWeek) and day % 7 == 0:
        has_vocabulary = (
            session.scalar(
                select(Vocabulary.id)
                .where(
                    Vocabulary.course_week == week_number,
                    (Vocabulary.owner_id == owner_id) | Vocabulary.owner_id.is_(None),
                )
                .limit(1)
            )
            is not None
        )
    elif isinstance(course, CourseWeek):
        first_sequence = ((day - 1) // 7) * 30 + ((day - 1) % 7) * 5 + 1
        has_vocabulary = (
            session.scalar(
                select(Vocabulary.id)
                .where(
                    Vocabulary.source_key.in_(
                        [
                            f"pdf:{index:03d}"
                            for index in range(first_sequence, first_sequence + scheduled_count)
                        ]
                    ),
                    (Vocabulary.owner_id == owner_id) | Vocabulary.owner_id.is_(None),
                )
                .limit(1)
            )
            is not None
        )
    previous_week = (
        session.scalar(select(CourseWeek).where(CourseWeek.week_number == week_for_day(day - 1)))
        if day > 1
        else None
    )
    has_previous_material = (previous_week is not None or previous_course is not None) and any(
        value.strip()
        for value in (
            (
                previous_week.grammar
                if previous_week
                else (previous_course.grammar if previous_course else "")
            ),
            (
                previous_week.reading_writing
                if previous_week
                else (previous_course.reading if previous_course else "")
            ),
            (
                previous_week.listening
                if previous_week
                else (previous_course.listening if previous_course else "")
            ),
            (
                previous_week.speaking_outcome
                if previous_week
                else (previous_course.writing if previous_course else "")
            ),
            (previous_course.objectives if previous_course else ""),
        )
    )
    return {
        "review": has_previous_material,
        "grammar": bool(course.grammar.strip()),
        "vocabulary": has_vocabulary
        if isinstance(course, CourseWeek)
        else (
            session.scalar(
                select(Vocabulary.id)
                .where(
                    Vocabulary.course_day == day,
                    (Vocabulary.owner_id == owner_id) | Vocabulary.owner_id.is_(None),
                )
                .limit(1)
            )
            is not None
        ),
        "exercises": bool(course.objectives.strip())
        if isinstance(course, CourseDay)
        else bool(course.grammar.strip()),
        "reading": bool(course.reading.strip())
        if isinstance(course, CourseDay)
        else bool(course.reading_writing.strip()),
        "listening": bool(course.listening.strip()),
        "writing": bool(course.writing.strip())
        if isinstance(course, CourseDay)
        else bool(course.reading_writing.strip()),
        # The app supplies its own objective quiz bank independently of the workbook.
        "quiz": True,
    }


def current_day(session: Session, owner_id: int) -> int:
    settings = session.get(UserSettings, owner_id)
    return min(DAY_COUNT, max(1, settings.current_day)) if settings else 1


def lesson_summary(session: Session, owner_id: int, day_number: int | None = None) -> dict:
    day = day_number or current_day(session, owner_id)
    day = min(DAY_COUNT, max(1, day))
    week_number = week_for_day(day)
    week = session.scalar(select(CourseWeek).where(CourseWeek.week_number == week_number))
    course = session.scalar(select(CourseDay).where(CourseDay.day_number == day))
    progress = {
        p.task_key: p.completed
        for p in session.scalars(
            select(TaskProgress).where(
                TaskProgress.owner_id == owner_id, TaskProgress.day_number == day
            )
        )
    }
    if week is not None and course is None:
        from app.learning.course_sources import new_cards_for_day

        sequences = new_cards_for_day(day)
        session.flush()
        due_count = len(due_words(session, limit=50, owner_id=owner_id))
        if sequences:
            cards = words_for_day(session, owner_id, week_number, sequences, day)
            studied = (
                session.scalar(
                    select(Activity.id).where(
                        Activity.owner_id == owner_id,
                        Activity.day_number == day,
                        Activity.kind == "vocabulary_study",
                    )
                )
                is not None
            )
            completed_assignments = list(
                session.scalars(
                    select(CourseDayVocabulary.reviewed).where(
                        CourseDayVocabulary.owner_id == owner_id,
                        CourseDayVocabulary.day_number == day,
                    )
                )
            )
            done = studied or (
                len(completed_assignments) >= len(sequences)
                and all(completed_assignments)
            )
            tasks = [
                {
                    "key": "vocabulary",
                    "title": "Vocabulary and collocations",
                    "minutes": 35,
                    "done": done,
                    "available": bool(cards) or done,
                    "new_cards": len(cards),
                }
            ]
        else:
            assignments = list(
                session.scalars(
                    select(CourseDayVocabulary).where(
                        CourseDayVocabulary.owner_id == owner_id,
                        CourseDayVocabulary.day_number == day,
                    )
                )
            )
            due_today = words_due_for_course_day(session, owner_id, week_number, day)
            assignments = list(
                session.scalars(
                    select(CourseDayVocabulary).where(
                        CourseDayVocabulary.owner_id == owner_id,
                        CourseDayVocabulary.day_number == day,
                    )
                )
            )
            reviewed_today = bool(assignments) and all(item.reviewed for item in assignments)
            tasks = [
                {
                    "key": "review",
                    "title": "Review due vocabulary",
                    "minutes": 35,
                    "done": reviewed_today,
                    "available": bool(due_today) or reviewed_today,
                    "due_cards": len(due_today) + len(assignments),
                }
            ]
        return {
            "day": day,
            "week": week_number,
            "course_imported": True,
            "week_source_available": True,
            "topic": week.topic,
            "daily_focus": f"Week {week_number}, study day {(day - 1) % 7 + 1}",
            "grammar": week.grammar,
            "reading": week.reading_writing,
            "listening": week.listening,
            "writing": week.reading_writing,
            "speaking_outcome": week.speaking_outcome,
            "tasks": tasks,
            "remaining": int(any(task["available"] and not task["done"] for task in tasks)),
            "content_granularity": "weekly",
            "scheduled_vocabulary_count": len(sequences),
            "due_vocabulary_count": int(due_count),
        }
    available = _task_availability(session, owner_id, day, course or week)
    # The spreadsheet describes a weekly routine, not eight authored tasks every day.
    # Keep the existing daily checklist for legacy CourseDay rows. For the new
    # roadmap, only expose content that is actually present and mark the weekly grain.
    rows = [
        {
            "key": key,
            "title": title,
            "minutes": minutes,
            "done": progress.get(key, False),
            "available": available[key],
        }
        for key, title, minutes in TASKS
    ]
    return {
        "day": day,
        "week": week_number,
        "week_source_available": week is not None,
        "course_imported": week is not None or course is not None,
        "topic": week.topic if week else (course.topic if course else "Программа не импортирована"),
        "daily_focus": (
            f"Week {week_number}, day {(day - 1) % 7 + 1}: follow the source weekly routine."
        )
        if week
        else "",
        "grammar": week.grammar if week else (course.grammar if course else ""),
        "reading": week.reading_writing if week else (course.reading if course else ""),
        "listening": week.listening if week else (course.listening if course else ""),
        "writing": week.reading_writing if week else (course.writing if course else ""),
        "speaking_outcome": week.speaking_outcome if week else "",
        "tasks": rows,
        "remaining": sum(row["available"] and not row["done"] for row in rows),
        "content_granularity": "weekly" if week else ("daily" if course else "missing"),
    }


def complete_task(session: Session, owner_id: int, day_number: int, task_key: str) -> bool:
    if task_key not in {task[0] for task in TASKS}:
        return False
    course = session.scalar(select(CourseDay).where(CourseDay.day_number == day_number))
    if course is None:
        # Weekly content needs its own progress contract; legacy day-task rows
        # cannot truthfully represent completion of a weekly source prompt.
        return False
    week = session.scalar(
        select(CourseWeek).where(CourseWeek.week_number == week_for_day(day_number))
    )
    availability = _task_availability(session, owner_id, day_number, course or week)
    if not availability.get(task_key, False):
        return False
    if course is None and task_key not in {"vocabulary"}:
        # The roadmap supplies prompts at weekly grain, not executable daily
        # lesson payloads. Do not let a checkbox claim unprovided material ran.
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
    if not 1 <= day_number <= DAY_COUNT:
        return False
    existing_completion = session.scalar(
        select(Activity).where(
            Activity.owner_id == owner_id,
            Activity.day_number == day_number,
            Activity.kind == "lesson",
        )
    )
    if existing_completion:
        return False
    course = session.scalar(select(CourseDay).where(CourseDay.day_number == day_number))
    week = session.scalar(
        select(CourseWeek).where(CourseWeek.week_number == week_for_day(day_number))
    )
    available = _task_availability(session, owner_id, day_number, course or week)
    required_task_keys = {key for key, is_available in available.items() if is_available}
    if not required_task_keys:
        return False
    progress = list(
        session.scalars(
            select(TaskProgress).where(
                TaskProgress.owner_id == owner_id,
                TaskProgress.day_number == day_number,
                TaskProgress.completed.is_(True),
            )
        )
    )
    completed_task_keys = {p.task_key for p in progress}
    if not required_task_keys.issubset(completed_task_keys):
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
    settings.current_day = min(DAY_COUNT, max(settings.current_day, day_number + 1))
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
