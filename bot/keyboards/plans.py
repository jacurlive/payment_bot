from aiogram.utils.keyboard import InlineKeyboardBuilder


def plans_keyboard(plans, bot_id):
    builder = InlineKeyboardBuilder()
    for plan in plans:
        if plan.get("is_active"):
            builder.button(
                text=f"{plan['name']} — {plan['price']}",
                callback_data=f"buy:{bot_id}:{plan['id']}"
            )
    builder.button(text="⬅️ Назад", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()
