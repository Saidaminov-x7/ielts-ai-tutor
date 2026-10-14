from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.database.models import Activity, TaskProgress, UserSettings, Vocabulary, WritingAttempt
from app.learning.lessons import TASKS
from app.learning.reports import weekly_progress_report
from app.scheduler.n8n_events import event_message


def test_weekly_report_uses_only_real_activity_from_last_seven_days(session):
    now = datetime(2026, 10, 14, 12, tzinfo=UTC)
    session.add_all(
        [
            Activity(
                owner_id=41,
                day_number=7,
                kind="lesson",
                topic="",
                score=100,
                completed_at=(now - timedelta(days=2)).replace(tzinfo=None),
            ),
            Activity(
                owner_id=41,
                day_number=1,
                kind="quiz",
                topic="Present Perfect",
                score=48,
                completed_at=(now - timedelta(days=2)).replace(tzinfo=None),
            ),
            Activity(
                owner_id=41,
                day_number=1,
                kind="quiz",
                topic="Old topic",
                score=0,
                completed_at=(now - timedelta(days=8)).replace(tzinfo=None),
            ),
            Vocabulary(
                english="review",
                translation="повторять",
                owner_id=41,
                learned_at=(now - timedelta(days=1)).replace(tzinfo=None),
            ),
            WritingAttempt(
                owner_id=41,
                task_type="task2",
                estimated_band=5.5,
                feedback_json="{}",
                created_at=(now - timedelta(days=1)).replace(tzinfo=None),
            ),
        ]
    )
    session.commit()

    report = weekly_progress_report(session, 41, now=now)

    assert "Завершено учебных дней: 1" in report
    assert "Добавлено личных слов: 1" in report
    assert "Объективных тестов: 1 · средний результат 48%" in report
    assert "Present Perfect (48%)" in report
    assert "5.5/9" in report
    assert "Old topic" not in report


def test_smart_reminder_lists_only_incomplete_lesson_tasks(session):
    settings = UserSettings(owner_id=41, current_day=3, reminders_enabled=True, quiet_mode=False)
    session.add(settings)
    session.add_all(
        TaskProgress(
            owner_id=41,
            day_number=3,
            task_key=key,
            completed=True,
        )
        for key, _, _ in TASKS[:-1]
    )
    session.commit()

    message, status = event_message(session, "smart_reminders", 41, Settings())

    assert status == "sent"
    assert message is not None
    assert "Осталось блоков: 1" in message
    assert "Проверка знаний и разбор ошибок" in message
    assert "Осталось блоков: 8" not in message


def test_smart_reminder_skips_completed_day(session):
    session.add(UserSettings(owner_id=41, current_day=3, reminders_enabled=True, quiet_mode=False))
    session.add_all(
        TaskProgress(owner_id=41, day_number=3, task_key=key, completed=True) for key, _, _ in TASKS
    )
    session.commit()

    message, status = event_message(session, "smart_reminders", 41, Settings())

    assert (message, status) == (None, "skipped")
