import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_course_reset_archive_downgrade_refuses_data_loss(monkeypatch):
    migration_path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "a7e618f4b302_course_restart_archive.py"
    )
    spec = importlib.util.spec_from_file_location("course_reset_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE user_settings (owner_id INTEGER PRIMARY KEY, current_day INTEGER)")
        )
        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(migration, "op", operations)
        migration.upgrade()
        connection.execute(
            text(
                "INSERT INTO course_reset_archives "
                "(owner_id, reset_at, payload_json, request_key) "
                "VALUES (44, '2026-10-25 12:00:00', '{\"counters\":{}}', 'request-1')"
            )
        )

        with pytest.raises(RuntimeError, match="Export and verify"):
            migration.downgrade()

        assert connection.execute(
            text("SELECT payload_json FROM course_reset_archives WHERE owner_id=44")
        ).scalar_one() == '{"counters":{}}'
        assert "course_schedule_day" in {
            column["name"] for column in inspect(connection).get_columns("user_settings")
        }

        connection.execute(text("DELETE FROM course_reset_archives"))
        migration.downgrade()
        assert "course_reset_archives" not in inspect(connection).get_table_names()
        assert "course_schedule_day" not in {
            column["name"] for column in inspect(connection).get_columns("user_settings")
        }
    engine.dispose()
