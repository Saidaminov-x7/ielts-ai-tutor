"""Strict readers for the user-supplied IELTS roadmap and vocabulary PDF.

The readers intentionally preserve source content as supplied. They do not
generate missing lessons or repair malformed source rows silently.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from openpyxl import load_workbook  # type: ignore[import-untyped]

WEEK_COUNT = 30
VOCABULARY_CARD_COUNT = 900
CARDS_PER_WEEK = 30


class CourseSourceError(ValueError):
    """Raised when a source workbook or PDF does not match its expected layout."""


@dataclass(frozen=True, slots=True)
class CourseWeekSource:
    week: int
    month: int
    topic: str
    grammar: str
    listening: str
    reading_writing: str
    speaking_outcome: str


@dataclass(frozen=True, slots=True)
class VocabularySource:
    sequence: int
    english: str
    translation: str
    ipa: str
    pronunciation_hint: str
    collocation: str
    collocation_translation: str
    collocation_ipa: str
    collocation_pronunciation_hint: str
    week: int
    source_page: int


def new_cards_for_day(day_number: int, *, cards_per_study_day: int = 5) -> tuple[int, ...]:
    """Return zero-based PDF sequence IDs for the plan's Mon-Sat five-card routine.

    Day 7 of each course week is review-only. On days 1-6, the schedule cycles
    through that week's 30 cards without inventing additional vocabulary.
    """
    if not isinstance(day_number, int) or day_number < 1:
        raise ValueError("day_number must be a positive integer")
    if not isinstance(cards_per_study_day, int) or cards_per_study_day < 1:
        raise ValueError("cards_per_study_day must be a positive integer")
    day_of_week = (day_number - 1) % 7 + 1
    if day_of_week == 7:
        return ()
    week = (day_number - 1) // 7
    first = week * 30 + (day_of_week - 1) * cards_per_study_day + 1
    last = min(week * 30 + 30, first + cards_per_study_day - 1)
    return tuple(range(first, last + 1))


_WEEK_HEADER_ALIASES = {
    "week": {"\u043d\u0435\u0434\u0435\u043b\u044f", "week"},
    "month": {"\u043c\u0435\u0441\u044f\u0446", "month"},
    "topic": {
        "\u043b\u0435\u043a\u0441\u0438\u0447\u0435\u0441\u043a\u0430\u044f "
        "\u0442\u0435\u043c\u0430",
        "\u0442\u0435\u043c\u0430",
        "topic",
        "lexical topic",
    },
    "grammar": {"\u0433\u0440\u0430\u043c\u043c\u0430\u0442\u0438\u043a\u0430", "grammar"},
    "listening": {
        "listening",
        "\u0430\u0443\u0434\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435",
    },
    "reading_writing": {
        "reading / writing",
        "reading/writing",
        "reading / writing ",
        "\u0447\u0442\u0435\u043d\u0438\u0435 / \u043f\u0438\u0441\u044c\u043c\u043e",
    },
    "speaking_outcome": {
        "speaking / \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442",
        "speaking/\u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442",
        "speaking / outcome",
        "speaking / result",
    },
}
_CARD_NUMBER = re.compile(r"^\d{3}$")
_WORD_LINE = re.compile(r"^(?P<word>.+?)\s+/([^/\r\n]+)/(?:\s+\[(?P<hint>.*)\])?$")
_COLLOCATION_LINE = re.compile(r"^(?P<english>.+?)\s+-\s+(?P<translation>.+)$")


def _clean_cell(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _header_key(value: object) -> str:
    return re.sub(r"\s+", " ", _clean_cell(value).casefold())


def parse_weekly_roadmap(path: Path | str) -> tuple[CourseWeekSource, ...]:
    """Read and validate the 30-row weekly roadmap workbook sheet."""

    source = Path(path)
    if not source.is_file():
        raise CourseSourceError(f"Roadmap workbook does not exist: {source}")

    try:
        workbook = load_workbook(source, read_only=True, data_only=True)
    except Exception as exc:
        raise CourseSourceError(f"Could not open roadmap workbook ({type(exc).__name__}).") from exc

    try:
        sheet = next(
            (
                item
                for item in workbook.worksheets
                if _header_key(item.title) == "30 \u043d\u0435\u0434\u0435\u043b\u044c"
            ),
            None,
        )
        if sheet is None:
            raise CourseSourceError("Workbook is missing the '30 РЅРµРґРµР»СЊ' sheet.")

        header_row: tuple[object, ...] | None = None
        header_row_number = 0
        for row_number, row in enumerate(sheet.iter_rows(values_only=True), start=1):
            keys = {_header_key(value) for value in row if _clean_cell(value)}
            if all(keys & aliases for aliases in _WEEK_HEADER_ALIASES.values()):
                header_row = row
                header_row_number = row_number
                break
        if header_row is None:
            raise CourseSourceError("Could not find all required roadmap column headers.")

        header_positions: dict[str, int] = {}
        for field, aliases in _WEEK_HEADER_ALIASES.items():
            match = next(
                (index for index, value in enumerate(header_row) if _header_key(value) in aliases),
                None,
            )
            if match is None:
                raise CourseSourceError(f"Roadmap is missing the '{field}' column.")
            header_positions[field] = match

        weeks: list[CourseWeekSource] = []
        for row_number, row in enumerate(
            sheet.iter_rows(min_row=header_row_number + 1, values_only=True),
            start=header_row_number + 1,
        ):
            values = {
                field: _clean_cell(row[index] if index < len(row) else None)
                for field, index in header_positions.items()
            }
            if not any(values.values()):
                continue
            raw_week = values["week"]
            try:
                week_value = float(raw_week)
                month_value = float(values["month"])
            except (TypeError, ValueError):
                # Skip non-course rows such as notes beneath the weekly table.
                if not raw_week:
                    continue
                raise CourseSourceError(
                    f"Roadmap row {row_number} has a non-numeric week or month."
                ) from None
            if not week_value.is_integer() or not month_value.is_integer():
                raise CourseSourceError(f"Roadmap row {row_number} has a fractional week/month.")
            week = int(week_value)
            month = int(month_value)
            if week < 1 or week > WEEK_COUNT:
                raise CourseSourceError(
                    f"Roadmap row {row_number} has week {week}; expected 1вЂ“{WEEK_COUNT}."
                )
            if month < 1 or month > WEEK_COUNT:
                raise CourseSourceError(f"Roadmap row {row_number} has an invalid month {month}.")
            required = ("topic", "grammar", "listening", "reading_writing", "speaking_outcome")
            missing = [field for field in required if not values[field]]
            if missing:
                raise CourseSourceError(
                    f"Roadmap row {row_number} (week {week}) is missing: {', '.join(missing)}."
                )
            weeks.append(
                CourseWeekSource(
                    week=week,
                    month=month,
                    topic=values["topic"],
                    grammar=values["grammar"],
                    listening=values["listening"],
                    reading_writing=values["reading_writing"],
                    speaking_outcome=values["speaking_outcome"],
                )
            )

        numbers = [week.week for week in weeks]
        expected = list(range(1, WEEK_COUNT + 1))
        if numbers != expected:
            raise CourseSourceError(
                "Roadmap weeks must contain exactly one row for each week 1вЂ“30 "
                f"in order; found {numbers!r}."
            )
        return tuple(weeks)
    finally:
        workbook.close()


def _pronunciation(raw: str, *, context: str) -> tuple[str, str]:
    value = raw.strip()
    match = re.fullmatch(r"/(?P<ipa>[^/]+)/(?:\s+\[(?P<hint>.*)\])?", value)
    if not match:
        raise CourseSourceError(f"Malformed pronunciation at {context}: {value!r}.")
    return match.group("ipa").strip(), (match.group("hint") or "").strip()


def parse_vocabulary_pages(
    pages: Iterable[str],
    *,
    expected_total: int = VOCABULARY_CARD_COUNT,
    cards_per_week: int = CARDS_PER_WEEK,
) -> tuple[VocabularySource, ...]:
    """Parse extracted PDF page text and reject missing or malformed cards."""

    if expected_total < 1 or cards_per_week < 1 or expected_total % cards_per_week:
        raise ValueError("expected_total must be a positive multiple of cards_per_week.")

    cards: list[VocabularySource] = []
    seen: set[int] = set()
    lines_with_pages = [
        (line.strip(), page_number)
        for page_number, page_text in enumerate(pages, start=1)
        for line in page_text.splitlines()
        if line.strip()
    ]

    cursor = 0
    while cursor < len(lines_with_pages):
        line, page = lines_with_pages[cursor]
        if not _CARD_NUMBER.fullmatch(line):
            cursor += 1
            continue

        sequence = int(line)
        if sequence in seen:
            raise CourseSourceError(f"Duplicate vocabulary card {sequence:03d} on PDF page {page}.")
        seen.add(sequence)
        context = f"card {sequence:03d}, PDF page {page}"
        required = lines_with_pages[cursor + 1 : cursor + 5]
        if len(required) != 4:
            raise CourseSourceError(f"Incomplete vocabulary card at {context}.")
        word_line, _word_page = required[0]
        translation, _translation_page = required[1]
        collocation_line, _collocation_page = required[2]
        pronunciation_line, _pronunciation_page = required[3]

        word_match = _WORD_LINE.fullmatch(word_line)
        if not word_match:
            raise CourseSourceError(f"Malformed English headword at {context}: {word_line!r}.")
        english = word_match.group("word").strip()
        ipa = re.search(r"/([^/]+)/", word_line)
        if ipa is None:
            raise CourseSourceError(f"Missing IPA transcription at {context}.")
        pronunciation_hint_match = re.search(r"\[(.*)\]\s*$", word_line)
        pronunciation_hint = (
            pronunciation_hint_match.group(1).strip() if pronunciation_hint_match else ""
        )
        if not translation:
            raise CourseSourceError(f"Missing Russian meaning at {context}.")

        collocation_match = _COLLOCATION_LINE.fullmatch(collocation_line)
        if not collocation_match:
            raise CourseSourceError(f"Malformed collocation at {context}: {collocation_line!r}.")
        collocation_ipa, collocation_hint = _pronunciation(
            pronunciation_line, context=f"{context} collocation"
        )
        if (
            not collocation_match.group("english").strip()
            or not collocation_match.group("translation").strip()
        ):
            raise CourseSourceError(f"Incomplete collocation at {context}.")

        week = (sequence - 1) // cards_per_week + 1
        cards.append(
            VocabularySource(
                sequence=sequence,
                english=english,
                translation=translation,
                ipa=ipa.group(1).strip(),
                pronunciation_hint=pronunciation_hint,
                collocation=collocation_match.group("english").strip(),
                collocation_translation=collocation_match.group("translation").strip(),
                collocation_ipa=collocation_ipa,
                collocation_pronunciation_hint=collocation_hint,
                week=week,
                source_page=page,
            )
        )
        cursor += 5

    expected_numbers = list(range(1, expected_total + 1))
    actual_numbers = sorted(seen)
    if actual_numbers != expected_numbers:
        missing = sorted(set(expected_numbers) - seen)
        unexpected = sorted(seen - set(expected_numbers))
        raise CourseSourceError(
            f"Vocabulary PDF card IDs are incomplete: expected {expected_total} sequential cards; "
            f"missing={missing[:10]!r}, unexpected={unexpected[:10]!r}."
        )

    cards.sort(key=lambda card: card.sequence)
    distribution: dict[int, int] = {}
    for card in cards:
        distribution[card.week] = distribution.get(card.week, 0) + 1
    expected_distribution = {
        week: cards_per_week for week in range(1, expected_total // cards_per_week + 1)
    }
    if distribution != expected_distribution:
        raise CourseSourceError(f"Vocabulary cards do not divide evenly by week: {distribution!r}.")
    return tuple(cards)


def _validated_sources(
    roadmap_path: Path | str, vocabulary_path: Path | str
) -> tuple[tuple[CourseWeekSource, ...], tuple[VocabularySource, ...]]:
    weeks = parse_weekly_roadmap(roadmap_path)
    cards = parse_vocabulary_pdf(vocabulary_path)
    duplicate_pairs = [
        pair
        for pair, count in Counter(
            (card.english.casefold(), card.translation.casefold()) for card in cards
        ).items()
        if count > 1
    ]
    if duplicate_pairs:
        raise CourseSourceError(
            "Vocabulary contains duplicate source meanings; resolve before import: "
            f"{duplicate_pairs[:5]!r}."
        )
    return weeks, cards


def parse_vocabulary_pdf(
    path: Path | str,
    *,
    expected_total: int = VOCABULARY_CARD_COUNT,
    cards_per_week: int = CARDS_PER_WEEK,
) -> tuple[VocabularySource, ...]:
    """Extract and validate vocabulary cards from the supplied PDF."""

    source = Path(path)
    if not source.is_file():
        raise CourseSourceError(f"Vocabulary PDF does not exist: {source}")
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise CourseSourceError(
            "PDF parsing requires the 'pypdf' package to be installed."
        ) from exc

    try:
        reader = PdfReader(str(source))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise CourseSourceError(
            f"Could not extract vocabulary PDF ({type(exc).__name__})."
        ) from exc
    return parse_vocabulary_pages(
        pages, expected_total=expected_total, cards_per_week=cards_per_week
    )


def import_course_sources(
    session, roadmap_path: Path | str, vocabulary_path: Path | str
) -> dict[str, int]:
    """Idempotently upsert source course content while preserving learner review rows."""
    from sqlalchemy import select

    from app.database.models import CourseWeek, Vocabulary

    dataset_path = Path(__file__).resolve().parents[2] / "data" / "ielts_vocabulary_30_weeks.json"
    if dataset_path.is_file():
        dataset = load_course_dataset(dataset_path)
        weeks = tuple(CourseWeekSource(**item) for item in dataset["weeks"])
        cards = tuple(VocabularySource(**item) for item in dataset["vocabulary"])
    else:
        weeks, cards = _validated_sources(roadmap_path, vocabulary_path)
    for week_source in weeks:
        row = session.scalar(select(CourseWeek).where(CourseWeek.week_number == week_source.week))
        if row is None:
            row = CourseWeek(week_number=week_source.week)
            session.add(row)
        row.month = week_source.month
        row.topic = week_source.topic
        row.grammar = week_source.grammar
        row.listening = week_source.listening
        row.reading_writing = week_source.reading_writing
        row.speaking_outcome = week_source.speaking_outcome

    for card in cards:
        key = f"pdf:{card.sequence:03d}"
        row = session.scalar(select(Vocabulary).where(Vocabulary.source_key == key))
        if row is None:
            row = session.scalar(
                select(Vocabulary).where(
                    Vocabulary.english == card.english,
                    Vocabulary.translation == card.translation,
                    Vocabulary.owner_id.is_(None),
                    Vocabulary.source_key.is_(None),
                )
            )
        if row is None:
            row = Vocabulary(
                source_key=key,
                english=card.english,
                translation=card.translation,
                owner_id=None,
                topic="",
                transcription=card.ipa,
                next_review=date.today(),
                learned_at=datetime.min.replace(tzinfo=UTC),
            )
            session.add(row)
        else:
            if row.source_key is None:
                row.source_key = key
            row.english = card.english
            row.translation = card.translation
            row.transcription = card.ipa
            row.owner_id = None
            row.next_review = date.today()
            row.interval_days = 1
            row.correct_count = 0
            row.error_count = 0
            row.mastery = 0.0
            row.learned_at = datetime.min.replace(tzinfo=UTC)
        row.course_week = card.week
        row.pronunciation_hint = card.pronunciation_hint
        row.collocation = card.collocation
        row.collocation_translation = card.collocation_translation
        row.collocation_transcription = card.collocation_ipa
        row.collocation_pronunciation_hint = card.collocation_pronunciation_hint
        row.topic = weeks[card.week - 1].topic
    session.flush()
    from app.database.models import VocabularyProgress

    legacy_words = list(session.scalars(select(Vocabulary).where(Vocabulary.source_key.is_(None))))
    for old in legacy_words:
        if (
            old.owner_id is not None
            and session.scalar(
                select(VocabularyProgress.id).where(
                    VocabularyProgress.owner_id == old.owner_id,
                    VocabularyProgress.vocabulary_id == old.id,
                )
            )
            is None
        ):
            session.add(
                VocabularyProgress(
                    owner_id=old.owner_id,
                    vocabulary_id=old.id,
                    next_review=old.next_review,
                    interval_days=old.interval_days,
                    correct_count=old.correct_count,
                    error_count=old.error_count,
                    mastery=old.mastery,
                )
            )
            # Preserve legacy values in place; future course review uses owner state.
    session.commit()
    return {"weeks": len(weeks), "vocabulary": len(cards)}


def build_course_dataset(roadmap_path: Path | str, vocabulary_path: Path | str) -> dict:
    """Return validated, serializable course source data without database writes."""
    weeks, cards = _validated_sources(roadmap_path, vocabulary_path)
    return {
        "notice": (
            "Private course source for the user-requested IELTS tutor. "
            "Pronunciation data includes CMUdict-derived content; see CMUDICT_LICENSE.txt."
        ),
        "weeks": [
            {
                "week": week.week,
                "month": week.month,
                "topic": week.topic,
                "grammar": week.grammar,
                "listening": week.listening,
                "reading_writing": week.reading_writing,
                "speaking_outcome": week.speaking_outcome,
            }
            for week in weeks
        ],
        "vocabulary": [
            {
                "sequence": card.sequence,
                "week": card.week,
                "english": card.english,
                "translation": card.translation,
                "ipa": card.ipa,
                "pronunciation_hint": card.pronunciation_hint,
                "collocation": card.collocation,
                "collocation_translation": card.collocation_translation,
                "collocation_ipa": card.collocation_ipa,
                "collocation_pronunciation_hint": card.collocation_pronunciation_hint,
                "source_page": card.source_page,
            }
            for card in cards
        ],
    }


def load_course_dataset(path: Path | str | None = None) -> dict:
    """Load and structurally validate generated course content without DB changes."""
    dataset_path = (
        Path(path)
        if path is not None
        else Path(__file__).resolve().parents[2]
        / "data"
        / "ielts_vocabulary_30_weeks.json"
    )
    if not dataset_path.is_file():
        raise CourseSourceError(f"Generated course dataset does not exist: {dataset_path}")
    try:
        dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
        weeks = tuple(CourseWeekSource(**item) for item in dataset["weeks"])
        cards = tuple(VocabularySource(**item) for item in dataset["vocabulary"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise CourseSourceError("Generated course dataset is invalid.") from exc
    if len(weeks) != 30 or [item.week for item in weeks] != list(range(1, 31)):
        raise CourseSourceError("Generated dataset must contain roadmap weeks 1 through 30.")
    if len(cards) != 900 or [item.sequence for item in cards] != list(range(1, 901)):
        raise CourseSourceError("Generated dataset must contain vocabulary cards 001 through 900.")
    if any(card.week != (card.sequence - 1) // 30 + 1 for card in cards):
        raise CourseSourceError("Generated dataset has inconsistent vocabulary week assignments.")
    return dataset


def import_course_dataset(session, path: Path | str | None = None) -> dict[str, int]:
    """Idempotently upsert the generated, validated dataset without source PDFs."""
    from sqlalchemy import select

    from app.database.models import CourseWeek, Vocabulary, VocabularyProgress

    dataset = load_course_dataset(path)
    weeks = tuple(CourseWeekSource(**item) for item in dataset["weeks"])
    cards = tuple(VocabularySource(**item) for item in dataset["vocabulary"])
    by_week: dict[int, CourseWeek] = {}
    for source in weeks:
        row = session.scalar(select(CourseWeek).where(CourseWeek.week_number == source.week))
        if row is None:
            row = CourseWeek(week_number=source.week)
            session.add(row)
        row.month = source.month
        row.topic = source.topic
        row.grammar = source.grammar
        row.listening = source.listening
        row.reading_writing = source.reading_writing
        row.speaking_outcome = source.speaking_outcome
        by_week[source.week] = row
    for card in cards:
        key = f"pdf:{card.sequence:03d}"
        row = session.scalar(select(Vocabulary).where(Vocabulary.source_key == key))
        if row is None:
            row = session.scalar(select(Vocabulary).where(
                Vocabulary.english == card.english,
                Vocabulary.translation == card.translation,
                Vocabulary.owner_id.is_(None),
                Vocabulary.source_key.is_(None),
            ))
        if row is None:
            row = Vocabulary(
                source_key=key, english=card.english, translation=card.translation,
                owner_id=None, topic=by_week[card.week].topic,
                transcription=card.ipa, next_review=date.today(),
                learned_at=datetime.min.replace(tzinfo=UTC),
            )
            session.add(row)
        else:
            row.source_key = key
            row.english = card.english
            row.translation = card.translation
            row.transcription = card.ipa
            row.owner_id = None
            row.topic = by_week[card.week].topic
            row.next_review = date.today()
            row.interval_days = 1
            row.correct_count = 0
            row.error_count = 0
            row.mastery = 0
            row.learned_at = datetime.min.replace(tzinfo=UTC)
        row.course_week = card.week
        row.pronunciation_hint = card.pronunciation_hint
        row.collocation = card.collocation
        row.collocation_translation = card.collocation_translation
        row.collocation_transcription = card.collocation_ipa
        row.collocation_pronunciation_hint = card.collocation_pronunciation_hint
    session.flush()
    for old in session.scalars(select(Vocabulary).where(Vocabulary.source_key.is_(None))):
        if old.owner_id is None:
            continue
        state = session.scalar(select(VocabularyProgress.id).where(
            VocabularyProgress.owner_id == old.owner_id,
            VocabularyProgress.vocabulary_id == old.id,
        ))
        if state is None:
            session.add(VocabularyProgress(
                owner_id=old.owner_id, vocabulary_id=old.id,
                next_review=old.next_review, interval_days=old.interval_days,
                correct_count=old.correct_count, error_count=old.error_count,
                mastery=old.mastery,
            ))
    session.commit()
    return {"weeks": len(weeks), "vocabulary": len(cards)}
