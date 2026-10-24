"""Authenticated JSON API for the Telegram Mini App.

The hosting application must install ``mini_app_auth_middleware`` from
``app.security.mini_app_auth`` before registering these routes. It attaches a
verified ``MiniAppIdentity`` to the request.

Routes are rooted at ``/api/v1``. Errors use ``{"error": {"code", "message"}}``.
"""

import json
import logging
import re
from datetime import datetime

from aiohttp import web
from sqlalchemy import func, or_, select

from app.ai.budget_manager import BudgetExceeded
from app.ai.gemini_tutor import GeminiTutorError, ask_course_tutor
from app.ai.writing_examiner import examine
from app.config import get_settings
from app.database.models import (
    Activity,
    AIUsage,
    CourseDay,
    CourseWeek,
    ErrorLog,
    ExamSession,
    QuizSession,
    UserSettings,
    Vocabulary,
    VocabularyProgress,
    WritingAttempt,
)
from app.database.session import SessionLocal
from app.learning.course_sources import new_cards_for_day
from app.learning.daily_tests import answer_quiz, start_quiz, submit_quiz
from app.learning.lessons import TASKS, complete_task, current_day, finish_day, lesson_summary
from app.learning.vocabulary import (
    due_words,
    mark_course_day_reviewed,
    record_review_for_owner,
    words_due_for_course_day,
    words_for_day,
)
from app.learning.weekly_exams import record_exam_answer, start_exam, submit_exam
from app.security.mini_app_auth import get_mini_app_identity

API_PREFIX = "/api/v1"
_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message


@web.middleware
async def json_errors(request: web.Request, handler):
    try:
        return await handler(request)
    except ApiError as exc:
        return web.json_response(
            {"error": {"code": exc.code, "message": exc.message}}, status=exc.status
        )
    except web.HTTPException as exc:
        return web.json_response(
            {"error": {"code": "http_error", "message": exc.reason}}, status=exc.status
        )


def _owner(request: web.Request) -> int:
    try:
        owner_id = get_mini_app_identity(request).telegram_user_id
    except RuntimeError:
        raise ApiError(401, "unauthorized", "Authentication is required.") from None
    if not isinstance(owner_id, int) or owner_id <= 0:
        raise ApiError(401, "unauthorized", "Authentication is required.")
    return owner_id


async def _body(request: web.Request) -> dict:
    if request.content_type != "application/json":
        raise ApiError(415, "unsupported_media_type", "Send application/json.")
    try:
        value = await request.json()
    except (json.JSONDecodeError, ValueError):
        raise ApiError(400, "invalid_json", "Request body must be valid JSON.") from None
    if not isinstance(value, dict):
        raise ApiError(400, "invalid_body", "Request body must be a JSON object.")
    return value


def _settings(session, owner_id: int) -> UserSettings:
    row = session.get(UserSettings, owner_id)
    if row is None:
        row = UserSettings(owner_id=owner_id)
        session.add(row)
        session.flush()
    return row


def _question_payload(raw: dict, index: int) -> dict:
    # Deliberately omit the correct answer and explanation until the quiz is graded.
    return {
        "index": index,
        "topic": raw["topic"],
        "question": raw["question"],
        "options": raw["options"],
    }


def _quiz_result(quiz: QuizSession) -> dict:
    questions = json.loads(quiz.questions_json)
    answers = json.loads(quiz.answers_json or "{}")
    results = []
    for index, question in enumerate(questions):
        selected = answers.get(str(index), -1)
        results.append(
            {
                "index": index,
                "topic": question["topic"],
                "selected": selected,
                "correct": selected == question["answer"],
                "correct_option": question["options"][question["answer"]],
                "explanation": question["explanation"],
            }
        )
    total = len(questions)
    score = quiz.score or 0
    return {
        "score": score,
        "total": total,
        "percent": round(score / total * 100) if total else 0,
        "results": results,
    }


def _owned_quiz(session, owner_id: int, raw_id: str) -> QuizSession:
    try:
        quiz_id = int(raw_id)
    except ValueError:
        raise ApiError(404, "quiz_not_found", "Quiz session was not found.") from None
    quiz = session.scalar(
        select(QuizSession).where(QuizSession.id == quiz_id, QuizSession.owner_id == owner_id)
    )
    if quiz is None:
        raise ApiError(404, "quiz_not_found", "Quiz session was not found.")
    return quiz


def _owned_exam(session, owner_id: int, raw_id: str) -> ExamSession:
    try:
        exam_id = int(raw_id)
    except ValueError:
        raise ApiError(404, "exam_not_found", "Exam session was not found.") from None
    exam = session.scalar(
        select(ExamSession).where(ExamSession.id == exam_id, ExamSession.owner_id == owner_id)
    )
    if exam is None:
        raise ApiError(404, "exam_not_found", "Exam session was not found.")
    return exam


def _exam_result(exam: ExamSession) -> dict:
    """Build feedback from the stored answer snapshot without changing records."""
    questions = json.loads(exam.questions_json)
    answers = json.loads(exam.answers_json or "{}")
    results = []
    for index, question in enumerate(questions):
        selected = answers.get(str(index), -1)
        results.append(
            {
                "index": index,
                "topic": question["topic"],
                "selected": selected,
                "correct": selected == question["answer"],
                "correct_option": question["options"][question["answer"]],
                "explanation": question["explanation"],
            }
        )
    score = exam.score or 0
    total = len(questions)
    return {
        "score": score,
        "total": total,
        "percent": round(score / total * 100) if total else 0,
        "week": exam.week_number,
        "note": "Practice result; not an official IELTS score.",
        "results": results,
    }


def _serialize_exam(exam: ExamSession) -> dict:
    questions = json.loads(exam.questions_json)
    return {
        "id": exam.id,
        "week": exam.week_number,
        "deadline": exam.deadline.isoformat(),
        "submitted": exam.submitted_at is not None,
        "answers": json.loads(exam.answers_json or "{}"),
        "questions": [_question_payload(question, i) for i, question in enumerate(questions)],
        "result": _exam_result(exam) if exam.submitted_at is not None else None,
    }


async def bootstrap(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    with SessionLocal() as session:
        settings = _settings(session, owner_id)
        day = current_day(session, owner_id)
        lesson = lesson_summary(session, owner_id, day)
        due_count = (
            session.scalar(
                select(func.count(Vocabulary.id))
                .select_from(Vocabulary)
                .outerjoin(
                    VocabularyProgress,
                    (VocabularyProgress.vocabulary_id == Vocabulary.id)
                    & (VocabularyProgress.owner_id == owner_id),
                )
                .where(
                    (Vocabulary.owner_id == owner_id) | Vocabulary.owner_id.is_(None),
                    or_(
                        (
                            VocabularyProgress.id.is_(None)
                            & (Vocabulary.next_review <= datetime.now().date())
                        ),
                        VocabularyProgress.next_review <= datetime.now().date(),
                    ),
                )
            )
            or 0
        )
        session.commit()
        return web.json_response(
            {
                "user": {"telegram_id": owner_id},
                "dashboard": {
                    "day": day,
                    "week": lesson["week"],
                    "topic": lesson["topic"],
                    "course_imported": lesson["course_imported"],
                    "completed_days": settings.completed_days,
                    "streak": settings.streak,
                    "due_vocabulary": int(due_count),
                },
                "lesson": lesson,
                "notifications": {
                    "reminders_enabled": settings.reminders_enabled,
                    "quiet_mode": settings.quiet_mode,
                    "reminder_time": settings.reminder_time,
                    "timezone": get_settings().timezone,
                },
            }
        )


async def current_lesson(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    with SessionLocal() as session:
        return web.json_response(lesson_summary(session, owner_id))


async def course_roadmap(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    with SessionLocal() as session:
        settings = session.get(UserSettings, owner_id)
        current = min(210, max(1, settings.current_day if settings else 1))
        weeks = list(session.scalars(select(CourseWeek).order_by(CourseWeek.week_number)))
        return web.json_response(
            {
                "total_weeks": 30,
                "total_days": 210,
                "current_day": current,
                "current_week": min(30, max(1, (current - 1) // 7 + 1)),
                "weeks": [
                    {
                        "week": row.week_number,
                        "month": row.month,
                        "topic": row.topic,
                        "grammar": row.grammar,
                        "listening": row.listening,
                        "reading_writing": row.reading_writing,
                        "speaking_outcome": row.speaking_outcome,
                        "content_granularity": "weekly",
                        "current": row.week_number == min(30, max(1, (current - 1) // 7 + 1)),
                    }
                    for row in weeks
                ],
            }
        )


async def complete_lesson_task(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    try:
        day_number = int(request.match_info["day_number"])
    except ValueError:
        raise ApiError(400, "invalid_day", "day_number must be an integer.") from None
    task_key = request.match_info["task_key"]
    if task_key not in {key for key, _title, _minutes in TASKS}:
        raise ApiError(404, "task_not_found", "Lesson task was not found.")

    with SessionLocal() as session:
        learner_day = current_day(session, owner_id)
        if day_number != learner_day:
            raise ApiError(409, "stale_day", "Only the current lesson day can be updated.")
        course_day = session.scalar(select(CourseDay).where(CourseDay.day_number == day_number))
        if (
            course_day is None
            and session.scalar(
                select(CourseWeek.id).where(
                    CourseWeek.week_number == min(30, (day_number - 1) // 7 + 1)
                )
            )
            is None
        ):
            raise ApiError(409, "course_not_imported", "Course content has not been imported.")
        availability = lesson_summary(session, owner_id, day_number)["tasks"]
        task_available = next(task["available"] for task in availability if task["key"] == task_key)
        if not task_available:
            raise ApiError(
                409,
                "task_content_not_imported",
                "This lesson task has no imported course material yet.",
            )
        if not complete_task(session, owner_id, day_number, task_key):
            raise ApiError(422, "task_not_completed", "Lesson task could not be completed.")
        if task_key == "vocabulary":
            from app.learning.course_sources import new_cards_for_day

            summary = lesson_summary(session, owner_id, day_number)
            week = int(summary["week"])
            sequences = new_cards_for_day(day_number)
            cards = (
                words_due_for_course_day(session, owner_id, week, day_number)
                if day_number % 7 == 0
                else words_for_day(session, owner_id, week, sequences, day_number)
            )
            if course_day is not None:
                cards = list(
                    session.scalars(
                        select(Vocabulary).where(
                            Vocabulary.course_day == day_number,
                            (Vocabulary.owner_id == owner_id) | Vocabulary.owner_id.is_(None),
                        )
                    )
                )
            if day_number % 7 == 0:
                for card in cards:
                    mark_course_day_reviewed(session, owner_id, day_number, card)
            elif course_day is None and len(cards) != len(sequences):
                raise ApiError(
                    409,
                    "course_vocabulary_incomplete",
                    "Scheduled word cards are unavailable.",
                )
            if not cards:
                raise ApiError(409, "vocabulary_not_due", "No scheduled vocabulary is available.")
            for card in cards:
                mark_course_day_reviewed(session, owner_id, day_number, card)
            for card in cards:
                record_review_for_owner(session, card, owner_id, True)
            session.add(
                Activity(
                    owner_id=owner_id,
                    day_number=day_number,
                    kind="vocabulary_study",
                    topic=summary["topic"],
                    score=100,
                )
            )
            session.commit()
        day_state = lesson_summary(session, owner_id, day_number)
        day_completed = (
            finish_day(session, owner_id, day_number) if day_state["remaining"] == 0 else False
        )
        return web.json_response(
            {
                "lesson": lesson_summary(session, owner_id),
                "day_completed": day_completed,
            }
        )


async def quiz_start(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    with SessionLocal() as session:
        quiz = start_quiz(session, owner_id, current_day(session, owner_id))
        return web.json_response(_serialize_quiz(quiz), status=201)


def _serialize_quiz(quiz: QuizSession) -> dict:
    questions = json.loads(quiz.questions_json)
    return {
        "id": quiz.id,
        "day": quiz.day_number,
        "submitted": quiz.submitted_at is not None,
        "answers": json.loads(quiz.answers_json or "{}"),
        "questions": [_question_payload(question, i) for i, question in enumerate(questions)],
        "result": _quiz_result(quiz) if quiz.submitted_at is not None else None,
    }


async def quiz_get(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    with SessionLocal() as session:
        return web.json_response(
            _serialize_quiz(_owned_quiz(session, owner_id, request.match_info["quiz_id"]))
        )


async def quiz_answer(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    data = await _body(request)
    index, option = data.get("question_index"), data.get("option_index")
    if type(index) is not int or type(option) is not int:
        raise ApiError(400, "invalid_answer", "question_index and option_index must be integers.")
    with SessionLocal() as session:
        quiz = _owned_quiz(session, owner_id, request.match_info["quiz_id"])
        if quiz.submitted_at is not None:
            raise ApiError(409, "quiz_submitted", "Submitted quiz answers cannot be changed.")
        if not answer_quiz(session, quiz, index, option):
            raise ApiError(422, "invalid_answer", "Question or option index is out of range.")
        return web.json_response(_serialize_quiz(quiz))


async def quiz_submit(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    with SessionLocal() as session:
        quiz = _owned_quiz(session, owner_id, request.match_info["quiz_id"])
        if quiz.submitted_at is None:
            submit_quiz(session, quiz)
        return web.json_response(_quiz_result(quiz))


async def exam_start(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    with SessionLocal() as session:
        week = min(26, max(1, (current_day(session, owner_id) - 1) // 7 + 1))
        exam = start_exam(session, owner_id, week)
        return web.json_response(_serialize_exam(exam), status=201)


async def exam_get(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    with SessionLocal() as session:
        exam = _owned_exam(session, owner_id, request.match_info["exam_id"])
        return web.json_response(_serialize_exam(exam))


async def exam_answer(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    data = await _body(request)
    question_index, answer_index = data.get("question_index"), data.get("answer_index")
    if type(question_index) is not int or type(answer_index) is not int:
        raise ApiError(
            400,
            "invalid_answer",
            "question_index and answer_index must be integers.",
        )
    with SessionLocal() as session:
        exam = _owned_exam(session, owner_id, request.match_info["exam_id"])
        if exam.submitted_at is not None:
            raise ApiError(409, "exam_submitted", "Submitted exam answers cannot be changed.")
        if not record_exam_answer(session, exam, question_index, answer_index):
            raise ApiError(
                422,
                "invalid_answer",
                "Exam is expired or the question or answer index is out of range.",
            )
        return web.json_response(_serialize_exam(exam))


async def exam_submit(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    with SessionLocal() as session:
        exam = _owned_exam(session, owner_id, request.match_info["exam_id"])
        if exam.submitted_at is None:
            submit_exam(session, exam)
        return web.json_response(_exam_result(exam))


async def vocabulary_due(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    raw_limit = request.query.get("limit", "20")
    try:
        limit = int(raw_limit)
    except ValueError:
        raise ApiError(400, "invalid_limit", "limit must be an integer from 1 to 50.") from None
    if not 1 <= limit <= 50:
        raise ApiError(400, "invalid_limit", "limit must be an integer from 1 to 50.")
    with SessionLocal() as session:
        words = due_words(session, limit=limit, owner_id=owner_id)
        return web.json_response({"items": [_word(word) for word in words], "count": len(words)})


async def vocabulary_library(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    query = request.query.get("q", "").strip()[:100]
    week_raw = request.query.get("week")
    try:
        limit = min(100, max(1, int(request.query.get("limit", "50"))))
        week = int(week_raw) if week_raw is not None else None
    except ValueError:
        raise ApiError(400, "invalid_filter", "Invalid vocabulary filter.") from None
    if week is not None and not 1 <= week <= 30:
        raise ApiError(400, "invalid_filter", "Week must be from 1 to 30.")
    with SessionLocal() as session:
        stmt = select(Vocabulary).where(
            (Vocabulary.owner_id == owner_id) | Vocabulary.owner_id.is_(None)
        )
        if query:
            needle = f"%{query}%"
            stmt = stmt.where(
                Vocabulary.english.ilike(needle)
                | Vocabulary.translation.ilike(needle)
                | Vocabulary.collocation.ilike(needle)
                | Vocabulary.collocation_translation.ilike(needle)
            )
        if week is not None:
            stmt = stmt.where(Vocabulary.course_week == week)
        items = list(
            session.scalars(stmt.order_by(Vocabulary.course_week, Vocabulary.id).limit(limit))
        )
        return web.json_response({"items": [_word(item) for item in items], "count": len(items)})


async def vocabulary_today(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    with SessionLocal() as session:
        day = current_day(session, owner_id)
        week = min(30, max(1, (day - 1) // 7 + 1))
        rows = (
            words_due_for_course_day(session, owner_id, week, day)
            if day % 7 == 0
            else words_for_day(session, owner_id, week, new_cards_for_day(day), day)
        )
        return web.json_response(
            {
                "day": day,
                "week": week,
                "new_cards_today": 0 if day % 7 == 0 else len(rows),
                "due_cards_today": len(rows) if day % 7 == 0 else 0,
                "items": [_word(row) for row in rows],
            }
        )


def _word(word: Vocabulary) -> dict:
    return {
        "id": word.id,
        "english": word.english,
        "translation": word.translation,
        "transcription": word.transcription,
        "example": word.example,
        "topic": word.topic,
        "next_review": word.next_review.isoformat(),
        "mastery": word.mastery,
        "week": word.course_week,
        "pronunciation_hint": word.pronunciation_hint,
        "collocation": word.collocation,
        "collocation_translation": word.collocation_translation,
        "collocation_transcription": word.collocation_transcription,
        "collocation_pronunciation_hint": word.collocation_pronunciation_hint,
    }


async def vocabulary_review(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    data = await _body(request)
    correct = data.get("correct")
    if type(correct) is not bool:
        raise ApiError(400, "invalid_review", "correct must be a boolean.")
    try:
        word_id = int(request.match_info["word_id"])
    except ValueError:
        raise ApiError(404, "word_not_found", "Vocabulary item was not found.") from None
    with SessionLocal() as session:
        word = session.scalar(
            select(Vocabulary).where(
                Vocabulary.id == word_id,
                (Vocabulary.owner_id == owner_id) | Vocabulary.owner_id.is_(None),
            )
        )
        if word is None:
            raise ApiError(404, "word_not_found", "Vocabulary item was not found.")
        state = record_review_for_owner(session, word, owner_id, correct)
        session.add(
            Activity(
                owner_id=owner_id, kind="review", topic=word.topic, score=100 if correct else 0
            )
        )
        session.commit()
        result = _word(word)
        result.update({"next_review": state.next_review.isoformat(), "mastery": state.mastery})
        return web.json_response(result)


async def learning_tutor(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    data = await _body(request)
    question = data.get("question")
    if not isinstance(question, str) or not question.strip() or len(question) > 1000:
        raise ApiError(400, "invalid_question", "Question must contain 1 to 1000 characters.")
    settings = get_settings()
    if settings.gemini_api_key is None:
        raise ApiError(503, "tutor_unavailable", "Учебный помощник пока не настроен.")
    with SessionLocal() as session:
        now = datetime.now().date()
        used = (
            session.scalar(
                select(func.count(AIUsage.id)).where(
                    AIUsage.owner_id == owner_id,
                    AIUsage.request_date == now,
                    AIUsage.provider == "gemini",
                )
            )
            or 0
        )
        if used >= settings.max_daily_gemini_requests:
            raise ApiError(429, "tutor_limit", "На сегодня лимит учебных вопросов исчерпан.")
        day = current_day(session, owner_id)
        week = session.scalar(
            select(CourseWeek).where(CourseWeek.week_number == min(30, (day - 1) // 7 + 1))
        )
        if week is None:
            raise ApiError(409, "course_not_imported", "Материалы плана ещё не загружены.")
        words = list(
            session.scalars(
                select(Vocabulary.english)
                .where(
                    Vocabulary.course_week == week.week_number,
                    (Vocabulary.owner_id == owner_id) | Vocabulary.owner_id.is_(None),
                )
                .order_by(Vocabulary.id)
                .limit(10)
            )
        )
        excerpt = "\n".join(
            (week.grammar, week.listening, week.reading_writing, week.speaking_outcome)
        )[:2500]
        try:
            result = await ask_course_tutor(
                api_key=settings.gemini_api_key.get_secret_value(),
                model=settings.gemini_model,
                topic=week.topic,
                source_excerpt=excerpt,
                question=question,
                course_words=words,
            )
        except GeminiTutorError as exc:
            raise ApiError(502, "tutor_error", str(exc)) from None
        session.add(
            AIUsage(
                owner_id=owner_id,
                month=now.strftime("%Y-%m"),
                request_date=now,
                provider="gemini",
                input_tokens=result.prompt_tokens,
                output_tokens=result.output_tokens,
            )
        )
        session.commit()
        return web.json_response({"answer": result.text, "week": week.week_number})


async def progress(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    with SessionLocal() as session:
        settings = session.get(UserSettings, owner_id)
        activities = list(
            session.scalars(
                select(Activity)
                .where(Activity.owner_id == owner_id)
                .order_by(Activity.completed_at.desc())
                .limit(50)
            )
        )
        scores = [item.score for item in activities if item.score is not None]
        writing = list(
            session.scalars(
                select(WritingAttempt)
                .where(WritingAttempt.owner_id == owner_id)
                .order_by(WritingAttempt.created_at.desc())
                .limit(5)
            )
        )
        return web.json_response(
            {
                "day": settings.current_day if settings else 1,
                "completed_days": settings.completed_days if settings else 0,
                "streak": settings.streak if settings else 0,
                "max_streak": settings.max_streak if settings else 0,
                "activity_count_returned": len(activities),
                "recent_activity": [
                    {
                        "kind": item.kind,
                        "day": item.day_number,
                        "topic": item.topic,
                        "score": item.score,
                        "completed_at": item.completed_at.isoformat(),
                    }
                    for item in activities
                ],
                "recent_writing_bands": [item.estimated_band for item in writing],
                "average_recent_activity_score": round(sum(scores) / len(scores), 1)
                if scores
                else None,
            }
        )


async def errors(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    with SessionLocal() as session:
        rows = list(
            session.scalars(
                select(ErrorLog)
                .where(ErrorLog.owner_id == owner_id)
                .order_by(ErrorLog.created_at.desc())
                .limit(100)
            )
        )
        return web.json_response(
            {
                "items": [
                    {
                        "id": row.id,
                        "topic": row.topic,
                        "exercise": row.exercise,
                        "wrong_answer": row.wrong_answer,
                        "correct_answer": row.correct_answer,
                        "error_type": row.error_type,
                        "explanation": row.explanation,
                        "resolved": row.resolved,
                        "created_at": row.created_at.isoformat(),
                    }
                    for row in rows
                ]
            }
        )


async def writing_evaluate(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    data = await _body(request)
    text = data.get("text")
    task_type = data.get("task_type", "auto")
    if not isinstance(text, str):
        raise ApiError(400, "invalid_text", "text must be a string.")
    if not isinstance(task_type, str) or len(task_type) > 30:
        raise ApiError(
            400, "invalid_task_type", "task_type must be a string of at most 30 characters."
        )
    if len(text) > get_settings().max_writing_chars:
        raise ApiError(413, "text_too_long", "Writing exceeds the configured character limit.")
    with SessionLocal() as session:
        try:
            result = await examine(session, owner_id, text, task_type)
        except BudgetExceeded:
            raise ApiError(
                429, "ai_budget_exceeded", "Writing evaluation limits have been reached."
            ) from None
        except ValueError as exc:
            raise ApiError(422, "invalid_writing", str(exc)) from None
        except RuntimeError as exc:
            # Config/budget errors are actionable and safe; provider details are not returned.
            message = str(exc)
            code = "ai_unavailable" if "OPENAI_API_KEY" in message else "ai_budget_unavailable"
            raise ApiError(503, code, "Writing evaluation is currently unavailable.") from None
        except Exception:
            logger.exception("Mini App writing evaluation failed for owner_id=%s", owner_id)
            raise ApiError(
                502, "ai_provider_error", "Writing evaluation failed. Please try again."
            ) from None
        return web.json_response(result.model_dump(mode="json"), status=201)


async def writing_attempts(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    raw_limit = request.query.get("limit", "20")
    try:
        limit = int(raw_limit)
    except ValueError:
        raise ApiError(400, "invalid_limit", "limit must be an integer from 1 to 50.") from None
    if not 1 <= limit <= 50:
        raise ApiError(400, "invalid_limit", "limit must be an integer from 1 to 50.")
    with SessionLocal() as session:
        attempts = list(
            session.scalars(
                select(WritingAttempt)
                .where(WritingAttempt.owner_id == owner_id)
                .order_by(WritingAttempt.created_at.desc(), WritingAttempt.id.desc())
                .limit(limit)
            )
        )
        return web.json_response(
            {
                "items": [
                    {
                        "id": attempt.id,
                        "task_type": attempt.task_type,
                        "estimated_band": attempt.estimated_band,
                        "created_at": attempt.created_at.isoformat(),
                        "text_available": attempt.submission_text is not None,
                    }
                    for attempt in attempts
                ]
            }
        )


async def writing_attempt_detail(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    try:
        attempt_id = int(request.match_info["attempt_id"])
    except ValueError:
        raise ApiError(404, "writing_attempt_not_found", "Writing attempt was not found.") from None
    with SessionLocal() as session:
        attempt = session.scalar(
            select(WritingAttempt).where(
                WritingAttempt.id == attempt_id, WritingAttempt.owner_id == owner_id
            )
        )
        if attempt is None:
            raise ApiError(404, "writing_attempt_not_found", "Writing attempt was not found.")
        return web.json_response(
            {
                "id": attempt.id,
                "task_type": attempt.task_type,
                "estimated_band": attempt.estimated_band,
                "created_at": attempt.created_at.isoformat(),
                "submission_text": attempt.submission_text,
                "feedback": json.loads(attempt.feedback_json),
            }
        )


async def notification_settings(request: web.Request) -> web.Response:
    owner_id = _owner(request)
    if request.method == "GET":
        with SessionLocal() as session:
            row = _settings(session, owner_id)
            payload = {
                "reminders_enabled": row.reminders_enabled,
                "quiet_mode": row.quiet_mode,
                "reminder_time": row.reminder_time,
                "timezone": get_settings().timezone,
            }
            session.commit()
            return web.json_response(payload)
    data = await _body(request)
    allowed = {"reminders_enabled", "quiet_mode", "reminder_time"}
    if not data or set(data) - allowed:
        raise ApiError(
            400, "invalid_settings", "Provide one or more supported notification settings."
        )
    for key in ("reminders_enabled", "quiet_mode"):
        if key in data and type(data[key]) is not bool:
            raise ApiError(400, "invalid_settings", f"{key} must be a boolean.")
    if "reminder_time" in data and (
        not isinstance(data["reminder_time"], str) or not _TIME_RE.fullmatch(data["reminder_time"])
    ):
        raise ApiError(400, "invalid_settings", "reminder_time must use HH:MM 24-hour format.")
    with SessionLocal() as session:
        row = _settings(session, owner_id)
        for key in data:
            setattr(row, key, data[key])
        session.commit()
        return web.json_response(
            {
                "reminders_enabled": row.reminders_enabled,
                "quiet_mode": row.quiet_mode,
                "reminder_time": row.reminder_time,
                "timezone": get_settings().timezone,
            }
        )


def register_routes(app: web.Application) -> None:
    """Register Mini App routes on the host aiohttp app after auth middleware."""
    app.router.add_get(f"{API_PREFIX}/bootstrap", bootstrap)
    app.router.add_get(f"{API_PREFIX}/lesson/current", current_lesson)
    app.router.add_get(f"{API_PREFIX}/course/roadmap", course_roadmap)
    app.router.add_post(
        f"{API_PREFIX}/lesson/{{day_number:\\d+}}/tasks/{{task_key}}/complete",
        complete_lesson_task,
    )
    app.router.add_post(f"{API_PREFIX}/quiz/sessions", quiz_start)
    app.router.add_get(f"{API_PREFIX}/quiz/sessions/{{quiz_id}}", quiz_get)
    app.router.add_put(f"{API_PREFIX}/quiz/sessions/{{quiz_id}}/answers", quiz_answer)
    app.router.add_post(f"{API_PREFIX}/quiz/sessions/{{quiz_id}}/submit", quiz_submit)
    app.router.add_post(f"{API_PREFIX}/exam/sessions", exam_start)
    app.router.add_get(f"{API_PREFIX}/exam/sessions/{{exam_id}}", exam_get)
    app.router.add_put(f"{API_PREFIX}/exam/sessions/{{exam_id}}/answers", exam_answer)
    app.router.add_post(f"{API_PREFIX}/exam/sessions/{{exam_id}}/submit", exam_submit)
    app.router.add_get(f"{API_PREFIX}/vocabulary/due", vocabulary_due)
    app.router.add_get(f"{API_PREFIX}/vocabulary/library", vocabulary_library)
    app.router.add_get(f"{API_PREFIX}/vocabulary/today", vocabulary_today)
    app.router.add_post(f"{API_PREFIX}/vocabulary/{{word_id}}/review", vocabulary_review)
    app.router.add_post(f"{API_PREFIX}/learning/tutor", learning_tutor)
    app.router.add_get(f"{API_PREFIX}/progress", progress)
    app.router.add_get(f"{API_PREFIX}/errors", errors)
    app.router.add_post(f"{API_PREFIX}/writing/evaluate", writing_evaluate)
    app.router.add_get(f"{API_PREFIX}/writing/attempts", writing_attempts)
    app.router.add_get(f"{API_PREFIX}/writing/attempts/{{attempt_id}}", writing_attempt_detail)
    app.router.add_get(f"{API_PREFIX}/settings/notifications", notification_settings)
    app.router.add_patch(f"{API_PREFIX}/settings/notifications", notification_settings)
