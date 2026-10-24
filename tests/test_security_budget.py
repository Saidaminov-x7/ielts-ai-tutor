import pytest
from aiogram.types import User

from app.ai.budget_manager import BudgetExceeded, reserve
from app.config import Settings


def test_secret_settings_are_masked():
    settings = Settings(
        telegram_bot_token="example-token-value",
        openai_api_key="example-api-value",  # pragma: allowlist secret
    )
    assert "example-secret" not in str(settings)


@pytest.mark.asyncio
async def test_owner_middleware_rejects_non_owner(monkeypatch):
    from app.security import authentication

    monkeypatch.setattr(authentication, "get_settings", lambda: Settings(owner_telegram_id=123))
    called = False

    async def handler(event, data):
        nonlocal called
        called = True

    middleware = authentication.OwnerOnlyMiddleware()
    await middleware(
        handler,
        object(),
        {"event_from_user": User(id=456, is_bot=False, first_name="Other")},
    )
    assert not called


def test_budget_limit_blocks_next_request(session, monkeypatch):
    from app.ai import budget_manager

    monkeypatch.setattr(
        budget_manager,
        "get_settings",
        lambda: Settings(
            monthly_ai_budget_usd=0.00001,
            ai_input_price_per_million=10,
            ai_output_price_per_million=10,
            max_daily_ai_requests=4,
        ),
    )
    with pytest.raises(BudgetExceeded):
        reserve(session, 1, 2000, 100)


def test_daily_request_limit_ignores_earlier_days_in_month(session, monkeypatch):
    from datetime import date

    from app.ai import budget_manager
    from app.database.models import AIUsage

    today = date(2026, 10, 19)

    class FixedDate(date):
        @classmethod
        def today(cls):
            return today

    monkeypatch.setattr(budget_manager, "date", FixedDate)
    monkeypatch.setattr(
        budget_manager,
        "get_settings",
        lambda: Settings(
            monthly_ai_budget_usd=5,
            ai_input_price_per_million=0,
            ai_output_price_per_million=0,
            max_daily_ai_requests=1,
        ),
    )
    session.add(
        AIUsage(
            owner_id=1,
            month="2026-10",
            request_date=date(2026, 10, 18),
            reserved_usd=0,
            actual_usd=0,
        )
    )
    session.commit()

    usage = reserve(session, 1, 10, 10)

    assert usage.request_date == today


def test_user_input_prompt_is_structured_in_examiner_source():
    from pathlib import Path

    source = Path("app/ai/writing_examiner.py").read_text(encoding="utf-8")
    assert "недоверенные данные" in source
    assert '"submission": clean_text' in source


def test_writing_feedback_is_persisted_and_reported(session):
    import json

    from app.database.models import Activity, WritingAttempt
    from app.learning.reports import progress_report

    session.add(
        WritingAttempt(
            owner_id=44,
            task_type="task2",
            estimated_band=5.5,
            feedback_json=json.dumps({"estimated_band": 5.5}),
        )
    )
    session.add(
        Activity(owner_id=44, day_number=1, kind="writing", topic="Writing task2", score=61.1)
    )
    session.commit()
    assert "5.5" in progress_report(session, 44)


def test_sqlalchemy_database_path_is_parameterized(session):
    from app.database.models import Vocabulary

    malicious = "x%' OR 1=1 --"
    session.add_all(
        [
            Vocabulary(english="hello", translation="привет", owner_id=1),
            Vocabulary(english="secret", translation="секрет", owner_id=2),
        ]
    )
    session.commit()
    from app.learning.vocabulary import search_words

    assert search_words(session, malicious, owner_id=1) == []
