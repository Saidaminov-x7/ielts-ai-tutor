from openpyxl import Workbook

from app.database.models import CourseDay, Vocabulary
from app.importer import import_workbook


def test_import_is_repeatable_and_does_not_mutate_source(session, tmp_path):
    path = tmp_path / "course.xlsx"
    workbook = Workbook()
    days = workbook.active
    days.title = "Days"
    days.append(["day", "topic", "grammar", "reading"])
    days.append([1, "Introductions", "to be", "Short text"])
    words = workbook.create_sheet("Words")
    words.append(["english", "translation", "example"])
    words.append(["hello", "привет", "Hello!"])
    workbook.save(path)
    original = path.read_bytes()
    first = import_workbook(session, path)
    second = import_workbook(session, path)
    assert first.days_added == 1 and first.words_added == 1
    assert second.days_added == 0 and second.days_updated == 1 and second.words_added == 0
    assert path.read_bytes() == original
    assert session.query(CourseDay).count() == session.query(Vocabulary).count() == 1
