from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def payment_methods_keyboard(bot_id: int, plan_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚜️ CryptoBot", callback_data=f"pay_cryptobot:{bot_id}:{plan_id}"),
            InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"pay_stars:{bot_id}:{plan_id}"),
        ],
        [InlineKeyboardButton(text="⬅ Назад", callback_data=f"back_to_plans:{bot_id}")]
    ])
