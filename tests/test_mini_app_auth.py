import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from app.security.mini_app_auth import validate_init_data

BOT_TOKEN = "test-bot-token-only"
OWNER_ID = 7654321
NOW = 1_800_000_000


def _signed_init_data(*, auth_date: int, user: str | None = None) -> str:
    fields = {"auth_date": str(auth_date)}
    if user is not None:
        fields["user"] = user

    data_check_string = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    signature = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return urlencode([*fields.items(), ("hash", signature)])


def _user_json(user_id: int) -> str:
    return json.dumps({"id": user_id}, separators=(",", ":"))


def test_validate_init_data_accepts_valid_signed_owner() -> None:
    init_data = _signed_init_data(auth_date=NOW, user=_user_json(OWNER_ID))

    identity = validate_init_data(init_data, BOT_TOKEN, OWNER_ID, now=NOW)

    assert identity.telegram_user_id == OWNER_ID
    assert identity.auth_date == NOW


def test_validate_init_data_rejects_tampered_signature() -> None:
    init_data = _signed_init_data(auth_date=NOW, user=_user_json(OWNER_ID))
    init_data = init_data[:-1] + ("0" if init_data[-1] != "0" else "1")

    with pytest.raises(ValueError):
        validate_init_data(init_data, BOT_TOKEN, OWNER_ID, now=NOW)


@pytest.mark.parametrize("user", [None, "not-json"])
def test_validate_init_data_rejects_missing_or_malformed_user(user: str | None) -> None:
    init_data = _signed_init_data(auth_date=NOW, user=user)

    with pytest.raises(ValueError):
        validate_init_data(init_data, BOT_TOKEN, OWNER_ID, now=NOW)


def test_validate_init_data_rejects_expired_auth_date() -> None:
    init_data = _signed_init_data(auth_date=NOW - 86_401, user=_user_json(OWNER_ID))

    with pytest.raises(ValueError):
        validate_init_data(init_data, BOT_TOKEN, OWNER_ID, now=NOW)


def test_validate_init_data_rejects_future_auth_date() -> None:
    init_data = _signed_init_data(auth_date=NOW + 31, user=_user_json(OWNER_ID))

    with pytest.raises(ValueError):
        validate_init_data(init_data, BOT_TOKEN, OWNER_ID, now=NOW)


def test_validate_init_data_rejects_different_signed_owner() -> None:
    init_data = _signed_init_data(auth_date=NOW, user=_user_json(OWNER_ID + 1))

    with pytest.raises(ValueError):
        validate_init_data(init_data, BOT_TOKEN, OWNER_ID, now=NOW)
