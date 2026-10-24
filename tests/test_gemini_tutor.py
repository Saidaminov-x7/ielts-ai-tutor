from __future__ import annotations

import asyncio
import sys
import types as pytypes
from dataclasses import dataclass
from typing import Any

import pytest

from app.ai.gemini_tutor import GeminiTutorError, GeminiTutorResult, ask_course_tutor


@dataclass
class FakeResponse:
    text: str | None = "Tutor response with one example and practice."
    usage_metadata: Any = None
    usage_metadata: Any = None


class FakeModels:
    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.response = response or FakeResponse(
            usage_metadata=pytypes.SimpleNamespace(prompt_token_count=31, candidates_token_count=48)
        )
        self.error = error
        self.call: dict[str, Any] | None = None

    async def generate_content(self, **kwargs: Any) -> Any:
        self.call = kwargs
        if self.error:
            raise self.error
        return self.response


class FakeAio:
    def __init__(self, models: FakeModels) -> None:
        self.models = models
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


class FakeClient:
    def __init__(self, models: FakeModels) -> None:
        self.aio = FakeAio(models)


def install_fake_sdk(monkeypatch: pytest.MonkeyPatch, models: FakeModels) -> FakeClient:
    client = FakeClient(models)
    genai_module = pytypes.ModuleType("google.genai")
    genai_module.Client = lambda *, api_key: client  # type: ignore[attr-defined]
    types_module = pytypes.ModuleType("google.genai.types")
    types_module.GenerateContentConfig = lambda **kwargs: kwargs  # type: ignore[attr-defined]
    genai_module.types = types_module  # type: ignore[attr-defined]
    google_module = pytypes.ModuleType("google")
    google_module.genai = genai_module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", types_module)
    return client


@pytest.mark.asyncio
async def test_success_uses_bounded_config_and_returns_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    models = FakeModels()
    client = install_fake_sdk(monkeypatch, models)
    result = await ask_course_tutor(
        api_key="private-test-key",
        model="caller-selected-stable-model",
        topic="Healthy routines",
        source_excerpt="build a habit; maintain a routine",
        course_words=["routine", "consistent"],
        question="Как использовать routine?",
    )

    assert result == GeminiTutorResult(
        text="Tutor response with one example and practice.",
        prompt_tokens=31,
        output_tokens=48,
    )
    assert models.call is not None
    assert models.call["model"] == "caller-selected-stable-model"
    assert "Как использовать routine?" in models.call["contents"]
    assert "Healthy routines" in models.call["contents"]
    assert models.call["config"]["candidate_count"] == 1
    assert models.call["config"]["max_output_tokens"] == 700
    assert "недоверенными данными" in models.call["config"]["system_instruction"]
    assert client.aio.closed


@pytest.mark.asyncio
async def test_empty_response_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_sdk(monkeypatch, FakeModels(response=FakeResponse(text="  ")))
    with pytest.raises(GeminiTutorError, match="не вернул ответ"):
        await ask_course_tutor(
            api_key="secret",
            model="model",
            topic="Topic",
            source_excerpt="Course text",
            question="Why?",
        )


@pytest.mark.asyncio
async def test_timeout_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    models = FakeModels()
    real_timeout = asyncio.timeout
    monkeypatch.setattr(asyncio, "timeout", lambda _: real_timeout(0.001))

    async def timeout(**kwargs: Any) -> Any:
        await asyncio.sleep(1)

    models.generate_content = timeout  # type: ignore[method-assign]
    install_fake_sdk(monkeypatch, models)
    with pytest.raises(GeminiTutorError, match="не ответил вовремя"):
        await ask_course_tutor(
            api_key="secret",
            model="model",
            topic="Topic",
            source_excerpt="Course text",
            question="Why?",
        )


@pytest.mark.asyncio
async def test_provider_error_does_not_leak_provider_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_sdk(monkeypatch, FakeModels(error=RuntimeError("secret-key-and-provider-details")))
    with pytest.raises(GeminiTutorError) as caught:
        await ask_course_tutor(
            api_key="secret-key",
            model="model",
            topic="Topic",
            source_excerpt="Course text",
            question="Why?",
        )
    assert "secret-key" not in str(caught.value)
    assert "provider-details" not in str(caught.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("topic", "x" * 301),
        ("source_excerpt", "x" * 2501),
        ("question", "x" * 1001),
    ],
)
async def test_input_character_limits_are_enforced(
    monkeypatch: pytest.MonkeyPatch, field: str, value: str
) -> None:
    models = FakeModels()
    install_fake_sdk(monkeypatch, models)
    args = {
        "api_key": "secret",
        "model": "model",
        "topic": "Topic",
        "source_excerpt": "Course text",
        "question": "Why?",
    }
    args[field] = value
    with pytest.raises(GeminiTutorError):
        await ask_course_tutor(**args)  # type: ignore[arg-type]
    assert models.call is None


@pytest.mark.asyncio
async def test_course_words_limit_is_enforced_before_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    models = FakeModels()
    install_fake_sdk(monkeypatch, models)
    with pytest.raises(GeminiTutorError):
        await ask_course_tutor(
            api_key="secret",
            model="model",
            topic="Topic",
            source_excerpt="Course text",
            question="Why?",
            course_words=[str(index) for index in range(11)],
        )
    assert models.call is None
