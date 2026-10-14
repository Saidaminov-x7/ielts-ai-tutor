from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

MAIN_MENU = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📚 Сегодняшний урок", callback_data="lesson")],
        [
            InlineKeyboardButton(text="🧠 Изучить слова", callback_data="words"),
            InlineKeyboardButton(text="🔁 Повторение", callback_data="review"),
        ],
        [
            InlineKeyboardButton(text="📝 Мини-тест", callback_data="quiz"),
            InlineKeyboardButton(text="✍️ Writing", callback_data="writing"),
        ],
        [
            InlineKeyboardButton(text="📊 Мой прогресс", callback_data="progress"),
            InlineKeyboardButton(text="❌ Мои ошибки", callback_data="errors"),
        ],
        [
            InlineKeyboardButton(text="🏆 Еженедельный экзамен", callback_data="exam"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
        ],
    ]
)

BACK = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="⬅️ Главное меню", callback_data="menu")]]
)
