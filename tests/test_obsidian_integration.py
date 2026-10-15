import base64
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot import handlers
from app.config import Settings
from app.database.models import CourseDay, ObsidianSave, TaskProgress, Vocabulary
from app.integrations.obsidian import (
    GitHubVault,
    ObsidianAPIError,
    ObsidianNotConfigured,
    note_path,
    render_note,
    safe_root,
)


def test_paths_and_yaml_are_safe():
    path = note_path("../private//vault", "../../Words", "../a/b:*?", 8)
    assert path.startswith("private/vault/Words/")
    assert ".." not in path.split("/")
    assert "/a/" not in path
    assert note_path("safe", "../../Words", "x", 8).startswith("safe/Words/")
    with pytest.raises(ValueError):
        note_path("safe", "Notes", "x", -1)
    assert safe_root("../../") == "IELTS Tutor"
    markdown = render_note('x: "quoted"\n---', "Notes", 3, "body\n---")
    assert 'title: "x: \\"quoted\\"\\n---"' in markdown
    assert "telegram_user_id: 3" in markdown


@pytest.mark.asyncio
async def test_successful_markdown_write_creates_file(monkeypatch):
    calls = []

    class Response:
        def __init__(self, status, payload=None):
            self.status, self.payload, self.content_length = status, payload or {}, 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def json(self):
            return self.payload

    class Client:
        def __init__(self, **_):
            pass

        def request(self, method, url, **kwargs):
            calls.append((method, url, kwargs))
            return Response(404) if method == "GET" else Response(201)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

    monkeypatch.setattr("app.integrations.obsidian.aiohttp.ClientSession", Client)
    settings = Settings(github_token="secret-test-token", github_repo="owner/vault")
    vault = GitHubVault(settings)
    path = note_path("IELTS Tutor", "Notes", "hello", 9)
    content = render_note("hello", "Notes", 9, "example")
    await vault.write(path, content)
    assert [call[0] for call in calls] == ["GET", "PUT"]
    put = calls[-1][2]["json"]
    assert base64.b64decode(put["content"]).decode() == content
    assert put["branch"] == "main"
    # The token is required in the outbound Authorization header, but never in
    # response text, logs, Telegram output, or persisted note content.
    assert "secret-test-token" not in content


@pytest.mark.asyncio
async def test_github_api_error_is_reported_without_response_body(monkeypatch):
    class Response:
        status = 403
        content_length = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

    class Client:
        def __init__(self, **_):
            pass

        def request(self, *_args, **_kwargs):
            return Response()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

    monkeypatch.setattr("app.integrations.obsidian.aiohttp.ClientSession", Client)
    vault = GitHubVault(Settings(github_token="do-not-log", github_repo="owner/vault"))
    with pytest.raises(ObsidianAPIError):
        await vault.check()


@pytest.mark.asyncio
async def test_missing_configuration_is_explicit():
    with pytest.raises(ObsidianNotConfigured):
        await GitHubVault(Settings()).check()


@pytest.mark.asyncio
async def test_save_is_bound_to_user_and_duplicate_update_is_skipped(session, monkeypatch):
    session.add(ObsidianSave(owner_id=44, update_id=123, path="IELTS Tutor/Notes/x-123.md"))
    session.commit()

    @contextmanager
    def use_test_session():
        yield session

    monkeypatch.setattr(handlers, "SessionLocal", use_test_session)
    write = AsyncMock()
    monkeypatch.setattr(handlers, "_github_vault", lambda: SimpleNamespace(write=write))
    monkeypatch.setattr(
        handlers, "get_settings", lambda: Settings(github_notes_path="IELTS Tutor")
    )
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=44),
        message_id=123,
        answer=AsyncMock(),
    )
    await handlers._save_obsidian(message, "x", "Notes", "body")
    write.assert_not_awaited()
    assert "уже сохранена" in message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_successful_save_is_reserved_and_written_once(session, monkeypatch):
    @contextmanager
    def use_test_session():
        yield session

    monkeypatch.setattr(handlers, "SessionLocal", use_test_session)
    write = AsyncMock()
    monkeypatch.setattr(handlers, "_github_vault", lambda: SimpleNamespace(write=write))
    monkeypatch.setattr(
        handlers, "get_settings", lambda: Settings(github_notes_path="IELTS Tutor")
    )
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=45),
        message_id=124,
        answer=AsyncMock(),
    )
    await handlers._save_obsidian(message, "x", "Notes", "body")
    await handlers._save_obsidian(message, "x", "Notes", "body")
    write.assert_awaited_once()
    assert session.query(ObsidianSave).filter_by(owner_id=45, update_id=124).count() == 1


@pytest.mark.asyncio
async def test_failed_github_write_releases_idempotency_reservation(session, monkeypatch):
    @contextmanager
    def use_test_session():
        yield session

    monkeypatch.setattr(handlers, "SessionLocal", use_test_session)

    async def fail(*_args):
        raise ObsidianAPIError

    monkeypatch.setattr(handlers, "_github_vault", lambda: SimpleNamespace(write=fail))
    monkeypatch.setattr(
        handlers, "get_settings", lambda: Settings(github_notes_path="IELTS Tutor")
    )
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=46),
        message_id=125,
        answer=AsyncMock(),
    )
    await handlers._save_obsidian(message, "x", "Notes", "body")
    assert session.query(ObsidianSave).filter_by(owner_id=46, update_id=125).count() == 0
    assert "GitHub" in message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_save_word_only_selects_the_calling_users_personal_word(session, monkeypatch):
    session.add_all(
        [
            Vocabulary(owner_id=45, english="owned", translation="мой", example="mine"),
            Vocabulary(owner_id=99, english="private", translation="чужое"),
            Vocabulary(owner_id=None, english="shared", translation="общее"),
        ]
    )
    session.commit()

    @contextmanager
    def use_test_session():
        yield session

    monkeypatch.setattr(handlers, "SessionLocal", use_test_session)
    save = AsyncMock()
    monkeypatch.setattr(handlers, "_save_obsidian", save)
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=45), text="/save_word", answer=AsyncMock()
    )
    await handlers.save_word_handler(message)
    assert save.await_args.args[1:3] == ("owned — мой", "Vocabulary")
    assert "mine" in save.await_args.args[3]


@pytest.mark.asyncio
async def test_save_lesson_uses_owner_scoped_current_day(session, monkeypatch):
    session.add_all(
        [
            CourseDay(
                day_number=2,
                week_number=1,
                topic="Writing practice",
                grammar="Conditionals",
                reading="Article",
                listening="Podcast",
                writing="Essay",
                objectives="",
            ),
            TaskProgress(
                owner_id=45,
                day_number=2,
                task_key="writing",
                completed=True,
                completed_at=None,
            ),
        ]
    )
    session.commit()
    from app.database.models import UserSettings

    session.add(UserSettings(owner_id=45, current_day=2))
    session.commit()

    @contextmanager
    def use_test_session():
        yield session

    monkeypatch.setattr(handlers, "SessionLocal", use_test_session)
    save = AsyncMock()
    monkeypatch.setattr(handlers, "_save_obsidian", save)
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=45), text="/save_lesson", answer=AsyncMock()
    )
    await handlers.save_lesson_handler(message)
    assert save.await_args.args[1:3] == ("Lesson day 2 — Writing practice", "Lessons")
    assert "Conditionals" in save.await_args.args[3]
    assert "[x] Writing" in save.await_args.args[3]


@pytest.mark.asyncio
async def test_owner_middleware_remains_authoritative(monkeypatch):
    from app.security.authentication import OwnerOnlyMiddleware

    monkeypatch.setattr(
        "app.security.authentication.get_settings",
        lambda: Settings(owner_telegram_id=7),
    )
    entered = False

    async def handler(*_args, **_kwargs):
        nonlocal entered
        entered = True

    middleware = OwnerOnlyMiddleware()
    await middleware(handler, object(), {"event_from_user": SimpleNamespace(id=8)})
    assert not entered
