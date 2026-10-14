import pytest
from aiohttp.test_utils import make_mocked_request
from sqlalchemy import select

from app.config import Settings
from app.database.models import DailyDelivery


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, owner_id, text):
        self.messages.append((owner_id, text))


@pytest.mark.asyncio
async def test_daily_wakeup_is_secret_protected_and_idempotent(session, monkeypatch):
    from app import main

    secret = "a" * 40  # pragma: allowlist secret
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: Settings(
            owner_telegram_id=1234,
            daily_job_secret=secret,
            timezone="Asia/Tashkent",
        ),
    )
    monkeypatch.setattr(main, "SessionLocal", lambda: session)
    bot = FakeBot()
    app = {"bot": bot}
    request = make_mocked_request(
        "POST", "/internal/daily", headers={"X-Daily-Job-Secret": secret}, app=app
    )
    first = await main.daily_delivery(request)
    assert first.status == 200
    assert len(bot.messages) == 1
    assert (
        session.scalar(select(DailyDelivery).where(DailyDelivery.owner_id == 1234)).status == "sent"
    )
    second = await main.daily_delivery(request)
    assert second.status == 200
    assert len(bot.messages) == 1


@pytest.mark.asyncio
async def test_daily_wakeup_rejects_wrong_secret(monkeypatch):
    from aiohttp.web_exceptions import HTTPForbidden

    from app import main

    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: Settings(
            owner_telegram_id=1234, daily_job_secret="correct-secret-long-enough-1234567890"
        ),
    )
    request = make_mocked_request(
        "POST",
        "/internal/daily",
        headers={"X-Daily-Job-Secret": "wrong"},  # pragma: allowlist secret
    )
    with pytest.raises(HTTPForbidden):
        await main.daily_delivery(request)
