import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Activity, ErrorLog, ExamSession, QuizAttempt
from app.learning.daily_tests import WEEKLY_QUESTIONS


def start_exam(
    session: Session, owner_id: int, week: int, duration_minutes: int = 30
) -> ExamSession:
    now = datetime.now(UTC)
    exam = ExamSession(
        owner_id=owner_id,
        week_number=week,
        questions_json=json.dumps(WEEKLY_QUESTIONS, ensure_ascii=False),
        answers_json="{}",
        started_at=now,
        deadline=now + timedelta(minutes=duration_minutes),
    )
    session.add(exam)
    session.commit()
    session.refresh(exam)
    return exam


def record_exam_answer(session: Session, exam: ExamSession, question: int, answer: int) -> bool:
    if exam.submitted_at is not None or datetime.now(UTC) > exam.deadline.replace(tzinfo=UTC):
        return False
    questions = json.loads(exam.questions_json)
    if not 0 <= question < len(questions) or not 0 <= answer < len(questions[question]["options"]):
        return False
    answers = json.loads(exam.answers_json)
    answers[str(question)] = answer
    exam.answers_json = json.dumps(answers)
    session.commit()
    return True


def submit_exam(session: Session, exam: ExamSession) -> dict:
    questions = json.loads(exam.questions_json)
    answers = json.loads(exam.answers_json)
    score = 0
    for index, question in enumerate(questions):
        answer = answers.get(str(index), -1)
        correct = answer == question["answer"]
        score += int(correct)
        if not correct:
            session.add(
                ErrorLog(
                    owner_id=exam.owner_id,
                    topic=question["topic"],
                    exercise=question["question"],
                    wrong_answer=question["options"][answer] if answer >= 0 else "Нет ответа",
                    correct_answer=question["options"][question["answer"]],
                    explanation=question["explanation"],
                )
            )
    now = datetime.now(UTC)
    exam.submitted_at = now
    exam.score = score
    total = len(questions)
    session.add(
        QuizAttempt(
            owner_id=exam.owner_id,
            day_number=min(210, exam.week_number * 7),
            score=score,
            total=total,
            answers_json=exam.answers_json,
        )
    )
    session.add(
        Activity(
            owner_id=exam.owner_id,
            day_number=min(210, exam.week_number * 7),
            kind="weekly_exam",
            topic="Еженедельный экзамен",
            score=score / total * 100,
        )
    )
    session.commit()
    return {
        "score": score,
        "total": total,
        "week": exam.week_number,
        "note": "Учебная проверка знаний; не является официальным пробным IELTS.",
    }


def weekly_exam(session: Session, owner_id: int, week: int) -> ExamSession:
    return start_exam(session, owner_id, week)


def weekly_history(session: Session, owner_id: int) -> list[QuizAttempt]:
    return list(
        session.scalars(
            select(QuizAttempt)
            .where(QuizAttempt.owner_id == owner_id)
            .order_by(QuizAttempt.created_at.desc())
            .limit(20)
        )
    )
