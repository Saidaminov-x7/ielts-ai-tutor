from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Сегодняшний урок")],
        [
            KeyboardButton(text="🧠 Изучить слова"),
            KeyboardButton(text="🔁 Повторение"),
        ],
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
    ],
    resize_keyboard=True,
    is_persistent=True,
    input_field_placeholder="Выберите действие",
)

BACK = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="⬅️ Главное меню", callback_data="menu")]]
)

MENU_ACTIONS = {
    "📚 Сегодняшний урок": "lesson",
    "🧠 Изучить слова": "words",
    "🔁 Повторение": "review",
    "📝 Мини-тест": "quiz",
    "✍️ Writing": "writing",
    "📊 Мой прогресс": "progress",
    "❌ Мои ошибки": "errors",
    "🏆 Еженедельный экзамен": "exam",
    "⚙️ Настройки": "settings",
}
