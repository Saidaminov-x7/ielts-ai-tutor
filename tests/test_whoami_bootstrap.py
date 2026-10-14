from types import SimpleNamespace

import pytest

from app.config import Settings
from app.security.authentication import OwnerOnlyMiddleware


@pytest.mark.asyncio
async def test_whoami_is_the_only_allowed_command_before_owner_setup(monkeypatch):
    monkeypatch.setattr("app.security.authentication.get_settings", lambda: Settings())
    middleware = OwnerOnlyMiddleware()
    user = SimpleNamespace(id=24680)
    whoami_message = SimpleNamespace(
        text="/whoami",
        chat=SimpleNamespace(type="private"),
        answer=lambda *_args, **_kwargs: None,
    )
    called = []

    async def handler(_event, _data):
        called.append(True)
        return "allowed"

    async def blocked_answer(*_args, **_kwargs):
        return None

    whoami_message.answer = blocked_answer
    result = await middleware(handler, whoami_message, {"event_from_user": user})
    assert result == "allowed"
    assert called == [True]

    forbidden = SimpleNamespace(
        text="/progress",
        chat=SimpleNamespace(type="private"),
        answer=blocked_answer,
    )
    result = await middleware(handler, forbidden, {"event_from_user": user})
    assert result is None
    assert called == [True]


@pytest.mark.asyncio
async def test_whoami_is_not_allowed_before_owner_setup_in_group(monkeypatch):
    monkeypatch.setattr("app.security.authentication.get_settings", lambda: Settings())
    middleware = OwnerOnlyMiddleware()
    user = SimpleNamespace(id=24680)
    event = SimpleNamespace(
        text="/whoami",
        chat=SimpleNamespace(type="group"),
        answer=lambda *_args, **_kwargs: None,
    )

    async def handler(_event, _data):
        raise AssertionError("group update must not pass the owner gate")

    async def blocked_answer(*_args, **_kwargs):
        return None

    event.answer = blocked_answer
    assert await middleware(handler, event, {"event_from_user": user}) is None


@pytest.mark.asyncio
async def test_whoami_does_not_bypass_configured_owner_id(monkeypatch):
    monkeypatch.setattr(
        "app.security.authentication.get_settings", lambda: Settings(owner_telegram_id=111)
    )
    middleware = OwnerOnlyMiddleware()
    user = SimpleNamespace(id=24680)
    event = SimpleNamespace(
        text="/whoami",
        chat=SimpleNamespace(type="private"),
        answer=lambda *_args, **_kwargs: None,
    )

    async def handler(_event, _data):
        raise AssertionError("non-owner must not bypass the owner gate")

    async def blocked_answer(*_args, **_kwargs):
        return None

    event.answer = blocked_answer
    assert await middleware(handler, event, {"event_from_user": user}) is None
