import hmac
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.types import MenuButtonWebApp, WebAppInfo
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError

from app.api.mini_app import json_errors, register_routes
from app.bot.handlers import router
from app.bot.keyboards import MAIN_MENU
from app.config import get_settings
from app.database.models import CourseDay, CourseWeek, DailyDelivery, UserSettings, Vocabulary
from app.database.session import SessionLocal, init_db
from app.learning.course_sources import new_cards_for_day
from app.scheduler.n8n_events import EVENT_TYPES, event_message, finish_event, reserve_event
from app.security.authentication import OwnerOnlyMiddleware
from app.security.mini_app_auth import mini_app_auth_middleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("ielts_tutor")


@dataclass
class RuntimeState:
    bot: Bot | None
    dispatcher: Dispatcher | None


STATE_KEY = web.AppKey("runtime_state", RuntimeState)
FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


@web.middleware
async def security_headers(request: web.Request, handler) -> web.StreamResponse:
    response = await handler(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self' https://telegram.org; "
        "connect-src 'self'; img-src 'self' data: blob:; "
        "style-src 'self' 'unsafe-inline'; font-src 'self' data:; "
        "object-src 'none'; base-uri 'self'; "
        "frame-ancestors 'self' https://web.telegram.org https://*.telegram.org",
    )
    if request.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


async def mini_app_index(request: web.Request) -> web.StreamResponse:
    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        raise web.HTTPServiceUnavailable(text="Mini App assets are not built")
    return web.FileResponse(index)


async def mini_app_fallback(request: web.Request) -> web.StreamResponse:
    if request.path.startswith(("/api/", "/assets/")) or Path(request.path).suffix:
        raise web.HTTPNotFound()
    return await mini_app_index(request)


async def health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def _claim_daily_delivery(
    session, owner_id: int, day: date, now: datetime
) -> tuple[bool, int]:
    """Claim this day's Telegram delivery once, recovering abandoned sends after five minutes."""
    lease_expired_before = now - timedelta(minutes=5)
    delivery = session.scalar(
        select(DailyDelivery).where(
            DailyDelivery.owner_id == owner_id,
            DailyDelivery.day == day,
        )
    )
    if delivery is None:
        delivery = DailyDelivery(
            owner_id=owner_id,
            day=day,
            status="sending",
            claimed_at=now,
        )
        session.add(delivery)
        try:
            session.commit()
            return True, delivery.id
        except IntegrityError:
            session.rollback()
            delivery = session.scalar(
                select(DailyDelivery).where(
                    DailyDelivery.owner_id == owner_id,
                    DailyDelivery.day == day,
                )
            )
            if delivery is None:
                raise

    claim = session.execute(
        update(DailyDelivery)
        .where(
            DailyDelivery.id == delivery.id,
            DailyDelivery.status != "sent",
            or_(
                DailyDelivery.status != "sending",
                DailyDelivery.claimed_at.is_(None),
                DailyDelivery.claimed_at <= lease_expired_before,
            ),
        )
        .values(status="sending", claimed_at=now)
    )
    acquired = claim.rowcount == 1  # type: ignore[attr-defined]
    session.commit()
    return acquired, delivery.id


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
        claimed, delivery_id = _claim_daily_delivery(
            session, owner_id, local_today, datetime.now(UTC).replace(tzinfo=None)
        )
        if not claimed:
            prior = session.get(DailyDelivery, delivery_id)
            status = "already_sent" if prior and prior.status == "sent" else "in_progress"
            return web.json_response({"status": status})
        delivery = session.get(DailyDelivery, delivery_id)
        if delivery is None:
            raise web.HTTPInternalServerError(text="Daily delivery claim was lost")
        user_settings = session.get(UserSettings, owner_id)
        original_cursor = user_settings.course_schedule_day if user_settings else None
        original_course_started_at = user_settings.course_started_at if user_settings else None
        scheduled_day = (
            user_settings.course_schedule_day or user_settings.current_day
            if user_settings
            else 1
        )
        if scheduled_day > 210:
            delivery.status = "sent"
            delivery.claimed_at = None
            delivery.delivered_at = datetime.now(UTC)
            session.commit()
            return web.json_response({"status": "course_complete"})
        course_day = max(1, scheduled_day)
        week_number = min(30, max(1, (course_day - 1) // 7 + 1))
        lesson = session.scalar(select(CourseDay).where(CourseDay.day_number == course_day))
        week = session.scalar(select(CourseWeek).where(CourseWeek.week_number == week_number))
        topic = lesson.topic if lesson else week.topic if week else None
        grammar = lesson.grammar if lesson else week.grammar if week else ""
        sequences = () if course_day % 7 == 0 else new_cards_for_day(course_day)
        vocabulary = list(
            session.scalars(
                select(Vocabulary)
                .where(
                    Vocabulary.course_week == week_number,
                    Vocabulary.source_key.in_([f"pdf:{number:03d}" for number in sequences]),
                    (Vocabulary.owner_id == owner_id) | Vocabulary.owner_id.is_(None),
                )
                .order_by(Vocabulary.source_key)
            )
        )
        if not vocabulary:
            vocabulary = list(
                session.scalars(
                    select(Vocabulary)
                    .where(
                        Vocabulary.next_review <= local_today,
                        (Vocabulary.owner_id == owner_id) | Vocabulary.owner_id.is_(None),
                    )
                    .order_by(Vocabulary.next_review, Vocabulary.mastery)
                    .limit(10)
                )
            )
        day_label = f"День {course_day}/210 · неделя {week_number}/30"
        title = escape(topic) if topic else "материалы программы ещё не импортированы"
        day_in_week = (course_day - 1) % 7 + 1
        sourced_focus = (
            [week.grammar, week.listening, week.reading_writing, week.speaking_outcome]
            if week
            else []
        )
        focus = (
            sourced_focus[day_in_week - 1]
            if day_in_week <= 4 and sourced_focus
            else "повторение слов недели"
            if day_in_week == 7
            else "лексика недели"
        )
        focus = escape(focus) if focus else "материалы дня ещё не импортированы"
        lines = [
            "📚 <b>План на сегодня</b>",
            day_label,
            f"Тема недели: {title}",
            f"Фокус дня: {focus}",
        ]
        if grammar and not (week and day_in_week == 1):
            lines.append(f"Грамматика: {escape(grammar[:700])}")
        if vocabulary:
            lines.append("\n🧠 <b>Слова дня</b>")
            lines.extend(
                f"• <b>{escape(word.english)}</b> — {escape(word.translation)}"
                for word in vocabulary
            )
        else:
            lines.append("\nСлова появятся после импорта вашей программы курса.")
        lines.append("\nОткройте приложение кнопкой внизу чата, чтобы начать занятие.")
        try:
            await bot.send_message(owner_id, "\n".join(lines), reply_markup=MAIN_MENU)
        except TelegramAPIError:
            logger.exception("Daily Telegram delivery failed for owner")
            session.rollback()
            failed_delivery = session.get(DailyDelivery, delivery_id)
            if failed_delivery is not None:
                failed_delivery.status = "failed"
                failed_delivery.claimed_at = None
                session.commit()
            return web.json_response({"status": "delivery_failed"}, status=502)
        delivery.status = "sent"
        delivery.claimed_at = None
        delivery.delivered_at = datetime.now(UTC)
        if user_settings is not None and week is not None:
            cursor_filter = (
                UserSettings.course_schedule_day.is_(None)
                if original_cursor is None
                else UserSettings.course_schedule_day == original_cursor
            )
            started_at_filter = (
                UserSettings.course_started_at.is_(None)
                if original_course_started_at is None
                else UserSettings.course_started_at == original_course_started_at
            )
            session.execute(
                update(UserSettings)
                .where(
                    UserSettings.owner_id == owner_id,
                    cursor_filter,
                    started_at_filter,
                )
                .values(course_schedule_day=min(211, course_day + 1))
            )
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
    from app.learning.course_sources import import_course_dataset

    dataset_path = Path(__file__).resolve().parents[1] / "data" / "ielts_vocabulary_30_weeks.json"
    if dataset_path.is_file():
        with SessionLocal() as course_session:
            import_course_dataset(course_session, dataset_path)
        logger.info("Loaded private IELTS course source: 30 weeks and 900 vocabulary cards")
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
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Открыть приложение",
                web_app=WebAppInfo(url=settings.webhook_base_url.rstrip("/")),
            )
        )
    except TelegramAPIError:
        logger.exception("Could not configure Telegram Mini App menu button")
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
    bot_token = (
        settings.telegram_bot_token.get_secret_value() if settings.telegram_bot_token else ""
    )
    owner_id = settings.owner_telegram_id if settings.owner_telegram_id is not None else -1
    app = web.Application(
        client_max_size=64 * 1024,
        middlewares=[
            security_headers,
            json_errors,
            mini_app_auth_middleware(bot_token, owner_id, max_age_seconds=86_400),
        ],
    )
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
    register_routes(app)
    app.router.add_get("/", mini_app_index)
    if FRONTEND_DIST.is_dir():
        assets = FRONTEND_DIST / "assets"
        if assets.is_dir():
            app.router.add_static("/assets", assets, show_index=False, append_version=False)
        app.router.add_get("/{path:.*}", mini_app_fallback)
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
