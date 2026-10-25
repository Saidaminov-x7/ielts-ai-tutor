from datetime import UTC, date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database.models import CourseDayVocabulary, Vocabulary, VocabularyProgress

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
    source_key: str | None = None,
    course_week: int | None = None,
    pronunciation_hint: str = "",
    collocation: str = "",
    collocation_translation: str = "",
    collocation_transcription: str = "",
    collocation_pronunciation_hint: str = "",
) -> Vocabulary:
    word = Vocabulary(
        english=english.strip(),
        translation=translation.strip(),
        owner_id=owner_id,
        transcription=transcription.strip(),
        example=example.strip(),
        topic=topic.strip(),
        source_key=source_key,
        course_week=course_week,
        pronunciation_hint=pronunciation_hint.strip(),
        collocation=collocation.strip(),
        collocation_translation=collocation_translation.strip(),
        collocation_transcription=collocation_transcription.strip(),
        collocation_pronunciation_hint=collocation_pronunciation_hint.strip(),
    )
    session.add(word)
    session.commit()
    session.refresh(word)
    return word


def _progress(session: Session, owner_id: int, word: Vocabulary) -> VocabularyProgress:
    state = session.scalar(
        select(VocabularyProgress).where(
            VocabularyProgress.owner_id == owner_id,
            VocabularyProgress.vocabulary_id == word.id,
        )
    )
    if owner_id == -1:
        if state is None:
            state = VocabularyProgress(
                owner_id=-1,
                vocabulary_id=word.id,
                next_review=date.today(),
                interval_days=0,
                correct_count=0,
                error_count=0,
                mastery=0,
            )
            session.add(state)
            session.flush()
        return state
    if state is None:
        learned_at = (
            word.learned_at.replace(tzinfo=UTC)
            if word.learned_at.tzinfo is None
            else word.learned_at
        )
        is_catalogue_card = word.source_key is not None
        interval = (
            0
            if is_catalogue_card
            else word.interval_days
            if learned_at.date() < date.today()
            else 0
        )
        state = VocabularyProgress(
            owner_id=owner_id,
            vocabulary_id=word.id,
            next_review=word.next_review if interval else date.today(),
            interval_days=interval,
            correct_count=0 if is_catalogue_card else word.correct_count,
            error_count=0 if is_catalogue_card else word.error_count,
            mastery=0 if is_catalogue_card else word.mastery,
        )
        session.add(state)
        session.flush()
    return state


def due_words(session: Session, limit: int = 20, owner_id: int | None = None) -> list[Vocabulary]:
    query = select(Vocabulary)
    if owner_id is not None:
        query = query.where((Vocabulary.owner_id == owner_id) | Vocabulary.owner_id.is_(None))
        query = query.outerjoin(
            VocabularyProgress,
            (VocabularyProgress.vocabulary_id == Vocabulary.id)
            & (VocabularyProgress.owner_id == owner_id),
        )
        query = query.where(
            or_(
                (
                    Vocabulary.source_key.is_(None)
                    & VocabularyProgress.id.is_(None)
                    & (Vocabulary.next_review <= date.today())
                ),
                (
                    VocabularyProgress.id.is_not(None)
                    & (VocabularyProgress.next_review <= date.today())
                ),
            )
        )
        query = query.order_by(Vocabulary.english)
    else:
        query = query.where(Vocabulary.next_review <= date.today()).order_by(
            Vocabulary.next_review, Vocabulary.mastery
        )
    return list(session.scalars(query.limit(max(1, min(limit, 50)))))


def words_for_day(
    session: Session, owner_id: int, week: int, sequences: tuple[int, ...], day: int
) -> list[Vocabulary]:
    if not sequences:
        return []
    rows = list(
        session.scalars(
            select(Vocabulary)
            .where(
                Vocabulary.course_week == week,
                Vocabulary.owner_id.is_(None),
                Vocabulary.source_key.in_([f"pdf:{number:03d}" for number in sequences]),
            )
            .order_by(Vocabulary.source_key)
        )
    )
    for row in rows:
        assignment = session.scalar(
            select(CourseDayVocabulary).where(
                CourseDayVocabulary.owner_id == owner_id,
                CourseDayVocabulary.day_number == day,
                CourseDayVocabulary.vocabulary_id == row.id,
            )
        )
        if assignment is None:
            assignment = CourseDayVocabulary(
                owner_id=owner_id,
                day_number=day,
                vocabulary_id=row.id,
            )
            session.add(assignment)
        # Assigning a card to today's lesson is not evidence that the learner
        # studied or recalled it. The review flow marks it after an answer.
    for row in rows:
        _progress(session, owner_id, row)
    session.commit()
    return rows


def record_review(
    session: Session, word: Vocabulary, correct: bool
) -> Vocabulary | VocabularyProgress:
    return _record_legacy(session, word, correct)


def record_review_for_owner(
    session: Session, word: Vocabulary, owner_id: int, correct: bool
) -> VocabularyProgress:
    return _record_progress(session, _progress(session, owner_id, word), correct)


def mark_course_day_reviewed(session: Session, owner_id: int, day: int, word: Vocabulary) -> None:
    assignment = session.scalar(
        select(CourseDayVocabulary).where(
            CourseDayVocabulary.owner_id == owner_id,
            CourseDayVocabulary.day_number == day,
            CourseDayVocabulary.vocabulary_id == word.id,
        )
    )
    if assignment is None:
        assignment = CourseDayVocabulary(owner_id=owner_id, day_number=day, vocabulary_id=word.id)
        session.add(assignment)
    assignment.reviewed = True
    session.flush()


def words_due_for_course_day(
    session: Session, owner_id: int, week: int, day: int, limit: int = 50
) -> list[Vocabulary]:
    assigned = set(
        session.scalars(
            select(CourseDayVocabulary.vocabulary_id).where(
                CourseDayVocabulary.owner_id == owner_id,
                CourseDayVocabulary.day_number == day,
            )
        )
    )
    due = [
        word
        for word in due_words(session, limit=limit, owner_id=owner_id)
        if word.course_week is not None and word.course_week <= week
    ]
    selected = [word for word in due if word.id not in assigned]
    for word in selected:
        session.add(
            CourseDayVocabulary(
                owner_id=owner_id,
                day_number=day,
                vocabulary_id=word.id,
            )
        )
    session.commit()
    return selected


def _record_progress(
    session: Session, state: VocabularyProgress, correct: bool
) -> VocabularyProgress:
    if correct:
        state.correct_count += 1
        index = INTERVALS.index(state.interval_days) + 1 if state.interval_days in INTERVALS else -1
        state.interval_days = INTERVALS[min(index, len(INTERVALS) - 1)]
        state.mastery = min(1.0, state.mastery + 0.15)
    else:
        state.error_count += 1
        state.interval_days = INTERVALS[0]
        state.mastery = max(0.0, state.mastery - 0.2)
    state.next_review = date.today() + timedelta(days=state.interval_days)
    session.commit()
    return state


def _record_legacy(session: Session, word: Vocabulary, correct: bool) -> Vocabulary:
    if correct:
        word.correct_count += 1
        index = INTERVALS.index(word.interval_days) + 1 if word.interval_days in INTERVALS else 1
        word.interval_days = INTERVALS[min(index, len(INTERVALS) - 1)]
        session.flush()
        word.mastery = min(1.0, word.mastery + 0.15)
    else:
        word.error_count += 1
        word.interval_days = INTERVALS[0]
        word.mastery = max(0.0, word.mastery - 0.2)
    word.next_review = date.today() + timedelta(days=word.interval_days)
    session.commit()
    return word


def search_words(session: Session, query: str, owner_id: int | None = None) -> list[Vocabulary]:
    escaped = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    needle = f"%{escaped}%"
    stmt = select(Vocabulary).where(
        (Vocabulary.english.ilike(needle, escape="\\"))
        | (Vocabulary.translation.ilike(needle, escape="\\"))
        | (Vocabulary.collocation.ilike(needle, escape="\\"))
        | (Vocabulary.collocation_translation.ilike(needle, escape="\\"))
    )
    if owner_id is not None:
        stmt = stmt.where((Vocabulary.owner_id == owner_id) | Vocabulary.owner_id.is_(None))
    return list(session.scalars(stmt.limit(30)))


def vocabulary_count(session: Session, owner_id: int | None = None) -> int:
    stmt = select(func.count(Vocabulary.id))
    if owner_id is not None:
        stmt = stmt.where((Vocabulary.owner_id == owner_id) | Vocabulary.owner_id.is_(None))
    return int(session.scalar(stmt) or 0)
