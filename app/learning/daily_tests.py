import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Activity, ErrorLog, QuizAttempt, QuizSession

# Verified objective questions only; add course-specific questions from validated course data.
QUESTIONS = [
    {
        "topic": "Present Simple",
        "question": "She ___ to work every day.",
        "options": ["go", "goes", "going", "gone"],
        "answer": 1,
        "explanation": "В 3-м лице ед. числа добавляется -s.",
    },
    {
        "topic": "Past Simple",
        "question": "Yesterday, we ___ a film.",
        "options": ["watch", "watched", "watches", "watching"],
        "answer": 1,
        "explanation": "Yesterday указывает на Past Simple.",
    },
    {
        "topic": "Articles",
        "question": "I saw ___ elephant.",
        "options": ["a", "an", "the", "—"],
        "answer": 1,
        "explanation": "Перед гласным звуком используется an.",
    },
    {
        "topic": "Present Continuous",
        "question": "They ___ dinner now.",
        "options": ["have", "has", "are having", "had"],
        "answer": 2,
        "explanation": "Now указывает на Present Continuous.",
    },
    {
        "topic": "Prepositions",
        "question": "The book is ___ the table.",
        "options": ["on", "at", "by", "for"],
        "answer": 0,
        "explanation": "On the table — на поверхности стола.",
    },
    {
        "topic": "Countable nouns",
        "question": "How ___ apples do you need?",
        "options": ["much", "many", "any", "a"],
        "answer": 1,
        "explanation": "Many используется с исчисляемыми существительными.",
    },
    {
        "topic": "Future",
        "question": "I think it ___ rain tomorrow.",
        "options": ["will", "is", "did", "has"],
        "answer": 0,
        "explanation": "Will используется для прогноза.",
    },
    {
        "topic": "Comparatives",
        "question": "This road is ___ than that one.",
        "options": ["long", "longer", "longest", "more long"],
        "answer": 1,
        "explanation": "Короткое прилагательное: longer than.",
    },
    {
        "topic": "Pronouns",
        "question": "This is Anna. ___ is my friend.",
        "options": ["He", "She", "It", "They"],
        "answer": 1,
        "explanation": "Для Anna используется местоимение she.",
    },
    {
        "topic": "Modal verbs",
        "question": "You ___ wear a seat belt. It is the law.",
        "options": ["must", "might", "would", "could"],
        "answer": 0,
        "explanation": "Must выражает обязанность.",
    },
]


def daily_quiz(session: Session, owner_id: int, day: int) -> list[dict]:
    attempts = list(
        session.scalars(
            select(QuizAttempt)
            .where(QuizAttempt.owner_id == owner_id)
            .order_by(QuizAttempt.created_at.desc())
            .limit(10)
        )
    )
    recent = {item for attempt in attempts for item in json.loads(attempt.answers_json or "[]")}
    offset = (day - 1) % len(QUESTIONS)
    rotated = QUESTIONS[offset:] + QUESTIONS[:offset]
    unseen = [i for i in range(len(rotated)) if f"{day}:{i}" not in recent]
    return [{**rotated[i], "id": i} for i in (unseen or list(range(len(rotated))))]


def grade_quiz(session: Session, owner_id: int, day: int, answers: list[int]) -> dict:
    questions = daily_quiz(session, owner_id, day)
    score = 0
    results = []
    for index, question in enumerate(questions):
        answer = answers[index] if index < len(answers) else -1
        correct = answer == question["answer"]
        score += int(correct)
        results.append(
            {"topic": question["topic"], "correct": correct, "explanation": question["explanation"]}
        )
        if not correct:
            session.add(
                ErrorLog(
                    owner_id=owner_id,
                    topic=question["topic"],
                    exercise=question["question"],
                    wrong_answer=str(answer),
                    correct_answer=question["options"][question["answer"]],
                    explanation=question["explanation"],
                )
            )
    session.add(
        QuizAttempt(
            owner_id=owner_id,
            day_number=day,
            score=score,
            total=len(questions),
            answers_json=json.dumps([f"{day}:{i}" for i in range(len(questions))]),
        )
    )
    session.add(
        Activity(
            owner_id=owner_id,
            day_number=day,
            kind="quiz",
            topic="Смешанный мини-тест",
            score=score / len(questions) * 100,
        )
    )
    session.commit()
    return {
        "score": score,
        "total": len(questions),
        "percent": round(score / len(questions) * 100),
        "results": results,
    }


def start_quiz(session: Session, owner_id: int, day: int) -> QuizSession:
    questions = daily_quiz(session, owner_id, day)
    attempt = QuizSession(
        owner_id=owner_id,
        day_number=day,
        questions_json=json.dumps(questions, ensure_ascii=False),
        answers_json="{}",
    )
    session.add(attempt)
    session.commit()
    session.refresh(attempt)
    return attempt


def answer_quiz(session: Session, quiz: QuizSession, question_idx: int, answer_idx: int) -> bool:
    if quiz.submitted_at is not None:
        return False
    questions = json.loads(quiz.questions_json)
    if not 0 <= question_idx < len(questions):
        return False
    if not 0 <= answer_idx < len(questions[question_idx]["options"]):
        return False
    answers = json.loads(quiz.answers_json)
    answers[str(question_idx)] = answer_idx
    quiz.answers_json = json.dumps(answers)
    session.commit()
    return True


def submit_quiz(session: Session, quiz: QuizSession) -> dict:
    if quiz.submitted_at is not None:
        return {
            "score": quiz.score or 0,
            "total": len(json.loads(quiz.questions_json)),
            "percent": round((quiz.score or 0) / len(json.loads(quiz.questions_json)) * 100),
            "results": [],
        }
    questions = json.loads(quiz.questions_json)
    answers = json.loads(quiz.answers_json)
    answer_list = [answers.get(str(idx), -1) for idx in range(len(questions))]
    result = grade_quiz(session, quiz.owner_id, quiz.day_number, answer_list)
    quiz.submitted_at = datetime.now(UTC)
    quiz.score = result["score"]
    session.commit()
    return result
