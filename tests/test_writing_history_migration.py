import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_writing_text_migration_preserves_legacy_row_and_downgrade_only_drops_column(
    monkeypatch,
):
    migration_path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "a6c42e91d3f0_writing_submission_text.py"
    )
    spec = importlib.util.spec_from_file_location("writing_text_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE writing_attempts (id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, "
                "task_type VARCHAR(30) NOT NULL, estimated_band FLOAT NOT NULL, "
                "feedback_json TEXT NOT NULL, created_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO writing_attempts VALUES "
                "(1, 44, 'task2', 5.5, :feedback, '2026-10-19 10:00:00')"
            ),
            {"feedback": '{"legacy":true}'},
        )
        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(migration, "op", operations)
        migration.upgrade()

        row = connection.execute(
            text("SELECT id, feedback_json, submission_text FROM writing_attempts WHERE id=1")
        ).one()
        assert row == (1, '{"legacy":true}', None)
        column_names = {
            column["name"] for column in inspect(connection).get_columns("writing_attempts")
        }
        assert "submission_text" in column_names

        migration.downgrade()
        columns_after_downgrade = {
            column["name"] for column in inspect(connection).get_columns("writing_attempts")
        }
        assert "submission_text" not in columns_after_downgrade
        assert "feedback_json" in columns_after_downgrade
        assert connection.execute(
            text("SELECT feedback_json FROM writing_attempts WHERE id=1")
        ).scalar_one() == '{"legacy":true}'
    engine.dispose()
