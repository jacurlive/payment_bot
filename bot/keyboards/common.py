from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅ Назад", callback_data=f"cancel")]
    ])
