from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import Vocabulary

INTERVALS = (1, 3, 7, 14, 30)


def add_word(
    session: Session,
    english: str,
    translation: str,
    *,
    owner_id: int | None = None,
    transcription: str = "",
    example: str = "",
    topic: str = "",
) -> Vocabulary:
    word = Vocabulary(
        english=english.strip(),
        translation=translation.strip(),
        owner_id=owner_id,
        transcription=transcription.strip(),
        example=example.strip(),
        topic=topic.strip(),
    )
    session.add(word)
    session.commit()
    session.refresh(word)
    return word


def due_words(session: Session, limit: int = 20, owner_id: int | None = None) -> list[Vocabulary]:
    query = select(Vocabulary).where(Vocabulary.next_review <= date.today())
    if owner_id is not None:
        query = query.where((Vocabulary.owner_id == owner_id) | Vocabulary.owner_id.is_(None))
    query = query.order_by(Vocabulary.next_review, Vocabulary.mastery).limit(max(1, min(limit, 50)))
    return list(session.scalars(query))


def record_review(session: Session, word: Vocabulary, correct: bool) -> Vocabulary:
    if correct:
        word.correct_count += 1
        index = (
            min(INTERVALS.index(word.interval_days) + 1, len(INTERVALS) - 1)
            if word.interval_days in INTERVALS
            else 1
        )
        word.interval_days = INTERVALS[index]
        word.mastery = min(1.0, word.mastery + 0.15)
    else:
        word.error_count += 1
        word.interval_days = INTERVALS[0]
        word.mastery = max(0.0, word.mastery - 0.2)
    word.next_review = date.today() + timedelta(days=word.interval_days)
    session.commit()
    return word


def search_words(session: Session, query: str, owner_id: int | None = None) -> list[Vocabulary]:
    needle = f"%{query.strip()}%"
    stmt = select(Vocabulary).where(
        (Vocabulary.english.ilike(needle)) | (Vocabulary.translation.ilike(needle))
    )
    if owner_id is not None:
        stmt = stmt.where((Vocabulary.owner_id == owner_id) | Vocabulary.owner_id.is_(None))
    return list(session.scalars(stmt.limit(30)))


def vocabulary_count(session: Session, owner_id: int | None = None) -> int:
    stmt = select(func.count(Vocabulary.id))
    if owner_id is not None:
        stmt = stmt.where((Vocabulary.owner_id == owner_id) | Vocabulary.owner_id.is_(None))
    return int(session.scalar(stmt) or 0)
