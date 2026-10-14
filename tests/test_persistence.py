import os
import subprocess
import sys


def test_database_survives_process_restart(tmp_path):
    database_path = tmp_path / "persistent.sqlite"
    database_url = f"sqlite:///{database_path.as_posix()}"
    create = (
        "from app.database.session import Base, make_engine; "
        "from app.database.models import UserSettings; "
        "from sqlalchemy.orm import Session; "
        f"engine=make_engine('{database_url}'); Base.metadata.create_all(engine); "
        "session=Session(engine); session.add(UserSettings(owner_id=123456, current_day=42)); "
        "session.commit(); session.close(); engine.dispose()"
    )
    verify = (
        "from app.database.session import make_engine; "
        "from app.database.models import UserSettings; "
        "from sqlalchemy.orm import Session; "
        f"engine=make_engine('{database_url}'); session=Session(engine); "
        "record=session.get(UserSettings,123456); "
        "assert record is not None and record.current_day == 42; "
        "print('persistent state restored'); session.close(); engine.dispose()"
    )
    environment = dict(os.environ)
    for script in (create, verify):
        result = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            timeout=20,
        )
        assert result.returncode == 0, result.stderr
    assert "persistent state restored" in result.stdout


def test_alembic_creates_and_reuses_schema(tmp_path):
    database_path = tmp_path / "migrated.sqlite"
    environment = dict(os.environ)
    environment["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
    root = os.path.dirname(os.path.dirname(__file__))
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            timeout=20,
        )
        assert result.returncode == 0, result.stderr
    verify = (
        "import sqlite3, sys; c=sqlite3.connect(sys.argv[1]); "
        "tables={r[0] for r in c.execute(\"select name from sqlite_master where type='table'\")}; "
        "assert 'course_days' in tables and 'writing_attempts' in tables; "
        "assert c.execute('select count(*) from alembic_version').fetchone()[0] == 1; "
        "print('schema migrated and reused')"
    )
    result = subprocess.run(
        [sys.executable, "-c", verify, str(database_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert "schema migrated and reused" in result.stdout
