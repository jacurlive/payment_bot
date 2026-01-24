from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def language_selection_keyboard():
    """
    Клавиатура для выбора языка
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
            ],
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang:uz"),
            ]
        ]
    )
    return keyboard