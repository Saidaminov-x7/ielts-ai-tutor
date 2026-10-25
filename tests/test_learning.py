from datetime import date

from app.database.models import (
    Activity,
    CourseDay,
    CourseDayVocabulary,
    CourseWeek,
    Vocabulary,
)
from app.learning.adaptive import adapt_day, recommendation, weak_topics
from app.learning.daily_tests import (
    QUESTIONS,
    WEEKLY_QUESTIONS,
    answer_quiz,
    grade_quiz,
    start_quiz,
    submit_quiz,
)
from app.learning.lessons import TASKS, complete_task, finish_day, lesson_summary
from app.learning.vocabulary import (
    due_words,
    mark_course_day_reviewed,
    record_review,
    record_review_for_owner,
)
from app.learning.weekly_exams import record_exam_answer, start_exam, submit_exam


def test_progress_only_finishes_after_every_task(session):
    session.add(
        CourseDay(
            day_number=1,
            week_number=1,
            topic="Present simple",
            grammar="Present simple practice",
            reading="Short reading text",
            listening="Listening transcript",
            writing="Writing prompt",
            objectives="Review exercises",
        )
    )
    session.add(
        Vocabulary(
            english="practice",
            translation="упражняться",
            owner_id=101,
            course_day=1,
        )
    )
    session.commit()
    task_rows = lesson_summary(session, 101)["tasks"]
    available_keys = {row["key"] for row in task_rows if row["available"]}
    assert len(available_keys) == len(TASKS) - 1  # No prior lesson exists for day-one review.
    assert lesson_summary(session, 101)["remaining"] == len(available_keys)
    assert complete_task(session, 101, 1, "grammar")
    assert not finish_day(session, 101, 1)
    for key in available_keys:
        complete_task(session, 101, 1, key)
    assert finish_day(session, 101, 1)
    assert lesson_summary(session, 101)["day"] == 2


def test_missing_course_has_no_completable_blocks(session):
    assert lesson_summary(session, 101)["remaining"] == 0
    assert all(not row["available"] for row in lesson_summary(session, 101)["tasks"])
    assert not complete_task(session, 101, 1, "quiz")
    assert not finish_day(session, 101, 1)


def test_course_day_is_not_done_until_every_assigned_card_is_recalled(session):
    session.add(CourseWeek(week_number=1, month=1, topic="Introductions"))
    cards = [
        Vocabulary(
            english=f"word-{number}",
            translation=f"перевод-{number}",
            source_key=f"pdf:{number:03d}",
            course_week=1,
            topic="Introductions",
        )
        for number in range(1, 6)
    ]
    session.add_all(cards)
    session.commit()

    summary = lesson_summary(session, 101, 1)
    task = summary["tasks"][0]
    assert summary["week"] == 1 and summary["day"] == 1
    assert task["available"] and not task["done"]
    assert task["new_cards"] == 5
    assert session.query(CourseDayVocabulary).filter_by(owner_id=101, day_number=1).count() == 5
    assert not any(
        assignment.reviewed
        for assignment in session.query(CourseDayVocabulary).filter_by(
            owner_id=101, day_number=1
        )
    )
    assert not due_words(session, owner_id=202)
    assert not complete_task(session, 101, 1, "vocabulary")

    for card in cards:
        record_review_for_owner(session, card, 101, True)
        mark_course_day_reviewed(session, 101, 1, card)
    assert complete_task(session, 101, 1, "vocabulary")
    assert finish_day(session, 101, 1)
    assert lesson_summary(session, 101, 1)["tasks"][0]["done"]


def test_review_only_sunday_can_complete_when_no_cards_are_due(session):
    session.add(CourseWeek(week_number=1, month=1, topic="Introductions"))
    session.commit()

    summary = lesson_summary(session, 101, 7)
    task = summary["tasks"][0]
    assert summary["day"] == 7
    assert task["available"] and not task["done"]
    assert task["due_cards"] == 0
    assert complete_task(session, 101, 7, "review")
    assert finish_day(session, 101, 7)


def test_unassigned_course_cards_are_not_in_any_learners_due_queue(session):
    session.add_all(
        [
            Vocabulary(
                english=f"catalogue-{number}",
                translation=f"слово-{number}",
                source_key=f"pdf:{number:03d}",
                course_week=1,
            )
            for number in range(1, 31)
        ]
    )
    session.commit()

    assert due_words(session, owner_id=101) == []
    assert due_words(session, owner_id=202) == []


def test_vocabulary_spaced_repetition_and_owner_filter(session):
    word = Vocabulary(english="apple", translation="яблоко", owner_id=101, next_review=date.today())
    other = Vocabulary(english="pear", translation="груша", owner_id=202, next_review=date.today())
    session.add_all([word, other])
    session.commit()
    assert [x.english for x in due_words(session, owner_id=101)] == ["apple"]
    record_review(session, word, True)
    assert word.interval_days == 3
    record_review(session, word, False)
    assert word.interval_days == 1 and word.error_count == 1


def test_quiz_is_python_graded_and_logs_errors(session):
    result = grade_quiz(session, 101, 1, [q["answer"] for q in QUESTIONS])
    assert result["score"] == result["total"] == 10
    assert result["percent"] == 100
    result = grade_quiz(session, 202, 1, [])
    assert result["score"] == 0


def test_adaptive_accuracy_uses_real_activity(session):
    session.add_all(
        [
            Activity(owner_id=5, kind="quiz", topic="Present perfect", score=45),
            Activity(owner_id=5, kind="quiz", topic="Present perfect", score=55),
        ]
    )
    session.commit()
    assert recommendation(59.9) == "Повторное изучение"
    assert weak_topics(session, 5)[0].accuracy == 50


def test_adaptive_lesson_uses_lowest_observed_topic_score(session):
    session.add_all(
        [
            Activity(owner_id=5, kind="quiz", topic="Present Simple", score=92),
            Activity(owner_id=5, kind="quiz", topic="Present Perfect", score=48),
        ]
    )
    session.commit()

    assert "слабую тему" in adapt_day(session, 5, 12)


def test_weekly_exam_records_answers_and_submits(session):
    exam = start_exam(session, 101, 1, duration_minutes=30)
    assert record_exam_answer(session, exam, 0, QUESTIONS[0]["answer"])
    result = submit_exam(session, exam)
    assert result["total"] == len(WEEKLY_QUESTIONS) and result["score"] == 1
    assert not record_exam_answer(session, exam, 0, 0)


def test_daily_quiz_persists_answers_and_result(session):
    attempt = start_quiz(session, 101, 1)
    assert answer_quiz(session, attempt, 0, QUESTIONS[1]["answer"])
    for index in range(1, 10):
        answer_quiz(session, attempt, index, -1)
    result = submit_quiz(session, attempt)
    assert result["total"] == 10 and result["score"] == 1
    assert submit_quiz(session, attempt)["score"] == 1


def test_srs_review_session_is_owner_bound_and_persistent(session):
    import json

    from app.database.models import ReviewSession

    word = Vocabulary(english="learn", translation="учить", owner_id=101, next_review=date.today())
    session.add(word)
    session.commit()
    attempt = ReviewSession(owner_id=101, word_ids_json=json.dumps([word.id]), cursor=0)
    session.add(attempt)
    session.commit()
    assert attempt.owner_id == 101 and attempt.cursor == 0
    assert json.loads(attempt.word_ids_json) == [word.id]
