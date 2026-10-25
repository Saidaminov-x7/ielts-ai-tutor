from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from app.config import get_settings

_LEGACY_MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Сегодняшний урок")],
        [
            KeyboardButton(text="🧠 Изучить слова"),
            KeyboardButton(text="🔁 Повторение"),
        ],
        [KeyboardButton(text="🔎 Найти слово")],
        [
            KeyboardButton(text="📝 Мини-тест"),
            KeyboardButton(text="✍️ Writing"),
        ],
        [
            KeyboardButton(text="📊 Мой прогресс"),
            KeyboardButton(text="❌ Мои ошибки"),
        ],
        [
            KeyboardButton(text="🏆 Еженедельный экзамен"),
            KeyboardButton(text="⚙️ Настройки"),
        ],
        [KeyboardButton(text="🏠 Главное меню")],
    ],
    resize_keyboard=True,
    is_persistent=True,
    input_field_placeholder="Выберите действие",
)

_mini_app_url = get_settings().webhook_base_url
if _mini_app_url and _mini_app_url.startswith("https://"):
    MAIN_MENU = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Открыть приложение")]
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
else:
    MAIN_MENU = _LEGACY_MAIN_MENU

BACK = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="⬅️ Главное меню", callback_data="menu")]]
)

MENU_ACTIONS = {
    "🚀 Открыть приложение": "app",
    "🏠 Главное меню": "menu",
    "📚 Сегодняшний урок": "lesson",
    "🧠 Изучить слова": "words",
    "🔎 Найти слово": "search",
    "🔁 Повторение": "review",
    "📝 Мини-тест": "quiz",
    "✍️ Writing": "writing",
    "📊 Мой прогресс": "progress",
    "❌ Мои ошибки": "errors",
    "🏆 Еженедельный экзамен": "exam",
    "⚙️ Настройки": "settings",
}


def mini_app_launch_keyboard(url: str, tab: str | None = None) -> InlineKeyboardMarkup:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if tab in {"home", "lesson", "practice", "exam", "words", "insights", "settings", "writing"}:
        query["tab"] = tab
    app_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Открыть приложение", web_app=WebAppInfo(url=app_url))]
        ]
    )


def lesson_tasks_keyboard(tasks: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'✅' if row['done'] else '▫️'} {row['title']}",
                    callback_data=f"task:{row['key']}",
                )
            ]
            for row in tasks
        ]
    )


def settings_keyboard(reminders: bool, quiet: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🔔 Напоминания: {'вкл' if reminders else 'выкл'}",
                    callback_data="settings:reminders",
                ),
                InlineKeyboardButton(
                    text=f"🌙 Тихий режим: {'вкл' if quiet else 'выкл'}",
                    callback_data="settings:quiet",
                ),
            ],
            [
                InlineKeyboardButton(text=time, callback_data=f"settings:time:{time}")
                for time in ("08:00", "12:00", "19:00", "21:00")
            ],
        ]
    )


EXAM_SUBMIT = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🏁 Завершить экзамен", callback_data="exam:submit")]
    ]
)
