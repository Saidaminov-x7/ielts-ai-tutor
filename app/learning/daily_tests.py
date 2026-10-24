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

# A validated local question bank for weekly practice. Keeping this content in
# code means the exam remains usable when the optional course workbook has not
# been imported. Questions are objective and graded locally.
WEEKLY_QUESTIONS = QUESTIONS + [
    {
        "topic": "Present Perfect",
        "question": "I ___ in Tashkent since 2020.",
        "options": ["live", "lived", "have lived", "am living"],
        "answer": 2,
        "explanation": "Since with a continuing situation uses the present perfect.",
    },
    {
        "topic": "Present Perfect",
        "question": "Have you ever ___ sushi?",
        "options": ["eat", "ate", "eaten", "eating"],
        "answer": 2,
        "explanation": "The present perfect takes the past participle: eaten.",
    },
    {
        "topic": "Past Continuous",
        "question": "I ___ when the phone rang.",
        "options": ["studied", "was studying", "am studying", "have studied"],
        "answer": 1,
        "explanation": (
            "Past continuous describes an action in progress interrupted by another past event."
        ),
    },
    {
        "topic": "Past Perfect",
        "question": "The train ___ before we reached the station.",
        "options": ["leaves", "has left", "had left", "was leaving"],
        "answer": 2,
        "explanation": "Past perfect marks the earlier of two past events.",
    },
    {
        "topic": "Future forms",
        "question": "Look at those clouds! It ___ soon.",
        "options": ["rains", "will have rained", "is going to rain", "would rain"],
        "answer": 2,
        "explanation": "Be going to is natural for a prediction based on present evidence.",
    },
    {
        "topic": "First Conditional",
        "question": "If you ___ now, you will catch the bus.",
        "options": ["leave", "will leave", "left", "would leave"],
        "answer": 0,
        "explanation": "The first conditional uses present simple in the if-clause.",
    },
    {
        "topic": "Second Conditional",
        "question": "If I ___ more free time, I would learn Spanish.",
        "options": ["have", "will have", "had", "would have"],
        "answer": 2,
        "explanation": "The second conditional uses past simple after if.",
    },
    {
        "topic": "Third Conditional",
        "question": "If she had set an alarm, she ___ the meeting.",
        "options": ["would not miss", "would not have missed", "did not miss", "will not miss"],
        "answer": 1,
        "explanation": "The third conditional uses would have plus a past participle.",
    },
    {
        "topic": "Passive Voice",
        "question": "The new library ___ by the city council next year.",
        "options": ["will open", "will be opened", "opens", "has opening"],
        "answer": 1,
        "explanation": "The passive future is will be plus a past participle.",
    },
    {
        "topic": "Passive Voice",
        "question": "This painting ___ by a local artist in 1998.",
        "options": ["created", "was created", "has created", "is creating"],
        "answer": 1,
        "explanation": "Use past simple passive for a completed past action with an agent.",
    },
    {
        "topic": "Reported Speech",
        "question": "He said that he ___ tired.",
        "options": ["is", "was", "will be", "has been"],
        "answer": 1,
        "explanation": (
            "In standard reported speech, present simple commonly shifts back to past simple."
        ),
    },
    {
        "topic": "Relative Clauses",
        "question": "The woman ___ lives next door is a doctor.",
        "options": ["which", "whose", "who", "where"],
        "answer": 2,
        "explanation": (
            "Who refers to a person performing the action in a defining relative clause."
        ),
    },
    {
        "topic": "Relative Clauses",
        "question": "That's the café ___ we first met.",
        "options": ["who", "which", "where", "whose"],
        "answer": 2,
        "explanation": "Where introduces a relative clause about a place.",
    },
    {
        "topic": "Gerunds and Infinitives",
        "question": "They decided ___ the earlier train.",
        "options": ["take", "taking", "to take", "taken"],
        "answer": 2,
        "explanation": "Decide is followed by a to-infinitive.",
    },
    {
        "topic": "Gerunds and Infinitives",
        "question": "She avoids ___ late at night.",
        "options": ["drive", "to drive", "driving", "drove"],
        "answer": 2,
        "explanation": "Avoid is followed by a gerund.",
    },
    {
        "topic": "Articles",
        "question": "Mount Everest is ___ highest mountain in the world.",
        "options": ["a", "an", "the", "no article"],
        "answer": 2,
        "explanation": "Superlative adjectives normally take the.",
    },
    {
        "topic": "Articles",
        "question": "My brother is ___ engineer.",
        "options": ["a", "an", "the", "no article"],
        "answer": 1,
        "explanation": "Engineer begins with a vowel sound, so use an.",
    },
    {
        "topic": "Quantifiers",
        "question": "There is ___ information in the report to answer the question.",
        "options": ["too many", "enough", "few", "many"],
        "answer": 1,
        "explanation": "Information is uncountable; enough can describe a sufficient amount.",
    },
    {
        "topic": "Quantifiers",
        "question": "___ students chose the optional course, so it was cancelled.",
        "options": ["a few", "few", "a little", "much"],
        "answer": 1,
        "explanation": "Few with a plural countable noun means not enough.",
    },
    {
        "topic": "Comparatives",
        "question": "This explanation is ___ than the one in the textbook.",
        "options": ["clear", "clearest", "more clear", "clearer"],
        "answer": 3,
        "explanation": "The comparative of the short adjective clear is clearer.",
    },
    {
        "topic": "Comparatives",
        "question": "The more you practise, ___ you become.",
        "options": ["the confident", "more confident", "the more confident", "most confident"],
        "answer": 2,
        "explanation": "This correlative structure is the more..., the more...",
    },
    {
        "topic": "Modal Verbs",
        "question": "You ___ submit the form by Friday; it is a strict requirement.",
        "options": ["might", "must", "would", "could"],
        "answer": 1,
        "explanation": "Must expresses a strong obligation.",
    },
    {
        "topic": "Modal Verbs",
        "question": "She ___ be at home; all the lights are off and her car is gone.",
        "options": ["must", "can't", "should", "has to"],
        "answer": 1,
        "explanation": "Can't expresses a strong negative deduction from evidence.",
    },
    {
        "topic": "Prepositions",
        "question": "The research focuses ___ the effects of sleep on memory.",
        "options": ["at", "in", "on", "for"],
        "answer": 2,
        "explanation": "The collocation is focus on something.",
    },
    {
        "topic": "Prepositions",
        "question": "She is responsible ___ organising the event.",
        "options": ["of", "for", "to", "with"],
        "answer": 1,
        "explanation": "The adjective responsible is followed by for.",
    },
    {
        "topic": "Linking Words",
        "question": "The sample was small; ___, the results should be treated cautiously.",
        "options": ["however", "therefore", "for example", "meanwhile"],
        "answer": 1,
        "explanation": "Therefore introduces a result or conclusion.",
    },
    {
        "topic": "Linking Words",
        "question": "___ the high cost, the project went ahead.",
        "options": ["Although", "Despite", "Because", "However"],
        "answer": 1,
        "explanation": "Despite is followed by a noun phrase, not a full clause.",
    },
    {
        "topic": "Word Formation",
        "question": "The study provides ___ evidence for the theory.",
        "options": ["convince", "convinced", "convincing", "convincingly"],
        "answer": 2,
        "explanation": "An adjective is needed before the noun evidence.",
    },
    {
        "topic": "Word Formation",
        "question": "Regular exercise can improve both physical and mental ___.",
        "options": ["healthy", "health", "healthily", "healthier"],
        "answer": 1,
        "explanation": "A noun is needed after both and before the implied condition/state.",
    },
    {
        "topic": "Collocations",
        "question": "The government plans to ___ a survey on public transport.",
        "options": ["make", "do", "conduct", "perform up"],
        "answer": 2,
        "explanation": "Conduct a survey is the standard academic collocation.",
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
