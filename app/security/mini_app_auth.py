"""Authentication helpers for Telegram Mini App API requests.

The client must send the raw ``Telegram.WebApp.initData`` query string. Never
derive identity from ``initDataUnsafe`` or from client-supplied user IDs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass
from typing import Final
from urllib.parse import parse_qsl

from aiohttp import web
from aiohttp.helpers import RequestKey
from aiohttp.typedefs import Middleware

MAX_INIT_DATA_LENGTH: Final = 16_384
_HASH_PATTERN: Final = re.compile(r"^[0-9a-fA-F]{64}$")
_POSITIVE_INTEGER_PATTERN: Final = re.compile(r"^[0-9]+$")


@dataclass(frozen=True, slots=True)
class MiniAppIdentity:
    """The Telegram account authenticated by signed Mini App init data."""

    telegram_user_id: int
    auth_date: int


class MiniAppAuthError(ValueError):
    """Raised when Mini App init data is invalid or not authorized."""


class MiniAppForbiddenError(MiniAppAuthError):
    """Raised when valid Telegram data belongs to a different Telegram user."""


IDENTITY_KEY: Final[RequestKey[MiniAppIdentity]] = RequestKey(
    "mini_app_identity", MiniAppIdentity
)


def validate_init_data(
    init_data: str,
    bot_token: str,
    owner_telegram_id: int,
    *,
    now: int | None = None,
    max_age_seconds: int = 86_400,
    future_tolerance_seconds: int = 30,
) -> MiniAppIdentity:
    """Validate Telegram's HMAC and freshness, then enforce the configured owner.

    ``now`` is injectable for deterministic callers. Telegram's documented
    data-check string contains all decoded fields except ``hash``, sorted by
    key and joined with LF. Duplicate query fields are rejected to avoid
    ambiguous representations.
    """
    if not isinstance(init_data, str) or not init_data or len(init_data) > MAX_INIT_DATA_LENGTH:
        raise MiniAppAuthError("Invalid Mini App authentication data")
    if not isinstance(bot_token, str) or not bot_token:
        raise MiniAppAuthError("Mini App authentication is not configured")
    if not isinstance(owner_telegram_id, int) or isinstance(owner_telegram_id, bool):
        raise MiniAppAuthError("Mini App authentication is not configured")
    if max_age_seconds <= 0 or future_tolerance_seconds < 0:
        raise ValueError("Invalid Mini App authentication time limits")

    try:
        pairs = parse_qsl(
            init_data,
            keep_blank_values=True,
            strict_parsing=True,
            encoding="utf-8",
            errors="strict",
            max_num_fields=100,
            separator="&",
        )
    except (UnicodeDecodeError, ValueError):
        raise MiniAppAuthError("Invalid Mini App authentication data") from None

    fields: dict[str, str] = {}
    for key, value in pairs:
        if not key or key in fields:
            raise MiniAppAuthError("Invalid Mini App authentication data")
        fields[key] = value

    received_hash = fields.pop("hash", None)
    if received_hash is None or not _HASH_PATTERN.fullmatch(received_hash):
        raise MiniAppAuthError("Invalid Mini App authentication data")

    data_check_string = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    # Derive the secret as HMAC(key=WebAppData, message=bot token), then sign
    # the data-check string using that derived secret as the HMAC key.
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    expected_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash.lower()):
        raise MiniAppAuthError("Invalid Mini App authentication data")

    auth_date_value = fields.get("auth_date", "")
    if not _POSITIVE_INTEGER_PATTERN.fullmatch(auth_date_value):
        raise MiniAppAuthError("Invalid Mini App authentication data")
    auth_date = int(auth_date_value)
    current_time = int(time.time()) if now is None else now
    age = current_time - auth_date
    if age > max_age_seconds or age < -future_tolerance_seconds:
        raise MiniAppAuthError("Expired Mini App authentication data")

    try:
        user = json.loads(fields.get("user", ""))
    except (json.JSONDecodeError, TypeError):
        raise MiniAppAuthError("Invalid Mini App authentication data") from None
    if not isinstance(user, dict):
        raise MiniAppAuthError("Invalid Mini App authentication data")
    user_id = user.get("id")
    if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id <= 0:
        raise MiniAppAuthError("Invalid Mini App authentication data")
    if user_id != owner_telegram_id:
        raise MiniAppForbiddenError("Mini App user is not authorized")

    return MiniAppIdentity(telegram_user_id=user_id, auth_date=auth_date)


def get_mini_app_identity(request: web.Request) -> MiniAppIdentity:
    """Return the authenticated identity attached by ``mini_app_auth_middleware``."""
    try:
        return request[IDENTITY_KEY]
    except KeyError:
        raise RuntimeError("Mini App authentication middleware has not run") from None


def mini_app_auth_middleware(
    bot_token: str,
    owner_telegram_id: int,
    *,
    api_prefix: str = "/api/",
    max_age_seconds: int = 86_400,
    future_tolerance_seconds: int = 30,
) -> Middleware:
    """Create middleware that authenticates requests under ``api_prefix``.

    Supply the bot token from secret configuration, never from a request. The
    middleware reads ``X-Telegram-Init-Data`` (or ``Authorization: tma <init_data>``),
    attaches a :class:`MiniAppIdentity`, and returns generic errors without
    logging or disclosing credentials or submitted init data.
    """

    @web.middleware
    async def authenticate(request: web.Request, handler):
        if not request.path.startswith(api_prefix):
            return await handler(request)

        init_data = request.headers.get("X-Telegram-Init-Data", "")
        authorization = request.headers.get("Authorization", "")
        if not init_data and authorization.startswith("tma "):
            init_data = authorization[4:]
        try:
            identity = validate_init_data(
                init_data,
                bot_token,
                owner_telegram_id,
                max_age_seconds=max_age_seconds,
                future_tolerance_seconds=future_tolerance_seconds,
            )
        except MiniAppForbiddenError:
            raise web.HTTPForbidden(
                text="Forbidden", headers={"Cache-Control": "no-store"}
            ) from None
        except MiniAppAuthError:
            raise web.HTTPUnauthorized(
                text="Unauthorized", headers={"Cache-Control": "no-store"}
            ) from None

        request[IDENTITY_KEY] = identity
        return await handler(request)

    return authenticate
