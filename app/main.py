import hmac
import logging
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
from app.config import get_settings
from app.database.models import CourseDay, DailyDelivery, UserSettings, Vocabulary
from app.database.session import SessionLocal, init_db
from app.security.authentication import OwnerOnlyMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("ielts_tutor")


async def health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def daily_delivery(request: web.Request) -> web.Response:
    settings = get_settings()
    provided = request.headers.get("X-Daily-Job-Secret", "")
    expected = settings.daily_job_secret.get_secret_value() if settings.daily_job_secret else ""
    if len(expected) < 32 or not hmac.compare_digest(provided, expected):
        raise web.HTTPForbidden(text="Forbidden")

    bot: Bot = request.app["bot"]
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
        lines.append("\nОткройте /menu, чтобы начать занятие.")
        try:
            await bot.send_message(owner_id, "\n".join(lines))
        except TelegramAPIError:
            logger.exception("Daily Telegram delivery failed for owner")
            session.rollback()
            return web.json_response({"status": "delivery_failed"}, status=502)
        delivery.status = "sent"
        delivery.delivered_at = datetime.now(UTC)
        session.commit()
    return web.json_response({"status": "sent", "day": course_day, "words": len(vocabulary)})


async def startup(app: web.Application) -> None:
    settings = get_settings()
    init_db()
    bot: Bot = app["bot"]
    secret = (
        settings.webhook_secret_token.get_secret_value() if settings.webhook_secret_token else ""
    )
    if not settings.webhook_base_url or not settings.webhook_base_url.startswith("https://"):
        raise RuntimeError("WEBHOOK_BASE_URL must be an HTTPS Railway domain")
    if len(secret) < 32:
        raise RuntimeError(
            "WEBHOOK_SECRET_TOKEN must be a generated secret of at least 32 characters"
        )
    if not settings.daily_job_secret or len(settings.daily_job_secret.get_secret_value()) < 32:
        raise RuntimeError("DAILY_JOB_SECRET must be a generated secret of at least 32 characters")
    await bot.set_webhook(
        f"{settings.webhook_base_url.rstrip('/')}/telegram",
        secret_token=secret,
        allowed_updates=app["dispatcher"].resolve_used_update_types(),
        drop_pending_updates=False,
    )
    logger.info("Telegram webhook configured")


async def cleanup(app: web.Application) -> None:
    await app["bot"].session.close()


def create_app() -> web.Application:
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.owner_telegram_id:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN and OWNER_TELEGRAM_ID in Railway Variables")
    bot = Bot(
        token=settings.telegram_bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.message.outer_middleware(OwnerOnlyMiddleware())
    dispatcher.callback_query.outer_middleware(OwnerOnlyMiddleware())
    dispatcher.include_router(router)
    app = web.Application(client_max_size=64 * 1024)
    app["bot"] = bot
    app["dispatcher"] = dispatcher
    SimpleRequestHandler(
        dispatcher=dispatcher,
        bot=bot,
        secret_token=settings.webhook_secret_token.get_secret_value()
        if settings.webhook_secret_token
        else None,
    ).register(app, path="/telegram")
    app.router.add_get("/health", health)
    app.router.add_post("/internal/daily", daily_delivery)
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
