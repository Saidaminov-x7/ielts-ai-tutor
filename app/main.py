import hmac
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web
from sqlalchemy import select

from app.bot.handlers import router
from app.bot.keyboards import MAIN_MENU
from app.config import get_settings
from app.database.models import CourseDay, DailyDelivery, UserSettings, Vocabulary
from app.database.session import SessionLocal, init_db
from app.scheduler.n8n_events import EVENT_TYPES, event_message, finish_event, reserve_event
from app.security.authentication import OwnerOnlyMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("ielts_tutor")


@dataclass
class RuntimeState:
    bot: Bot | None
    dispatcher: Dispatcher | None


STATE_KEY = web.AppKey("runtime_state", RuntimeState)


async def health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def daily_delivery(request: web.Request) -> web.Response:
    settings = get_settings()
    provided = request.headers.get("X-Daily-Job-Secret", "")
    expected = settings.daily_job_secret.get_secret_value() if settings.daily_job_secret else ""
    if len(expected) < 32 or not hmac.compare_digest(provided, expected):
        raise web.HTTPForbidden(text="Forbidden")

    bot = request.app[STATE_KEY].bot
    if bot is None:
        return web.json_response({"status": "bot_not_configured"}, status=503)
    owner_id = settings.owner_telegram_id
    if owner_id is None:
        raise web.HTTPServiceUnavailable(text="Owner is not configured")
    local_today = datetime.now(ZoneInfo(settings.timezone)).date()
    with SessionLocal() as session:
        prior = session.scalar(
            select(DailyDelivery).where(
                DailyDelivery.owner_id == owner_id,
                DailyDelivery.day == local_today,
            )
        )
        if prior and prior.status == "sent":
            return web.json_response({"status": "already_sent"})
        delivery = prior or DailyDelivery(owner_id=owner_id, day=local_today, status="pending")
        session.add(delivery)
        session.commit()
        user_settings = session.get(UserSettings, owner_id)
        course_day = user_settings.current_day if user_settings else 1
        lesson = session.scalar(select(CourseDay).where(CourseDay.day_number == course_day))
        vocabulary = list(
            session.scalars(
                select(Vocabulary)
                .where(Vocabulary.course_day == course_day)
                .order_by(Vocabulary.english)
                .limit(10)
            )
        )
        if not vocabulary:
            vocabulary = list(
                session.scalars(
                    select(Vocabulary)
                    .where(Vocabulary.next_review <= local_today)
                    .order_by(Vocabulary.next_review, Vocabulary.mastery)
                    .limit(10)
                )
            )
        day_label = f"День {course_day}/182 · неделя {(course_day - 1) // 7 + 1}/26"
        title = escape(lesson.topic) if lesson else "материалы программы ещё не импортированы"
        lines = ["📚 <b>План на сегодня</b>", day_label, f"Тема: {title}"]
        if lesson and lesson.grammar:
            lines.append(f"Грамматика: {escape(lesson.grammar[:700])}")
        if vocabulary:
            lines.append("\n🧠 <b>Слова дня</b>")
            lines.extend(
                f"• <b>{escape(word.english)}</b> — {escape(word.translation)}"
                for word in vocabulary
            )
        else:
            lines.append("\nСлова появятся после импорта вашей программы курса.")
        lines.append("\nОткройте меню кнопок внизу чата, чтобы начать занятие.")
        try:
            await bot.send_message(owner_id, "\n".join(lines), reply_markup=MAIN_MENU)
        except TelegramAPIError:
            logger.exception("Daily Telegram delivery failed for owner")
            session.rollback()
            return web.json_response({"status": "delivery_failed"}, status=502)
        delivery.status = "sent"
        delivery.delivered_at = datetime.now(UTC)
        session.commit()
    return web.json_response({"status": "sent", "day": course_day, "words": len(vocabulary)})


async def scheduled_event(request: web.Request) -> web.Response:
    settings = get_settings()
    provided = request.headers.get("X-Daily-Job-Secret", "")
    expected = settings.daily_job_secret.get_secret_value() if settings.daily_job_secret else ""
    if len(expected) < 32 or not hmac.compare_digest(provided, expected):
        raise web.HTTPForbidden(text="Forbidden")
    bot = request.app[STATE_KEY].bot
    owner_id = settings.owner_telegram_id
    if bot is None or owner_id is None:
        raise web.HTTPServiceUnavailable(text="Bot is not configured")
    try:
        payload = await request.json()
        event_type = payload["event_type"]
        event_day = datetime.strptime(payload["event_date"], "%Y-%m-%d").date()
    except (KeyError, TypeError, ValueError):
        raise web.HTTPBadRequest(text="Invalid event payload") from None
    if not isinstance(event_type, str) or event_type not in EVENT_TYPES:
        raise web.HTTPBadRequest(text="Unsupported event type")

    with SessionLocal() as session:
        event, claimed = reserve_event(session, event_type, event_day)
        if not claimed:
            return web.json_response({"status": "already_processed"})
        try:
            message, status = event_message(session, event_type, owner_id, settings)
            if status == "skipped":
                finish_event(session, event, "skipped")
                return web.json_response({"status": "skipped"})
            if message is None:
                finish_event(session, event, "skipped")
                return web.json_response({"status": "skipped"})
            await bot.send_message(owner_id, message, reply_markup=MAIN_MENU)
            finish_event(session, event, "sent")
        except TelegramAPIError:
            logger.exception("Scheduled Telegram event failed")
            finish_event(session, event, "failed")
            return web.json_response({"status": "delivery_failed"}, status=502)
        except Exception:
            logger.exception("Scheduled event processing failed")
            finish_event(session, event, "failed")
            return web.json_response({"status": "event_failed"}, status=500)
    return web.json_response({"status": "sent", "event_type": event_type})


async def startup(app: web.Application) -> None:
    init_db()
    settings = get_settings()
    state = app[STATE_KEY]
    bot = state.bot
    dispatcher = state.dispatcher
    if bot is None or dispatcher is None:
        logger.warning("Telegram delivery is disabled until owner credentials are configured")
        return
    secret = (
        settings.webhook_secret_token.get_secret_value() if settings.webhook_secret_token else ""
    )
    if not settings.webhook_base_url or not settings.webhook_base_url.startswith("https://"):
        raise RuntimeError("WEBHOOK_BASE_URL must be an HTTPS Railway domain")
    if len(secret) < 32:
        raise RuntimeError(
            "WEBHOOK_SECRET_TOKEN must be a generated secret of at least 32 characters"
        )
    await bot.set_my_commands([])
    if not settings.daily_job_secret or len(settings.daily_job_secret.get_secret_value()) < 32:
        raise RuntimeError("DAILY_JOB_SECRET must be a generated secret of at least 32 characters")
    await bot.set_webhook(
        f"{settings.webhook_base_url.rstrip('/')}/telegram",
        secret_token=secret,
        allowed_updates=dispatcher.resolve_used_update_types(),
        drop_pending_updates=False,
    )
    logger.info("Telegram webhook configured")


async def cleanup(app: web.Application) -> None:
    bot = app[STATE_KEY].bot
    if bot is not None:
        await bot.session.close()


def create_app() -> web.Application:
    settings = get_settings()
    bot: Bot | None = None
    dispatcher: Dispatcher | None = None
    if settings.telegram_bot_token:
        bot = Bot(
            token=settings.telegram_bot_token.get_secret_value(),
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dispatcher = Dispatcher()
        dispatcher.message.outer_middleware(OwnerOnlyMiddleware())
        dispatcher.callback_query.outer_middleware(OwnerOnlyMiddleware())
        dispatcher.include_router(router)
    else:
        logger.warning("Telegram delivery is disabled until TELEGRAM_BOT_TOKEN is configured")
    app = web.Application(client_max_size=64 * 1024)
    app[STATE_KEY] = RuntimeState(bot=bot, dispatcher=dispatcher)
    if bot is not None and dispatcher is not None and settings.webhook_secret_token:
        SimpleRequestHandler(
            dispatcher=dispatcher,
            bot=bot,
            secret_token=settings.webhook_secret_token.get_secret_value(),
        ).register(app, path="/telegram")
    app.router.add_get("/health", health)
    app.router.add_post("/internal/daily", daily_delivery)
    app.router.add_post("/internal/scheduled-event", scheduled_event)
    app.on_startup.append(startup)
    app.on_cleanup.append(cleanup)
    return app


def main() -> None:
    settings = get_settings()
    try:
        web.run_app(create_app(), host="0.0.0.0", port=settings.port, print=None)
    except (TelegramAPIError, OSError):
        logger.exception("Webhook service stopped")
        raise


if __name__ == "__main__":
    main()
