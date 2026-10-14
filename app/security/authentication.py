from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.config import get_settings


class OwnerOnlyMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        settings = get_settings()
        user = data.get("event_from_user")
        message = data.get("event_message") or getattr(event, "message", None)
        if message is None and hasattr(event, "text"):
            message = event
        message_command = (
            getattr(message, "text", "").strip().split(maxsplit=1)[0].split("@", 1)[0]
            if message is not None and getattr(message, "text", "").strip()
            else ""
        )
        if (
            settings.owner_telegram_id is None
            and message is not None
            and message_command == "/whoami"
            and getattr(getattr(message, "chat", None), "type", None) == "private"
            and user is not None
        ):
            return await handler(event, data)
        if (
            settings.owner_telegram_id is None
            or user is None
            or user.id != settings.owner_telegram_id
        ):
            callback = data.get("event_callback_query") or getattr(event, "callback_query", None)
            if callback:
                await callback.answer("Доступ закрыт.", show_alert=True)
            elif message:
                await message.answer("Этот бот доступен только владельцу.")
            return None
        return await handler(event, data)
