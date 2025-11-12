from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅ Назад", callback_data=f"cancel")]
    ])

def language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang:en"),
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="set_lang:uz"),
        ]
    ])
