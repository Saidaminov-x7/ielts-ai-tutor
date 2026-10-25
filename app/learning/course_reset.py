"""Safe, owner-scoped restart of course counters while preserving learning history."""

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import CourseDayVocabulary, CourseResetArchive, TaskProgress, UserSettings


def reset_course(session: Session, owner_id: int, request_key: str) -> UserSettings:
    """Archive course checklist rows, reset visible counters, preserve all learning history."""
    prior_reset = session.scalar(
        select(CourseResetArchive).where(
            CourseResetArchive.owner_id == owner_id,
            CourseResetArchive.request_key == request_key,
        )
    )
    if prior_reset is not None:
        existing_settings = session.get(UserSettings, owner_id)
        if existing_settings is not None:
            return existing_settings
    settings = session.get(UserSettings, owner_id)
    if settings is None:
        settings = UserSettings(owner_id=owner_id, current_day=1)
        session.add(settings)
        session.flush()

    task_rows = list(
        session.scalars(select(TaskProgress).where(TaskProgress.owner_id == owner_id))
    )
    vocabulary_rows = list(
        session.scalars(
            select(CourseDayVocabulary).where(CourseDayVocabulary.owner_id == owner_id)
        )
    )
    archive_payload = {
        "previous_counters": {
            "current_day": settings.current_day,
            "completed_days": settings.completed_days,
            "streak": settings.streak,
            "last_active_date": settings.last_active_date.isoformat()
            if settings.last_active_date
            else None,
            "course_started_at": settings.course_started_at.isoformat()
            if settings.course_started_at
            else None,
            "course_schedule_day": settings.course_schedule_day,
        },
        "task_progress": [
            {
                "day_number": row.day_number,
                "task_key": row.task_key,
                "completed": row.completed,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            }
            for row in task_rows
        ],
        "course_day_vocabulary": [
            {
                "day_number": row.day_number,
                "vocabulary_id": row.vocabulary_id,
                "reviewed": row.reviewed,
            }
            for row in vocabulary_rows
        ],
    }
    session.add(
        CourseResetArchive(
            owner_id=owner_id,
            request_key=request_key,
            reset_at=datetime.now(UTC),
            payload_json=json.dumps(archive_payload, ensure_ascii=False),
        )
    )
    for row in (*task_rows, *vocabulary_rows):
        session.delete(row)
    settings.current_day = 1
    settings.completed_days = 0
    settings.streak = 0
    settings.last_active_date = None
    settings.course_started_at = datetime.now(UTC)
    settings.course_schedule_day = 1
    session.commit()
    return settings
