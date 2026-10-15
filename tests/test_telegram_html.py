from types import SimpleNamespace

import pytest

from app.bot import handlers
from app.database.models import Vocabulary


@pytest.mark.asyncio
async def test_search_escapes_untrusted_vocabulary_for_telegram_html(session, monkeypatch):
    session.add(
        Vocabulary(
            english="<b>word</b>",
            translation="A & B",
            example="<script>alert(1)</script>",
            owner_id=17,
        )
    )
    session.commit()
    monkeypatch.setattr(handlers, "SessionLocal", lambda: session)
    messages = []

    async def reply(text, **_kwargs):
        messages.append(text)

    message = SimpleNamespace(
        text="word",
        from_user=SimpleNamespace(id=17),
        answer=reply,
    )

    await handlers.search(message)

    assert messages == [
        "&lt;b&gt;word&lt;/b&gt; — A &amp; B. &lt;script&gt;alert(1)&lt;/script&gt;"
    ]
