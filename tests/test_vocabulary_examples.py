import json

import pytest

from app.ai.vocabulary_examples import VocabularyExamplesError, validate_examples


def _items():
    return [
        {
            "english": f"I understand the example number {index}.",
            "translation": f"Я понимаю пример номер {index}.",
        }
        for index in range(10)
    ]


def test_validate_examples_accepts_exactly_ten_translated_unique_sentences():
    result = validate_examples(json.dumps({"items": _items()}))
    assert len(result) == 10
    assert result[0]["translation"].startswith("Я понимаю")


def test_validate_examples_requires_each_sentence_to_use_target_item():
    with pytest.raises(VocabularyExamplesError, match="target vocabulary"):
        validate_examples(_items(), target_word="unrelated")


@pytest.mark.parametrize(
    "value",
    [
        [],
        _items()[:9],
        _items() + [_items()[0]],
        [{"english": "An English sentence.", "translation": ""}] * 10,
        [{"english": "An English sentence.", "translation": "A translation"}] * 10,
        "not json",
    ],
)
def test_validate_examples_rejects_invalid_or_incomplete_output(value):
    with pytest.raises(VocabularyExamplesError):
        validate_examples(value)
