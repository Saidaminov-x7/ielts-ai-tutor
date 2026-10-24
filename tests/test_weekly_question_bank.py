import json

from app.learning.daily_tests import QUESTIONS, WEEKLY_QUESTIONS, daily_quiz
from app.learning.weekly_exams import start_exam


def test_weekly_exam_uses_expanded_bank_without_changing_daily_quiz(session):
    exam = start_exam(session, owner_id=101, week=1)

    assert json.loads(exam.questions_json) == WEEKLY_QUESTIONS
    assert len(WEEKLY_QUESTIONS) > len(QUESTIONS)

    daily_questions = daily_quiz(session, owner_id=202, day=1)
    assert len(daily_questions) == len(QUESTIONS)
    assert [question["question"] for question in daily_questions] == [
        question["question"] for question in QUESTIONS
    ]


def test_weekly_bank_multiple_choice_items_have_unambiguous_grammar():
    passive_question = next(
        question for question in WEEKLY_QUESTIONS if "The new library" in question["question"]
    )
    assert "by the city council" in passive_question["question"]
    assert passive_question["options"][passive_question["answer"]] == "will be opened"

    quantifier_question = next(
        question for question in WEEKLY_QUESTIONS if "optional course" in question["question"]
    )
    assert quantifier_question["question"].startswith("___ students")
    assert quantifier_question["options"][quantifier_question["answer"]] == "few"
