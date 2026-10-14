import json
from datetime import date
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, User
from sqlalchemy import select

from app.ai.writing_examiner import examine
from app.bot.keyboards import BACK, MAIN_MENU
from app.database.models import (
    Activity,
    ErrorLog,
    ExamSession,
    QuizSession,
    ReviewSession,
    UserSettings,
    Vocabulary,
)
from app.database.session import SessionLocal
from app.learning.daily_tests import answer_quiz, start_quiz, submit_quiz
from app.learning.lessons import complete_task, current_day, finish_day, lesson_summary
from app.learning.reports import progress_report
from app.learning.vocabulary import add_word, due_words, record_review, search_words
from app.learning.weekly_exams import record_exam_answer, submit_exam, weekly_exam

router = Router()


def owner_id(user: User | None) -> int:
    if user is None:
        raise ValueError("Telegram update has no user")
    return user.id


class WritingState(StatesGroup):
    awaiting_text = State()


class WordState(StatesGroup):
    awaiting_word = State()


async def answer(message: Message, text: str, **kwargs) -> None:
    await message.answer(text, **kwargs)


@router.message(CommandStart())
async def start(message: Message) -> None:
    await answer(
        message,
        "Привет! Я помогу заниматься по программе IELTS Academic.\n\n"
        "Результаты — учебная оценка, не официальный IELTS Band Score.\n"
        "Тексты для проверки Writing отправляются в OpenAI API, если ключ настроен.",
        reply_markup=MAIN_MENU,
    )


@router.message(Command("whoami"))
async def whoami(message: Message) -> None:
    if message.chat.type != "private" or message.from_user is None:
        await answer(message, "Команда доступна только в личном чате с ботом.")
        return
    await answer(
        message,
        f"Ваш Telegram User ID: <code>{message.from_user.id}</code>\n"
        "До настройки этого ID доступна только эта команда.",
        parse_mode="HTML",
    )


@router.message(Command("menu"))
async def menu(message: Message) -> None:
    await answer(message, "Главное меню:", reply_markup=MAIN_MENU)


@router.callback_query(F.data == "menu")
async def show_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await callback.message.answer("Главное меню:", reply_markup=MAIN_MENU)


@router.callback_query(F.data == "lesson")
async def lesson(callback: CallbackQuery) -> None:
    await callback.answer()
    with SessionLocal() as session:
        data = lesson_summary(session, owner_id(callback.from_user))
        lines = [
            f"📚 Неделя {data['week']}/26 · день {data['day']}/182",
            f"Тема: {escape(str(data['topic']))}",
        ]
        if data["grammar"]:
            lines.append(f"Грамматика: {escape(str(data['grammar'])[:500])}")
        for item in data["tasks"]:
            lines.append(
                f"{'✅' if item['done'] else '⬜'} {item['title']} ({item['minutes']} мин.)"
            )
        lines.append(f"Осталось заданий: {data['remaining']}")
        lines.append("Чтобы отметить выполненный блок: /done grammar (после реального выполнения).")
        if callback.message:
            await callback.message.answer("\n".join(lines), reply_markup=BACK)


@router.message(Command("done"))
async def done(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    key = parts[1].strip().lower() if len(parts) > 1 else ""
    with SessionLocal() as session:
        uid = owner_id(message.from_user)
        day = current_day(session, uid)
        if not complete_task(session, uid, day, key):
            await answer(
                message,
                "Блоки: review, grammar, vocabulary, exercises, reading, listening, writing, quiz.",
            )
            return
        finished = finish_day(session, uid, day)
        await answer(
            message,
            "День завершён. Серия и прогресс обновлены."
            if finished
            else "Блок отмечен. День засчитается после выполнения всех 8 блоков.",
        )


@router.callback_query(F.data == "progress")
async def progress(callback: CallbackQuery) -> None:
    await callback.answer()
    with SessionLocal() as session:
        report = escape(progress_report(session, owner_id(callback.from_user)))
    if callback.message:
        await callback.message.answer(report, reply_markup=BACK)


@router.callback_query(F.data == "words")
async def words(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "Отправьте слово и перевод в формате: <code>apple — яблоко</code>.\n"
            "Для поиска используйте /search слово.",
            parse_mode="HTML",
            reply_markup=BACK,
        )


@router.message(Command("search"))
async def search(message: Message) -> None:
    query = (message.text or "").partition(" ")[2].strip()
    if not query:
        await answer(message, "Использование: /search английское слово или перевод")
        return
    with SessionLocal() as session:
        found = search_words(session, query, owner_id(message.from_user))
    await answer(
        message,
        "\n".join(
            f"{escape(w.english)} — {escape(w.translation)}. {escape(w.example)}" for w in found
        )
        or "Ничего не найдено.",
    )


@router.message(F.text.contains("—"))
async def add_personal_word(message: Message) -> None:
    en, _, ru = (message.text or "").partition("—")
    if not en.strip() or not ru.strip() or len(en) > 200 or len(ru) > 300:
        await answer(message, "Формат: английское слово — перевод")
        return
    with SessionLocal() as session:
        try:
            word = add_word(session, en, ru, owner_id=owner_id(message.from_user))
            await answer(
                message,
                f"Добавлено: {escape(word.english)} — {escape(word.translation)}",
            )
        except Exception:
            session.rollback()
            await answer(message, "Это слово с таким переводом уже есть в словаре.")


@router.callback_query(F.data == "review")
async def review(callback: CallbackQuery) -> None:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    await callback.answer()
    with SessionLocal() as session:
        due = due_words(session, limit=10, owner_id=owner_id(callback.from_user))
        if callback.message:
            if not due:
                await callback.message.answer(
                    "На сегодня повторений нет. Добавьте слова или вернитесь позже.",
                    reply_markup=BACK,
                )
                return
            first = due[0]
            review_session = ReviewSession(
                owner_id=owner_id(callback.from_user),
                word_ids_json=json.dumps([word.id for word in due]),
                cursor=0,
            )
            session.add(review_session)
            session.commit()
            session.refresh(review_session)
            await callback.message.answer(
                f"Переведите: <b>{escape(first.english)}</b>\nОтветьте переводом.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✅ Помню", callback_data=f"review:{review_session.id}:1"
                            ),
                            InlineKeyboardButton(
                                text="🔁 Повторить", callback_data=f"review:{review_session.id}:0"
                            ),
                        ]
                    ]
                ),
            )


@router.callback_query(F.data.startswith("review:"))
async def review_answer_callback(callback: CallbackQuery) -> None:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    _, session_raw, answer_raw = (callback.data or "").split(":")
    with SessionLocal() as session:
        review_session = session.get(ReviewSession, int(session_raw))
        valid = bool(
            review_session
            and review_session.owner_id == owner_id(callback.from_user)
            and not review_session.completed
        )
        if not valid or review_session is None:
            await callback.answer("Сессия повторения завершена.", show_alert=True)
            return
        ids = json.loads(review_session.word_ids_json)
        cursor = review_session.cursor
        if cursor >= len(ids):
            review_session.completed = True
            session.commit()
            await callback.answer("Повторение завершено.")
            return
        word = session.get(Vocabulary, ids[cursor])
        if word is None:
            review_session.cursor += 1
            session.commit()
            await callback.answer("Слово недоступно.")
            return
        correct = answer_raw == "1"
        record_review(session, word, correct)
        review_session.cursor += 1
        session.add(
            Activity(
                owner_id=owner_id(callback.from_user),
                kind="review",
                topic=word.topic or "Vocabulary review",
                score=100 if correct else 0,
            )
        )
        if review_session.cursor >= len(ids):
            review_session.completed = True
            settings = session.get(UserSettings, owner_id(callback.from_user))
            if settings is not None:
                settings.last_active_date = date.today()
                settings.streak = max(settings.streak, 1)
                settings.max_streak = max(settings.max_streak, settings.streak)
                session.add(settings)
            await callback.answer(
                "Повторение завершено." if correct else f"Правильный перевод: {word.translation}"
            )
            if callback.message:
                await callback.message.answer("🔁 Повторение завершено. Отличная работа!")
        else:
            next_word = session.get(Vocabulary, ids[review_session.cursor])
            session.commit()
            await callback.answer(
                "Ответ учтён." if correct else f"Правильный перевод: {word.translation}",
                show_alert=not correct,
            )
            if callback.message and next_word:
                await callback.message.answer(
                    f"Следующее слово: <b>{escape(next_word.english)}</b>",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="✅ Помню",
                                    callback_data=f"review:{review_session.id}:1",
                                ),
                                InlineKeyboardButton(
                                    text="🔁 Повторить",
                                    callback_data=f"review:{review_session.id}:0",
                                ),
                            ]
                        ]
                    ),
                )


@router.message(Command("answer"))
async def review_answer(message: Message) -> None:
    guess = (message.text or "").partition(" ")[2].strip().casefold()
    with SessionLocal() as session:
        word = next(iter(due_words(session, limit=10, owner_id=owner_id(message.from_user))), None)
        if not word:
            await answer(message, "На сегодня повторений нет.")
            return
        correct = guess == word.translation.strip().casefold()
        record_review(session, word, correct)
        await answer(
            message,
            ("Верно!" if correct else f"Пока нет. Правильный ответ: {escape(word.translation)}")
            + f"\nСледующее повторение через {word.interval_days} дн.",
        )


@router.callback_query(F.data == "quiz")
async def quiz(callback: CallbackQuery) -> None:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    with SessionLocal() as session:
        attempt = start_quiz(
            session,
            owner_id(callback.from_user),
            current_day(session, owner_id(callback.from_user)),
        )
        qs = json.loads(attempt.questions_json)
        attempt_id = attempt.id
    if callback.message:
        for idx, q in enumerate(qs):
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=option, callback_data=f"q:{attempt_id}:{idx}:{n}")]
                    for n, option in enumerate(q["options"])
                ]
            )
            await callback.message.answer(f"{idx + 1}. {q['question']}", reply_markup=keyboard)
        await callback.message.answer("После ответов на вопросы результат появится автоматически.")
    await callback.answer()


@router.callback_query(F.data.startswith("q:"))
async def quiz_answer(callback: CallbackQuery) -> None:
    _, session_raw, idx_raw, ans_raw = (callback.data or "").split(":")
    with SessionLocal() as session:
        attempt = session.get(QuizSession, int(session_raw))
        saved = bool(
            attempt
            and attempt.owner_id == owner_id(callback.from_user)
            and answer_quiz(session, attempt, int(idx_raw), int(ans_raw))
        )
        total = len(json.loads(attempt.questions_json)) if attempt else 0
        answers = json.loads(attempt.answers_json) if attempt else {}
        result = (
            submit_quiz(session, attempt)
            if saved and attempt is not None and len(answers) == total
            else None
        )
    if result:
        await callback.answer("Тест завершён.", show_alert=True)
        if callback.message:
            await callback.message.answer(
                f"Результат: {result['score']}/{result['total']} ({result['percent']}%)."
            )
    else:
        await callback.answer(
            "Ответ сохранён." if saved else "Сессия теста недействительна.", show_alert=not saved
        )


@router.callback_query(F.data == "writing")
async def writing_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(WritingState.awaiting_text)
    if callback.message:
        await callback.message.answer(
            "Пришлите текст IELTS Writing Task 1 или 2 (до установленного лимита).\n"
            "Текст будет передан OpenAI API для проверки."
        )


@router.message(WritingState.awaiting_text, F.text)
async def writing_submit(message: Message, state: FSMContext) -> None:
    await state.clear()
    with SessionLocal() as session:
        try:
            result = await examine(session, owner_id(message.from_user), message.text or "")
            criteria = "\n".join(
                f"{escape(key)}: {escape(str(value))}" for key, value in result.criteria.items()
            )
            errors = "\n".join(
                f"• {escape(e.get('wrong', ''))} → {escape(e.get('correction', ''))}: "
                f"{escape(e.get('explanation_ru', ''))}"
                for e in result.errors[:8]
            )
            await answer(
                message,
                f"Ориентировочно: {result.estimated_band}/9 (не официальный балл)\n{criteria}\n"
                f"{escape(result.explanation_ru[:1500])}\nОшибки:\n{errors}\nРекомендации:\n"
                + "\n".join(f"• {escape(r)}" for r in result.recommendations[:5]),
            )
        except Exception as exc:
            await answer(
                message,
                f"Проверка не выполнена ({type(exc).__name__}). Проверьте настройки API и лимиты.",
            )


@router.callback_query(F.data == "errors")
async def errors(callback: CallbackQuery) -> None:
    await callback.answer()
    with SessionLocal() as session:
        rows = list(
            session.scalars(
                select(ErrorLog)
                .where(
                    ErrorLog.owner_id == owner_id(callback.from_user),
                    ErrorLog.resolved.is_(False),
                )
                .order_by(ErrorLog.created_at.desc())
                .limit(10)
            )
        )
    report = "\n\n".join(
        f"{escape(row.topic)}: {escape(row.wrong_answer)} → "
        f"{escape(row.correct_answer)}\n{escape(row.explanation)}"
        for row in rows
    )
    if callback.message:
        await callback.message.answer(report or "Журнал ошибок пока пуст.", reply_markup=BACK)


@router.callback_query(F.data == "exam")
async def exam(callback: CallbackQuery) -> None:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    await callback.answer()
    with SessionLocal() as session:
        uid = owner_id(callback.from_user)
        week = (current_day(session, uid) - 1) // 7 + 1
        result = weekly_exam(session, uid, week)
        exam_id = result.id
        questions = __import__("json").loads(result.questions_json)
    if callback.message:
        await callback.message.answer(
            f"Начат учебный экзамен недели {week}. Время: 30 минут. "
            "Это учебная проверка, не официальный IELTS."
        )
        for idx, question in enumerate(questions):
            buttons = [
                [
                    InlineKeyboardButton(
                        text=option, callback_data=f"exam:{exam_id}:{idx}:{option_idx}"
                    )
                ]
                for option_idx, option in enumerate(question["options"])
            ]
            await callback.message.answer(
                f"{idx + 1}. {question['question']}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            )
        await callback.message.answer("Когда закончите, отправьте /submit_exam.", reply_markup=BACK)


@router.callback_query(F.data.startswith("exam:"))
async def exam_answer(callback: CallbackQuery) -> None:
    _, exam_id_raw, question_raw, answer_raw = (callback.data or "").split(":")
    with SessionLocal() as session:
        exam_session = session.get(ExamSession, int(exam_id_raw))
        saved = bool(
            exam_session
            and exam_session.owner_id == owner_id(callback.from_user)
            and record_exam_answer(session, exam_session, int(question_raw), int(answer_raw))
        )
    await callback.answer(
        "Ответ сохранён." if saved else "Сессия истекла или недействительна.", show_alert=not saved
    )


@router.message(Command("submit_exam"))
async def submit_exam_command(message: Message) -> None:
    with SessionLocal() as session:
        exam_session = session.scalar(
            select(ExamSession)
            .where(
                ExamSession.owner_id == owner_id(message.from_user),
                ExamSession.submitted_at.is_(None),
            )
            .order_by(ExamSession.started_at.desc())
        )
        if not exam_session:
            await answer(message, "Активный экзамен не найден.")
            return
        result = submit_exam(session, exam_session)
    await answer(message, f"Результат: {result['score']}/{result['total']}\n{result['note']}")


@router.callback_query(F.data == "settings")
async def settings_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    with SessionLocal() as session:
        uid = owner_id(callback.from_user)
        settings = session.get(UserSettings, uid) or UserSettings(
            owner_id=uid, current_day=1, streak=0, max_streak=0, completed_days=0
        )
        session.add(settings)
        session.commit()
        reminder_state = "включены" if settings.reminders_enabled else "выключены"
        quiet_state = "да" if settings.quiet_mode else "нет"
        text = (
            f"Напоминания: {reminder_state}\nВремя: {settings.reminder_time} (Asia/Tashkent)\n"
            f"Тихий режим: {quiet_state}"
        )
    if callback.message:
        await callback.message.answer(
            text + "\nКоманды: /reminders on|off · /quiet on|off · /time ЧЧ:ММ", reply_markup=BACK
        )


@router.message(Command("reminders"))
async def reminders(message: Message) -> None:
    value = (message.text or "").partition(" ")[2].strip().lower()
    if value not in {"on", "off"}:
        await answer(message, "Использование: /reminders on|off")
        return
    with SessionLocal() as session:
        uid = owner_id(message.from_user)
        row = session.get(UserSettings, uid) or UserSettings(
            owner_id=uid, current_day=1, streak=0, max_streak=0, completed_days=0
        )
        row.reminders_enabled = value == "on"
        session.add(row)
        session.commit()
    await answer(message, "Напоминания " + ("включены." if value == "on" else "выключены."))


@router.message(Command("quiet"))
async def quiet(message: Message) -> None:
    value = (message.text or "").partition(" ")[2].strip().lower()
    if value not in {"on", "off"}:
        await answer(message, "Использование: /quiet on|off")
        return
    with SessionLocal() as session:
        uid = owner_id(message.from_user)
        row = session.get(UserSettings, uid) or UserSettings(
            owner_id=uid, current_day=1, streak=0, max_streak=0, completed_days=0
        )
        row.quiet_mode = value == "on"
        session.add(row)
        session.commit()
    await answer(message, "Тихий режим " + ("включён." if value == "on" else "выключен."))


@router.message(Command("time"))
async def change_time(message: Message) -> None:
    value = (message.text or "").partition(" ")[2].strip()
    try:
        date.fromisoformat("2020-01-01")
        hour, minute = map(int, value.split(":"))
        assert 0 <= hour <= 23 and 0 <= minute <= 59
    except (ValueError, AssertionError):
        await answer(message, "Формат времени: /time 19:00")
        return
    with SessionLocal() as session:
        uid = owner_id(message.from_user)
        row = session.get(UserSettings, uid) or UserSettings(
            owner_id=uid, current_day=1, streak=0, max_streak=0, completed_days=0
        )
        row.reminder_time = f"{hour:02d}:{minute:02d}"
        session.add(row)
        session.commit()
    await answer(
        message, f"Время напоминаний установлено: {hour:02d}:{minute:02d} (Asia/Tashkent)."
    )
