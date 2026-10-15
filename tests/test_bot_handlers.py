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


def test_button_menu_replaces_slash_command_navigation():
    registered = {handler.callback.__name__ for handler in handlers.router.message.handlers}
    assert "start" in registered
    assert "keyboard_menu_action" in registered
    assert not any(name.endswith("_command") for name in registered)


@pytest.mark.asyncio
async def test_start_shows_persistent_menu_and_limits_ai_to_writing():
    from app.bot.keyboards import MAIN_MENU

    message = SimpleNamespace(answer=AsyncMock())
    await handlers.start(message)
    text = message.answer.await_args.args[0]
    assert "кнопками" in text
    assert "только по вашему выбору" in text
    assert message.answer.await_args.kwargs["reply_markup"] is MAIN_MENU
