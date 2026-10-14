import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot import handlers
from app.database.models import Activity, ReviewSession, UserSettings, Vocabulary


@pytest.mark.asyncio
async def test_final_review_callback_commits_session_activity_and_streak(
    session, monkeypatch
):
    word = Vocabulary(english="persist", translation="сохранить")
    session.add(word)
    session.flush()
    review = ReviewSession(owner_id=101, word_ids_json=json.dumps([word.id]), cursor=0)
    session.add(review)
    session.add(
        UserSettings(owner_id=101, current_day=1, streak=0, max_streak=0, completed_days=0)
    )
    session.commit()
    review_id = review.id
    word_id = word.id

    @contextmanager
    def use_test_session():
        yield session

    monkeypatch.setattr(handlers, "SessionLocal", use_test_session)
    callback = SimpleNamespace(
        data=f"review:{review_id}:1",
        from_user=SimpleNamespace(id=101),
        answer=AsyncMock(),
        message=SimpleNamespace(answer=AsyncMock()),
    )

    await handlers.review_answer_callback(callback)
    session.expire_all()

    saved_review = session.get(ReviewSession, review_id)
    saved_word = session.get(Vocabulary, word_id)
    saved_settings = session.get(UserSettings, 101)
    activities = list(session.query(Activity).filter_by(owner_id=101, kind="review"))
    assert saved_review is not None and saved_review.completed and saved_review.cursor == 1
    assert saved_word is not None and saved_word.correct_count == 1
    assert saved_settings is not None and saved_settings.streak == 1
    assert len(activities) == 1 and activities[0].score == 100
    callback.answer.assert_awaited_once()


def test_required_slash_commands_are_registered():
    registered = {handler.callback.__name__ for handler in handlers.router.message.handlers}
    assert {
        "start",
        "help_command",
        "today_command",
        "words_command",
        "review_command",
        "test_command",
        "writing_command",
        "progress_command",
        "mistakes_command",
        "settings_command",
    } <= registered


@pytest.mark.asyncio
async def test_help_exposes_required_user_commands():
    message = SimpleNamespace(answer=AsyncMock())
    await handlers.help_command(message)
    text = message.answer.await_args.args[0]
    assert all(
        command in text
        for command in (
            "/today",
            "/words",
            "/review",
            "/test",
            "/writing",
            "/progress",
            "/mistakes",
            "/settings",
        )
    )
