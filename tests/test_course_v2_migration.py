import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_course_v2_migration_preserves_legacy_vocabulary_and_review_sessions(monkeypatch):
    path = Path(__file__).parents[1] / "migrations" / "versions" / "b7d0a1c2e4f6_course_v2.py"
    spec = importlib.util.spec_from_file_location("course_v2_migration", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE vocabulary (id INTEGER PRIMARY KEY, "
                "english VARCHAR(200), translation VARCHAR(300), owner_id INTEGER, "
                "next_review DATE, interval_days INTEGER DEFAULT 1, "
                "correct_count INTEGER DEFAULT 0, "
                "error_count INTEGER DEFAULT 0, mastery FLOAT DEFAULT 0)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE ai_usage (id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, "
                "month VARCHAR(7), request_date DATE, reserved_usd FLOAT, actual_usd FLOAT, "
                "input_tokens INTEGER, output_tokens INTEGER)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE review_sessions (id INTEGER PRIMARY KEY, "
                "owner_id INTEGER, word_ids_json TEXT)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO vocabulary "
                "(id, english, translation, owner_id, next_review, interval_days, "
                "correct_count, error_count, mastery) "
                "VALUES (17, 'legacy', 'old', NULL, '2026-10-24', 1, 0, 0, 0)"
            )
        )
        connection.execute(text("INSERT INTO review_sessions VALUES (23, 88, '[17]')"))
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.upgrade()
        assert connection.execute(
            text("SELECT id, english, translation FROM vocabulary")
        ).one() == (17, "legacy", "old")
        assert connection.execute(text("SELECT id, word_ids_json FROM review_sessions")).one() == (
            23,
            "[17]",
        )
        assert {col["name"] for col in inspect(connection).get_columns("vocabulary")} >= {
            "source_key",
            "course_week",
            "collocation",
            "collocation_translation",
        }
    engine.dispose()


