import json
from datetime import date, datetime
from html import escape
from types import SimpleNamespace

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, User
from sqlalchemy import select

from app.ai.writing_examiner import examine
from app.bot.keyboards import (
    BACK,
    EXAM_SUBMIT,
    MAIN_MENU,
    MENU_ACTIONS,
    lesson_tasks_keyboard,
    settings_keyboard,
)
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
from app.learning.adaptive import adapt_day
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
    awaiting_search = State()


async def answer(message: Message, text: str, **kwargs) -> None:
    await message.answer(text, **kwargs)


@router.message(CommandStart())
async def start(message: Message) -> None:
    await answer(
        message,
        "Привет! Я помогу заниматься по программе IELTS Academic. Выбирайте действия "
        "кнопками внизу чата. Обычный текст нужен для ответов, словаря и Writing.\n\n"
        "Результаты — учебная оценка, не официальный IELTS Band Score.\n"
        "GPT используется только по вашему выбору для проверки Writing.",
        reply_markup=MAIN_MENU,
    )


@router.message(F.text.in_(MENU_ACTIONS))
async def keyboard_menu_action(message: Message, state: FSMContext) -> None:
    """Route persistent Telegram keyboard labels to the same handlers as inline buttons."""
    action = MENU_ACTIONS[message.text or ""]
    await state.clear()
    if action == "menu":
        await answer(message, "Выберите действие:", reply_markup=MAIN_MENU)
        return
    callback = _command_as_callback(message, action)
    if action == "lesson":
        await lesson(callback)
    elif action == "words":
        await words(callback)
    elif action == "search":
        await search_start(message, state)
    elif action == "review":
        await review(callback)
    elif action == "quiz":
        await quiz(callback)
    elif action == "writing":
        await writing_start(callback, state)
    elif action == "progress":
        await progress(callback)
    elif action == "errors":
        await errors(callback)
    elif action == "exam":
        await exam(callback)
    elif action == "settings":
        await settings_menu(callback)


@router.callback_query(F.data == "menu")
async def show_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await callback.message.answer("Выберите действие:", reply_markup=MAIN_MENU)


@router.callback_query(F.data == "lesson")
async def lesson(callback: CallbackQuery) -> None:
    await callback.answer()
    with SessionLocal() as session:
        data = lesson_summary(session, owner_id(callback.from_user))
        lines = [
            f"📚 Неделя {data['week']}/26 · день {data['day']}/182",
            f"Тема: {escape(str(data['topic']))}",
            "Персональный план: "
            f"{escape(adapt_day(session, owner_id(callback.from_user), data['day']))}",
        ]
        if not data["course_imported"]:
            lines.append(
                "Полная программа и слова курса ещё не загружены. "
                "Можно заниматься по встроенному мини-тесту и личному словарю."
            )
        if data["grammar"]:
            lines.append(f"Грамматика: {escape(str(data['grammar'])[:500])}")
        for item in data["tasks"]:
            lines.append(
                f"{'✅' if item['done'] else '▫️'} {item['title']} ({item['minutes']} мин.)"
            )
        lines.append(f"Осталось заданий: {data['remaining']}")
        if callback.message:
            await callback.message.answer(
                "\n".join(lines), reply_markup=lesson_tasks_keyboard(data["tasks"])
            )


@router.callback_query(F.data.startswith("task:"))
async def complete_task_callback(callback: CallbackQuery) -> None:
    key = (callback.data or "").partition(":")[2]
    with SessionLocal() as session:
        uid = owner_id(callback.from_user)
        day = current_day(session, uid)
        if not complete_task(session, uid, day, key):
            await callback.answer("Не удалось отметить этот блок.", show_alert=True)
            return
        finished = finish_day(session, uid, day)
        summary = lesson_summary(session, uid, day)
    await callback.answer("День завершён!" if finished else "Блок отмечен. Прогресс обновлён.")
    if callback.message:
        await callback.message.answer(
            "День завершён. Серия и прогресс обновлены."
            if finished
            else "Блок отмечен. День засчитается после выполнения всех 8 блоков.",
            reply_markup=lesson_tasks_keyboard(summary["tasks"]),
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
            "Отправьте английское слово и перевод через тире, например: "
            "<code>apple — яблоко</code>.\n"
            "Чтобы найти слово, нажмите «🔎 Найти слово» в клавиатуре.",
            parse_mode="HTML",
            reply_markup=BACK,
        )


async def search_start(message: Message, state: FSMContext) -> None:
    await state.set_state(WordState.awaiting_search)
    await answer(message, "Напишите английское слово или перевод для поиска.")


@router.message(WordState.awaiting_search, F.text)
async def search(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    await state.clear()
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
            if review_session.cursor >= len(ids):
                review_session.completed = True
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
            # record_review commits the vocabulary row before Activity and the
            # review cursor are added. Persist the terminal callback explicitly.
            session.commit()
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
        await callback.message.answer(
            "Когда ответите на вопросы, завершите экзамен кнопкой:", reply_markup=EXAM_SUBMIT
        )


@router.callback_query(F.data == "exam:submit")
async def submit_exam_callback(callback: CallbackQuery) -> None:
    result = await submit_exam_for_owner(owner_id(callback.from_user))
    if result is None:
        await callback.answer("Активный экзамен не найден.", show_alert=True)
        return
    await callback.answer("Экзамен завершён.")
    if callback.message:
        await callback.message.answer(
            f"Результат: {result['score']}/{result['total']}\n{result['note']}",
            reply_markup=MAIN_MENU,
        )


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


async def submit_exam_for_owner(uid: int) -> dict | None:
    with SessionLocal() as session:
        exam_session = session.scalar(
            select(ExamSession)
            .where(
                ExamSession.owner_id == uid,
                ExamSession.submitted_at.is_(None),
            )
            .order_by(ExamSession.started_at.desc())
        )
        if not exam_session:
            return None
        return submit_exam(session, exam_session)


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
            f"Тихий режим: {quiet_state}\n\n"
            "Меняйте настройки кнопками под сообщением."
        )
        keyboard = settings_keyboard(settings.reminders_enabled, settings.quiet_mode)
    if callback.message:
        await callback.message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("settings:"))
async def update_settings_callback(callback: CallbackQuery) -> None:
    parts = (callback.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""
    time_value = parts[2] if len(parts) > 2 else ""
    if action == "time":
        try:
            parsed = datetime.strptime(time_value, "%H:%M")
        except ValueError:
            await callback.answer("Некорректное время.", show_alert=True)
            return
        time_value = parsed.strftime("%H:%M")
    with SessionLocal() as session:
        uid = owner_id(callback.from_user)
        row = session.get(UserSettings, uid) or UserSettings(
            owner_id=uid, current_day=1, streak=0, max_streak=0, completed_days=0
        )
        if action == "reminders":
            row.reminders_enabled = not row.reminders_enabled
            notice = "Напоминания включены." if row.reminders_enabled else "Напоминания выключены."
        elif action == "quiet":
            row.quiet_mode = not row.quiet_mode
            notice = "Тихий режим включён." if row.quiet_mode else "Тихий режим выключен."
        elif action == "time":
            row.reminder_time = time_value
            notice = f"Время напоминаний: {time_value} (Ташкент)."
        else:
            await callback.answer("Настройка не найдена.", show_alert=True)
            return
        session.add(row)
        session.commit()
        reminders_enabled, quiet_mode = row.reminders_enabled, row.quiet_mode
    await callback.answer(notice)
    if callback.message:
        await callback.message.edit_reply_markup(
            reply_markup=settings_keyboard(reminders_enabled, quiet_mode)
        )


async def _callback_ack(*_args, **_kwargs) -> None:
    """Acknowledge simulated callbacks used to reuse message-based button handlers."""


def _command_as_callback(message: Message, data: str) -> SimpleNamespace:
    return SimpleNamespace(
        from_user=message.from_user,
        message=message,
        data=data,
        answer=_callback_ack,
    )


@router.message(F.text)
async def unknown_text(message: Message) -> None:
    await answer(
        message,
        "Используйте кнопки меню. Для словаря отправьте пару «слово — перевод».",
        reply_markup=MAIN_MENU,
    )
