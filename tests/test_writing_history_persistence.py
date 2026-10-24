import json
from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from app.ai import writing_examiner
from app.config import Settings
from app.database.models import Activity, AIUsage, WritingAttempt
from app.database.session import make_engine


@pytest.mark.asyncio
async def test_examiner_persists_clean_essay_feedback_and_activity_together(monkeypatch):
    engine = make_engine("sqlite://")
    from app.database.session import Base

    Base.metadata.create_all(engine)

    def fake_reserve(session, owner_id, input_tokens, output_tokens):
        usage = AIUsage(
            owner_id=owner_id,
            month="2026-10",
            request_date=date(2026, 10, 19),
            reserved_usd=0.1,
            actual_usd=0,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        session.add(usage)
        session.flush()
        return usage

    def fake_settle(session, usage, input_tokens, output_tokens):
        usage.reserved_usd = 0
        usage.actual_usd = 0.01

    feedback = {
        "task_type": "task2",
        "estimated_band": 6.0,
        "criteria": {"task_achievement_response": 6, "coherence_cohesion": 6,
                     "lexical_resource": 6, "grammatical_range_accuracy": 6},
        "errors": [],
        "explanation_ru": "Feedback",
        "recommendations": ["Improve examples"],
        "improved_sample": "Sample",
        "recurring_errors": [],
        "disclaimer": "Estimate only",
    }

    class FakeClient:
        def __init__(self, **_kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=self._create,
                )
            )

        async def _create(self, **_kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(feedback)))],
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20),
            )

        async def close(self):
            pass

    monkeypatch.setattr(writing_examiner, "get_settings", lambda: Settings(openai_api_key="test"))
    monkeypatch.setattr(writing_examiner, "reserve", fake_reserve)
    monkeypatch.setattr(writing_examiner, "settle", fake_settle)
    monkeypatch.setattr(writing_examiner, "AsyncOpenAI", FakeClient)
    submitted = "  This is a sufficiently long response for testing persistence.  "

    try:
        with Session(engine, expire_on_commit=False) as session:
            result = await writing_examiner.examine(session, 44, submitted)
            attempt = session.query(WritingAttempt).one()
            activity = session.query(Activity).one()
            assert attempt.submission_text == submitted.strip()
            assert json.loads(attempt.feedback_json) == result.model_dump()
            assert activity.owner_id == attempt.owner_id == 44
            assert activity.kind == "writing"
    finally:
        engine.dispose()
