from pathlib import Path

import pytest
from openpyxl import Workbook

from app.learning.course_sources import (
    CourseSourceError,
    parse_vocabulary_pages,
    parse_weekly_roadmap,
)


def _make_workbook(path: Path, weeks: range = range(1, 31)) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "30 недель"
    sheet.append(
        [
            "Неделя",
            "Месяц",
            "Лексическая тема",
            "Грамматика",
            "Listening",
            "Reading / Writing",
            "Speaking / результат",
        ]
    )
    for week in weeks:
        sheet.append(
            [
                week,
                (week - 1) // 4 + 1,
                f"Topic {week}",
                "Grammar source",
                "Listening source",
                "Reading/writing source",
                "Speaking outcome",
            ]
        )
    workbook.save(path)


def _card(sequence: int, word: str | None = None) -> str:
    word = word or f"word{sequence}"
    return "\n".join(
        [
            f"{sequence:03d}",
            f"{word}  /wɜːd/  [ВЁРД]",
            "слово",
            f"{word} example - пример слова",
            "/wɜːd ɪɡˈzɑːmpl/ [ВЁРД ИГ-ЗАМПЛ]",
        ]
    )


def test_weekly_roadmap_requires_all_thirty_sequential_weeks(tmp_path: Path) -> None:
    path = tmp_path / "roadmap.xlsx"
    _make_workbook(path)

    weeks = parse_weekly_roadmap(path)

    assert len(weeks) == 30
    assert weeks[0].week == 1 and weeks[0].month == 1
    assert weeks[0].topic == "Topic 1"
    assert weeks[-1].week == 30 and weeks[-1].topic == "Topic 30"


def test_weekly_roadmap_rejects_missing_week(tmp_path: Path) -> None:
    path = tmp_path / "roadmap.xlsx"
    _make_workbook(path, weeks=range(1, 30))

    with pytest.raises(CourseSourceError, match="exactly one row"):
        parse_weekly_roadmap(path)


def test_vocabulary_pages_preserve_card_fields_and_assign_week() -> None:
    pages = ["\n".join([_card(1, "apple"), _card(2, "learn")]), "\n".join([_card(3), _card(4)])]

    cards = parse_vocabulary_pages(pages, expected_total=4, cards_per_week=2)

    assert [card.sequence for card in cards] == [1, 2, 3, 4]
    assert [card.week for card in cards] == [1, 1, 2, 2]
    assert cards[0].english == "apple"
    assert cards[0].translation == "слово"
    assert cards[0].ipa == "wɜːd"
    assert cards[0].pronunciation_hint == "ВЁРД"
    assert cards[0].collocation == "apple example"
    assert cards[0].collocation_translation == "пример слова"
    assert cards[0].collocation_ipa == "wɜːd ɪɡˈzɑːmpl"
    assert cards[0].source_page == 1


def test_vocabulary_pages_reject_missing_duplicate_and_malformed_cards() -> None:
    with pytest.raises(CourseSourceError, match="missing="):
        parse_vocabulary_pages([_card(1)], expected_total=2, cards_per_week=1)

    with pytest.raises(CourseSourceError, match="Duplicate vocabulary card"):
        parse_vocabulary_pages(
            ["\n".join([_card(1), _card(1)])], expected_total=1, cards_per_week=1
        )

    with pytest.raises(CourseSourceError, match="Malformed English headword"):
        parse_vocabulary_pages(
            [
                "\n".join(
                    [
                        "001",
                        "word without pronunciation",
                        "значение",
                        "some phrase - фраза",
                        "/ipa/ [подсказка]",
                    ]
                )
            ],
            expected_total=1,
            cards_per_week=1,
        )


_SOURCE_DIR = Path("C:/Users/vosil/Desktop")
_ROADMAP_PATH = _SOURCE_DIR / "IELTS_roadmap_30_weeks.xlsx"
_VOCABULARY_PATH = _SOURCE_DIR / "IELTS_vocabulary_30_weeks.pdf"


@pytest.mark.skipif(
    not _ROADMAP_PATH.is_file(),
    reason="User-provided source workbook is not present on this machine",
)
def test_supplied_roadmap_has_exactly_thirty_source_rows() -> None:
    weeks = parse_weekly_roadmap(_ROADMAP_PATH)
    assert len(weeks) == 30
    assert weeks[0].week == 1 and weeks[-1].week == 30
    assert all(week.topic and week.grammar and week.listening for week in weeks)


@pytest.mark.skipif(
    not _VOCABULARY_PATH.is_file(),
    reason="User-provided vocabulary PDF is not present on this machine",
)
def test_supplied_vocabulary_pdf_has_nine_hundred_complete_weekly_cards() -> None:
    pytest.importorskip("pypdf")
    from app.learning.course_sources import parse_vocabulary_pdf

    cards = parse_vocabulary_pdf(_VOCABULARY_PATH)

    assert len(cards) == 900
    assert len({card.english.casefold() for card in cards}) == 900
    assert len({card.collocation.casefold() for card in cards}) == 900
    assert all(card.translation and card.ipa and card.collocation_translation for card in cards)
    assert [sum(card.week == week for card in cards) for week in range(1, 31)] == [30] * 30
    assert (cards[0].sequence, cards[0].week, cards[0].source_page) == (1, 1, 5)
    assert (cards[-1].sequence, cards[-1].week, cards[-1].source_page) == (900, 30, 94)
