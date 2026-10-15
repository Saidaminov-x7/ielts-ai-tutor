import json
from datetime import date

import pytest
from aiohttp.test_utils import make_mocked_request
from sqlalchemy import select

from app.config import Settings
from app.database.models import ScheduledEvent


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, owner_id, text, **kwargs):
        self.messages.append((owner_id, text, kwargs))


def event_request(secret: str):
    from app import main

    request = make_mocked_request(
        "POST",
        "/internal/scheduled-event",
        headers={"X-Daily-Job-Secret": secret, "Content-Type": "application/json"},
        app={main.STATE_KEY: main.RuntimeState(bot=None, dispatcher=None)},
    )
    request._read_bytes = json.dumps(
        {"event_type": "weekly_progress_report", "event_date": date.today().isoformat()}
    ).encode()
    return request


@pytest.mark.asyncio
async def test_scheduled_event_is_secret_protected_and_idempotent(session, monkeypatch):
    from app import main

    secret = "n8n-internal-test-secret-with-more-than-32-chars"  # pragma: allowlist secret
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: Settings(owner_telegram_id=1234, daily_job_secret=secret),
    )
    monkeypatch.setattr(main, "SessionLocal", lambda: session)
    bot = FakeBot()
    request = event_request(secret)
    request.app[main.STATE_KEY] = main.RuntimeState(bot=bot, dispatcher=None)

    first = await main.scheduled_event(request)
    second = await main.scheduled_event(request)

    assert first.status == 200
    assert second.status == 200
    assert len(bot.messages) == 1
    event = session.scalar(select(ScheduledEvent))
    assert event is not None and event.status == "sent"


@pytest.mark.asyncio
async def test_scheduled_event_rejects_invalid_secret(monkeypatch):
    from aiohttp.web_exceptions import HTTPForbidden

    from app import main

    secret = "n8n-internal-test-secret-with-more-than-32-chars"  # pragma: allowlist secret
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: Settings(owner_telegram_id=1234, daily_job_secret=secret),
    )
    with pytest.raises(HTTPForbidden):
        await main.scheduled_event(event_request("wrong"))
