from aiogram.utils.keyboard import InlineKeyboardBuilder

def bots_keyboard(bots):
    builder = InlineKeyboardBuilder()
    for b in bots:
        builder.button(
            text=b.get("display_name") or b["username"],
            callback_data=f"select_bot:{b['username']}"
        )
    builder.adjust(1)
    return builder.as_markup()
