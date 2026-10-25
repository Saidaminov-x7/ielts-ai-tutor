from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot import handlers
from app.bot.keyboards import MAIN_MENU, MENU_ACTIONS
from app.config import Settings


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", [handlers.quiz, handlers.exam])
async def test_quiz_and_exam_entry_open_the_mini_app(handler, monkeypatch):
    monkeypatch.setattr(
        handlers,
        "get_settings",
        lambda: Settings(webhook_base_url="https://tutor.example.test"),
    )
    callback = SimpleNamespace(
        answer=AsyncMock(),
        message=SimpleNamespace(answer=AsyncMock()),
    )

    await handler(callback)

    callback.answer.assert_awaited_once()
    callback.message.answer.assert_awaited_once()
    markup = callback.message.answer.await_args.kwargs["reply_markup"]
    button = markup.inline_keyboard[0][0]
    assert button.web_app is not None
    expected_tab = "practice" if handler is handlers.quiz else "exam"
    assert button.web_app.url == f"https://tutor.example.test?tab={expected_tab}"


@pytest.mark.asyncio
async def test_quiz_entry_does_not_start_a_chat_quiz_without_https(monkeypatch):
    monkeypatch.setattr(handlers, "get_settings", lambda: Settings())
    callback = SimpleNamespace(
        answer=AsyncMock(),
        message=SimpleNamespace(answer=AsyncMock()),
    )

    await handlers.quiz(callback)

    callback.message.answer.assert_awaited_once()
    assert "HTTPS" in callback.message.answer.await_args.args[0]
    assert "reply_markup" not in callback.message.answer.await_args.kwargs


@pytest.mark.asyncio
async def test_persistent_keyboard_routes_to_authenticated_inline_web_app(monkeypatch):
    monkeypatch.setattr(
        handlers,
        "get_settings",
        lambda: Settings(webhook_base_url="https://tutor.example.test"),
    )
    state = SimpleNamespace(clear=AsyncMock())
    message = SimpleNamespace(
        text="🚀 Открыть приложение",
        answer=AsyncMock(),
    )

    assert MENU_ACTIONS[message.text] == "app"
    assert MAIN_MENU.keyboard[0][0].web_app is None
    await handlers.keyboard_menu_action(message, state)

    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once()
    launch_button = message.answer.await_args.kwargs["reply_markup"].inline_keyboard[0][0]
    assert launch_button.web_app is not None
    assert launch_button.web_app.url == "https://tutor.example.test?tab=home"
