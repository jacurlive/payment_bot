from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def payment_methods_keyboard(bot_id: int, plan_id: int, plan: dict, payment_methods: dict):
    buttons = []

    for m in payment_methods:
        cb = m.get("callback_data")
        name = m.get("name", "")

        if cb == "pay_stars":
            text = f"💫 Telegram Stars — ⭐️ {plan['price_stars']}"
        elif cb == "pay_crypto":
            text = f"🌏 CryptoBot — ${plan['price_usdt']}"
        elif cb == "pay_click":
            text = f"💳 Click — {int(float(plan['price_uzs'])):,} UZS"
        elif cb == "pay_payme":
            text = f"💳 PayMe — {int(float(plan['price_uzs'])):,} UZS"
        elif cb == "pay_russia":
            text = f"💰 РФ оплата — {plan['price_rub']} RUB"
        elif cb == "pay_card":
            text = f"💳 Карта — {plan['price_rub']} RUB"
        elif cb == "pay_sbp":
            text = f"🏦 СБП — {plan['price_rub']} RUB"
        else:
            text = f"{name}"

        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"{cb}:{bot_id}:{plan_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
