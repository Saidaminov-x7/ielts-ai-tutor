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
        if (
            settings.owner_telegram_id is None
            or user is None
            or user.id != settings.owner_telegram_id
        ):
            message = data.get("event_message") or getattr(event, "message", None)
            callback = data.get("event_callback_query") or getattr(event, "callback_query", None)
            if callback:
                await callback.answer("Доступ закрыт.", show_alert=True)
            elif message:
                await message.answer("Этот бот доступен только владельцу.")
            return None
        return await handler(event, data)
