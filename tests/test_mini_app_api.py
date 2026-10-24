import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from aiogram import Router
from aiohttp.test_utils import TestClient, TestServer
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.api import mini_app as api
from app.config import Settings
from app.database.models import (
    Activity,
    CourseDay,
    ExamSession,
    QuizAttempt,
    QuizSession,
    TaskProgress,
    UserSettings,
    Vocabulary,
    WritingAttempt,
)
from app.database.session import Base
from app.learning.daily_tests import WEEKLY_QUESTIONS, start_quiz
from app.learning.lessons import TASKS
from app.learning.weekly_exams import start_exam

BOT_TOKEN = "integration-test-bot-token"
OWNER_ID = 700001
FOREIGN_OWNER_ID = 700002
DAILY_SECRET = "integration-test-daily-secret-with-sufficient-length"


class _FakeBotSession:
    async def close(self) -> None:
        pass


class _FakeBot:
    def __init__(self, *args, **kwargs) -> None:
        self.session = _FakeBotSession()
        self.sent_messages: list[tuple[int, str, object]] = []

    async def send_message(self, chat_id: int, text: str, reply_markup=None) -> None:
        self.sent_messages.append((chat_id, text, reply_markup))


def _signed_init_data(owner_id: int, *, auth_date: int | None = None) -> str:
    fields = {
        "auth_date": str(int(time.time()) if auth_date is None else auth_date),
        "user": json.dumps({"id": owner_id}, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    signature = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return urlencode([*fields.items(), ("hash", signature)])


@pytest.fixture
def mini_app_env(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session_local = sessionmaker(bind=engine, expire_on_commit=False)
    settings = Settings(
        telegram_bot_token=BOT_TOKEN,
        owner_telegram_id=OWNER_ID,
        daily_job_secret=DAILY_SECRET,
        database_url="sqlite://",
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(api, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "init_db", lambda: None)
    monkeypatch.setattr(main, "startup", _noop_startup)
    monkeypatch.setattr(main, "Bot", _FakeBot)
    # The production router is a module-level singleton and aiohttp app
    # construction includes it. HTTP-only tests use a fresh empty router.
    monkeypatch.setattr(main, "router", Router(name="test-mini-app-router"))
    monkeypatch.setattr(main, "SessionLocal", test_session_local)
    monkeypatch.setattr(api, "SessionLocal", test_session_local)

    app = main.create_app()
    yield app, test_session_local
    engine.dispose()


async def _noop_startup(_app) -> None:
    pass


@pytest.mark.asyncio
async def test_api_rejects_unauthenticated_bootstrap_without_caching(mini_app_env):
    app, _ = mini_app_env
    async with TestClient(TestServer(app)) as client:
        response = await client.get("/api/v1/bootstrap")
        payload = await response.json()

    assert response.status == 401
    assert response.headers["Cache-Control"] == "no-store"
    assert payload["error"]["code"] == "http_error"


@pytest.mark.asyncio
async def test_bootstrap_returns_the_valid_signed_owner(mini_app_env):
    app, _ = mini_app_env
    async with TestClient(TestServer(app)) as client:
        response = await client.get(
            "/api/v1/bootstrap",
            headers={"X-Telegram-Init-Data": _signed_init_data(OWNER_ID)},
        )
        payload = await response.json()

    assert response.status == 200
    assert payload["user"]["telegram_id"] == OWNER_ID
    assert payload["dashboard"]["day"] == 1
    assert payload["notifications"]["reminder_time"] == "19:00"


@pytest.mark.asyncio
async def test_lesson_task_endpoint_requires_auth_and_rejects_unknown_task(mini_app_env):
    app, test_session_local = mini_app_env
    with test_session_local() as session:
        session.add(CourseDay(day_number=1, week_number=1, topic="Present simple"))
        session.commit()

    endpoint = "/api/v1/lesson/1/tasks/grammar/complete"
    async with TestClient(TestServer(app)) as client:
        unauthenticated = await client.post(endpoint)
        wrong_owner = await client.post(
            endpoint,
            headers={"X-Telegram-Init-Data": _signed_init_data(FOREIGN_OWNER_ID)},
        )
        unknown_task = await client.post(
            "/api/v1/lesson/1/tasks/not-a-task/complete",
            headers={"X-Telegram-Init-Data": _signed_init_data(OWNER_ID)},
        )
        unknown_payload = await unknown_task.json()

    assert unauthenticated.status == 401
    assert wrong_owner.status == 403
    assert unknown_task.status == 404
    assert unknown_payload["error"]["code"] == "task_not_found"


@pytest.mark.asyncio
async def test_lesson_task_requires_imported_course_and_creates_no_progress(mini_app_env):
    app, test_session_local = mini_app_env
    async with TestClient(TestServer(app)) as client:
        response = await client.post(
            "/api/v1/lesson/1/tasks/grammar/complete",
            headers={"X-Telegram-Init-Data": _signed_init_data(OWNER_ID)},
        )
        payload = await response.json()

    assert response.status == 409
    assert payload["error"]["code"] == "course_not_imported"
    with test_session_local() as session:
        assert session.scalar(select(func.count(TaskProgress.id))) == 0
        assert session.scalar(select(func.count(Activity.id))) == 0


@pytest.mark.asyncio
async def test_lesson_task_owner_comes_from_verified_telegram_identity(mini_app_env):
    app, test_session_local = mini_app_env
    with test_session_local() as session:
        session.add(
            CourseDay(
                day_number=1,
                week_number=1,
                topic="Present simple",
                grammar="Use the present simple for routines.",
            )
        )
        session.commit()

    task_key = "grammar"
    async with TestClient(TestServer(app)) as client:
        response = await client.post(
            f"/api/v1/lesson/1/tasks/{task_key}/complete",
            headers={"X-Telegram-Init-Data": _signed_init_data(OWNER_ID)},
            json={"owner_id": FOREIGN_OWNER_ID},
        )
        payload = await response.json()

    assert response.status == 200
    grammar_task = next(task for task in payload["lesson"]["tasks"] if task["key"] == "grammar")
    assert grammar_task["done"] is True
    with test_session_local() as session:
        rows = list(session.scalars(select(TaskProgress)))
        assert len(rows) == 1
        assert rows[0].owner_id == OWNER_ID
        assert rows[0].owner_id != FOREIGN_OWNER_ID


@pytest.mark.asyncio
async def test_lesson_task_rejects_blank_material_for_requested_task(mini_app_env):
    app, test_session_local = mini_app_env
    with test_session_local() as session:
        session.add(CourseDay(day_number=1, week_number=1, topic="Present simple"))
        session.commit()

    async with TestClient(TestServer(app)) as client:
        response = await client.post(
            "/api/v1/lesson/1/tasks/grammar/complete",
            headers={"X-Telegram-Init-Data": _signed_init_data(OWNER_ID)},
        )
        payload = await response.json()

    assert response.status == 409
    assert payload["error"]["code"] == "task_content_not_imported"
    with test_session_local() as session:
        assert session.scalar(select(func.count(TaskProgress.id))) == 0


@pytest.mark.asyncio
async def test_lesson_vocabulary_task_requires_imported_vocabulary(mini_app_env):
    app, test_session_local = mini_app_env
    with test_session_local() as session:
        session.add(
            CourseDay(
                day_number=1,
                week_number=1,
                topic="Present simple",
                grammar="Use the present simple for routines.",
            )
        )
        session.commit()

    async with TestClient(TestServer(app)) as client:
        response = await client.post(
            "/api/v1/lesson/1/tasks/vocabulary/complete",
            headers={"X-Telegram-Init-Data": _signed_init_data(OWNER_ID)},
        )
        payload = await response.json()

    assert response.status == 409
    assert payload["error"]["code"] == "task_content_not_imported"
    with test_session_local() as session:
        assert session.scalar(select(func.count(TaskProgress.id))) == 0


@pytest.mark.asyncio
async def test_lesson_completion_advances_once_and_retry_does_not_duplicate_activity(
    mini_app_env,
):
    app, test_session_local = mini_app_env
    with test_session_local() as session:
        session.add_all(
            [
                CourseDay(
                    day_number=1,
                    week_number=1,
                    topic="Current lesson",
                    grammar="Grammar",
                    reading="Reading passage",
                    listening="Listening transcript",
                    writing="Writing prompt",
                    objectives="Lesson objectives",
                ),
                CourseDay(day_number=2, week_number=1, topic="Next lesson"),
            ]
        )
        session.add(
            Vocabulary(
                english="routine",
                translation="ordinary activity",
                owner_id=OWNER_ID,
                course_day=1,
            )
        )
        session.commit()

    headers = {"X-Telegram-Init-Data": _signed_init_data(OWNER_ID)}
    async with TestClient(TestServer(app)) as client:
        lesson_response = await client.get("/api/v1/lesson/current", headers=headers)
        initial_lesson = await lesson_response.json()
        available_keys = [
            task["key"] for task in initial_lesson["tasks"] if task["available"]
        ]
        assert "review" not in available_keys
        assert len(available_keys) == len(TASKS) - 1

        first_key = available_keys[0]
        first_url = f"/api/v1/lesson/1/tasks/{first_key}/complete"
        first = await client.post(first_url, headers=headers)
        first_payload = await first.json()
        assert first.status == 200
        assert first_payload["day_completed"] is False
        assert first_payload["lesson"]["remaining"] == len(available_keys) - 1
        review_task = next(
            task for task in first_payload["lesson"]["tasks"] if task["key"] == "review"
        )
        assert review_task["available"] is False

        repeated_first = await client.post(first_url, headers=headers)
        repeated_payload = await repeated_first.json()
        assert repeated_first.status == 200
        assert repeated_payload["day_completed"] is False
        assert repeated_payload["lesson"]["remaining"] == len(available_keys) - 1

        for task_key in available_keys[1:-1]:
            response = await client.post(
                f"/api/v1/lesson/1/tasks/{task_key}/complete", headers=headers
            )
            assert response.status == 200
            assert (await response.json())["day_completed"] is False

        final_key = available_keys[-1]
        final_url = f"/api/v1/lesson/1/tasks/{final_key}/complete"
        final_response = await client.post(final_url, headers=headers)
        final_payload = await final_response.json()
        assert final_response.status == 200
        assert final_payload["day_completed"] is True
        assert final_payload["lesson"]["day"] == 2
        assert next(
            task for task in final_payload["lesson"]["tasks"] if task["key"] == "review"
        )["done"] is False

        retry = await client.post(final_url, headers=headers)
        retry_payload = await retry.json()
        assert retry.status == 409
        assert retry_payload["error"]["code"] == "stale_day"

    with test_session_local() as session:
        settings = session.get(UserSettings, OWNER_ID)
        assert settings is not None and settings.current_day == 2
        assert session.scalar(
            select(func.count(TaskProgress.id)).where(
                TaskProgress.owner_id == OWNER_ID, TaskProgress.day_number == 1
            )
        ) == len(available_keys)
        assert session.scalar(
            select(func.count(Activity.id)).where(
                Activity.owner_id == OWNER_ID,
                Activity.day_number == 1,
                Activity.kind == "lesson",
            )
        ) == 1


@pytest.mark.asyncio
async def test_quiz_start_answer_result_and_repeated_submit_are_idempotent(mini_app_env):
    app, test_session_local = mini_app_env
    headers = {"X-Telegram-Init-Data": _signed_init_data(OWNER_ID)}
    async with TestClient(TestServer(app)) as client:
        started = await client.post("/api/v1/quiz/sessions", headers=headers)
        assert started.status == 201
        quiz = await started.json()
        assert quiz["submitted"] is False
        assert len(quiz["questions"]) == 10

        answer_response = await client.put(
            f"/api/v1/quiz/sessions/{quiz['id']}/answers",
            headers=headers,
            json={"question_index": 0, "option_index": 0},
        )
        assert answer_response.status == 200
        answered = await answer_response.json()
        assert answered["answers"] == {"0": 0}

        first_submit = await client.post(
            f"/api/v1/quiz/sessions/{quiz['id']}/submit", headers=headers
        )
        assert first_submit.status == 200
        first_result = await first_submit.json()
        assert first_result["total"] == 10
        assert first_result["score"] in range(11)
        assert len(first_result["results"]) == 10

        second_submit = await client.post(
            f"/api/v1/quiz/sessions/{quiz['id']}/submit", headers=headers
        )
        assert second_submit.status == 200
        assert await second_submit.json() == first_result

    with test_session_local() as session:
        assert session.scalar(select(func.count(QuizAttempt.id))) == 1
        assert session.scalar(
            select(func.count(Activity.id)).where(
                Activity.owner_id == OWNER_ID, Activity.kind == "quiz"
            )
        ) == 1
        saved_quiz = session.get(QuizSession, quiz["id"])
        assert saved_quiz is not None and saved_quiz.submitted_at is not None


@pytest.mark.asyncio
async def test_quiz_session_owned_by_another_user_is_hidden_as_not_found(mini_app_env):
    app, test_session_local = mini_app_env
    with test_session_local() as session:
        foreign_quiz = start_quiz(session, FOREIGN_OWNER_ID, 1)
        foreign_quiz_id = foreign_quiz.id

    async with TestClient(TestServer(app)) as client:
        response = await client.get(
            f"/api/v1/quiz/sessions/{foreign_quiz_id}",
            headers={"X-Telegram-Init-Data": _signed_init_data(OWNER_ID)},
        )
        payload = await response.json()

    assert response.status == 404
    assert payload["error"]["code"] == "quiz_not_found"


@pytest.mark.asyncio
async def test_weekly_exam_lifecycle_hides_answer_keys_and_grades_on_server(mini_app_env):
    app, test_session_local = mini_app_env
    headers = {"X-Telegram-Init-Data": _signed_init_data(OWNER_ID)}
    async with TestClient(TestServer(app)) as client:
        started = await client.post("/api/v1/exam/sessions", headers=headers)
        assert started.status == 201
        exam = await started.json()
        assert exam["submitted"] is False
        assert exam["week"] == 1
        assert len(exam["questions"]) == len(WEEKLY_QUESTIONS)
        for question in exam["questions"]:
            assert set(question) == {"index", "topic", "question", "options"}

        exam_id = exam["id"]
        fetched = await client.get(f"/api/v1/exam/sessions/{exam_id}", headers=headers)
        assert fetched.status == 200
        assert (await fetched.json())["id"] == exam_id

        expected_correct = 0
        for index, source_question in enumerate(WEEKLY_QUESTIONS):
            correct_answer = source_question["answer"]
            selected_answer = (
                (correct_answer + 1) % len(source_question["options"])
                if index == 0
                else correct_answer
            )
            expected_correct += int(selected_answer == correct_answer)
            answer_response = await client.put(
                f"/api/v1/exam/sessions/{exam_id}/answers",
                headers=headers,
                json={"question_index": index, "answer_index": selected_answer},
            )
            assert answer_response.status == 200
            answer_payload = await answer_response.json()
            assert answer_payload["answers"][str(index)] == selected_answer
            assert all(
                "answer" not in question and "explanation" not in question
                for question in answer_payload["questions"]
            )

        before_submit = await client.get(
            f"/api/v1/exam/sessions/{exam_id}", headers=headers
        )
        before_payload = await before_submit.json()
        assert before_submit.status == 200
        assert before_payload["submitted"] is False
        assert before_payload["result"] is None

        submitted = await client.post(
            f"/api/v1/exam/sessions/{exam_id}/submit", headers=headers
        )
        assert submitted.status == 200
        result = await submitted.json()
        assert result["score"] == expected_correct
        assert result["total"] == len(WEEKLY_QUESTIONS)
        assert result["results"][0]["correct"] is False
        assert result["results"][0]["selected"] != WEEKLY_QUESTIONS[0]["answer"]
        assert result["results"][1]["correct"] is True

        repeated_submit = await client.post(
            f"/api/v1/exam/sessions/{exam_id}/submit", headers=headers
        )
        assert repeated_submit.status == 200
        assert await repeated_submit.json() == result

        after_submit = await client.get(
            f"/api/v1/exam/sessions/{exam_id}", headers=headers
        )
        persisted = await after_submit.json()
        assert persisted["submitted"] is True
        assert persisted["result"]["score"] == expected_correct

    with test_session_local() as session:
        saved_exam = session.get(ExamSession, exam_id)
        assert saved_exam is not None
        assert saved_exam.submitted_at is not None
        assert saved_exam.score == expected_correct
        assert session.scalar(
            select(func.count(QuizAttempt.id)).where(QuizAttempt.owner_id == OWNER_ID)
        ) == 1
        assert session.scalar(
            select(func.count(Activity.id)).where(
                Activity.owner_id == OWNER_ID, Activity.kind == "weekly_exam"
            )
        ) == 1


@pytest.mark.asyncio
async def test_weekly_exam_routes_hide_foreign_owner_session(mini_app_env):
    app, test_session_local = mini_app_env
    with test_session_local() as session:
        foreign_exam = start_exam(session, FOREIGN_OWNER_ID, 1)
        foreign_exam_id = foreign_exam.id

    headers = {"X-Telegram-Init-Data": _signed_init_data(OWNER_ID)}
    async with TestClient(TestServer(app)) as client:
        get_response = await client.get(
            f"/api/v1/exam/sessions/{foreign_exam_id}", headers=headers
        )
        answer_response = await client.put(
            f"/api/v1/exam/sessions/{foreign_exam_id}/answers",
            headers=headers,
            json={"question_index": 0, "answer_index": 0},
        )
        submit_response = await client.post(
            f"/api/v1/exam/sessions/{foreign_exam_id}/submit", headers=headers
        )

    assert get_response.status == 404
    assert answer_response.status == 404
    assert submit_response.status == 404


@pytest.mark.asyncio
async def test_writing_history_is_owner_scoped_and_detail_includes_legacy_null_text(
    mini_app_env,
):
    app, test_session_local = mini_app_env
    with test_session_local() as session:
        own = WritingAttempt(
            owner_id=OWNER_ID,
            task_type="task2",
            estimated_band=6.5,
            feedback_json=json.dumps({"criteria": {"coherence": 6}}),
            submission_text="My submitted response.",
        )
        legacy = WritingAttempt(
            owner_id=OWNER_ID,
            task_type="task1",
            estimated_band=5.5,
            feedback_json=json.dumps({"criteria": {"task": 5}}),
        )
        foreign = WritingAttempt(
            owner_id=FOREIGN_OWNER_ID,
            task_type="task2",
            estimated_band=9.0,
            feedback_json=json.dumps({"private": True}),
            submission_text="Foreign essay.",
        )
        session.add_all([own, legacy, foreign])
        session.commit()
        own_id, legacy_id, foreign_id = own.id, legacy.id, foreign.id

    headers = {"X-Telegram-Init-Data": _signed_init_data(OWNER_ID)}
    async with TestClient(TestServer(app)) as client:
        listing = await client.get("/api/v1/writing/attempts?limit=10", headers=headers)
        listed = await listing.json()
        detail_response = await client.get(
            f"/api/v1/writing/attempts/{own_id}", headers=headers
        )
        detail = await detail_response.json()
        legacy_response = await client.get(
            f"/api/v1/writing/attempts/{legacy_id}", headers=headers
        )
        legacy_detail = await legacy_response.json()
        foreign_response = await client.get(
            f"/api/v1/writing/attempts/{foreign_id}", headers=headers
        )
        missing_response = await client.get("/api/v1/writing/attempts/999999", headers=headers)
        foreign_error = await foreign_response.json()
        missing_error = await missing_response.json()

    assert listing.status == 200
    assert len(listed["items"]) == 2
    assert {item["id"] for item in listed["items"]} == {own_id, legacy_id}
    assert next(item for item in listed["items"] if item["id"] == own_id)["text_available"]
    assert not next(item for item in listed["items"] if item["id"] == legacy_id)["text_available"]
    assert detail_response.status == 200
    assert detail["submission_text"] == "My submitted response."
    assert detail["feedback"] == {"criteria": {"coherence": 6}}
    assert legacy_response.status == 200
    assert legacy_detail["submission_text"] is None
    assert foreign_response.status == missing_response.status == 404
    assert foreign_error == missing_error


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", ["0", "51", "bad"])
async def test_writing_history_rejects_invalid_limit(mini_app_env, limit):
    app, _ = mini_app_env
    async with TestClient(TestServer(app)) as client:
        response = await client.get(
            f"/api/v1/writing/attempts?limit={limit}",
            headers={"X-Telegram-Init-Data": _signed_init_data(OWNER_ID)},
        )
        payload = await response.json()

    assert response.status == 400
    assert payload["error"]["code"] == "invalid_limit"


@pytest.mark.asyncio
async def test_daily_delivery_includes_owner_and_shared_words_but_not_foreign_words(
    mini_app_env,
):
    app, test_session_local = mini_app_env
    with test_session_local() as session:
        session.add(CourseDay(day_number=1, week_number=1, topic="Test topic"))
        session.add(UserSettings(owner_id=OWNER_ID, current_day=1))
        session.add_all(
            [
                Vocabulary(
                    english="owner-word",
                    translation="owner translation",
                    owner_id=OWNER_ID,
                    course_day=1,
                ),
                Vocabulary(
                    english="shared-word",
                    translation="shared translation",
                    owner_id=None,
                    course_day=1,
                ),
                Vocabulary(
                    english="foreign-word",
                    translation="foreign translation",
                    owner_id=FOREIGN_OWNER_ID,
                    course_day=1,
                ),
            ]
        )
        session.commit()

    async with TestClient(TestServer(app)) as client:
        response = await client.post(
            "/internal/daily",
            headers={"X-Daily-Job-Secret": DAILY_SECRET},
        )
        payload = await response.json()

    bot = app[main.STATE_KEY].bot
    assert response.status == 200
    assert payload["words"] == 2
    assert len(bot.sent_messages) == 1
    assert bot.sent_messages[0][0] == OWNER_ID
    message = bot.sent_messages[0][1]
    assert "owner-word" in message
    assert "shared-word" in message
    assert "foreign-word" not in message

