from aiogram import types, F, Router
from aiogram.types import LabeledPrice, PreCheckoutQuery
from aiogram.exceptions import TelegramBadRequest

from ..config import bot, ADMIN_CHANNEL_ID
from ..core.utils import create_mock_payment, get_plans_for_bot

import logging
import os


router = Router()
logger = logging.getLogger(__name__)

STARS_RATE = float(os.getenv("STARS_RATE", 235.998))


@router.callback_query(F.data.startswith("pay_stars:"))
async def handle_telegram_stars_payment(callback: types.CallbackQuery):
    """
    Обработка кнопки оплаты через Telegram Stars
    """
    try:
        _, bot_id_str, plan_id_str = callback.data.split(":")
        bot_id, plan_id = int(bot_id_str), int(plan_id_str)
    except Exception:
        await callback.answer("Ошибка данных кнопки", show_alert=True)
        return

    plans = await get_plans_for_bot(bot_id)
    plan = next((p for p in plans if p["id"] == plan_id), None)
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    price_uzs = float(plan["price"])
    price_stars = round(price_uzs / STARS_RATE)
    logger.info(f"Converted {price_uzs} UZS → {price_stars} Stars (rate {STARS_RATE})")


    price = [LabeledPrice(label=plan["name"], amount=1)]
    title = plan["name"]
    description = f"Подписка на {plan['duration_days']} дней"

    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=title,
            description=description,
            payload=f"{bot_id}:{plan_id}",
            provider_token="",
            currency="XTR",  # 💫 Telegram Stars
            prices=price,
        )
        await callback.answer()
    except TelegramBadRequest as e:
        await callback.message.answer("❌ Не удалось создать счёт через Telegram Stars.")
        print("Telegram invoice error:", e)
        await callback.answer()


# --- Обработка успешного платежа через Telegram Stars ---
@router.pre_checkout_query()
async def pre_checkout_query_handler(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    payload = message.successful_payment.invoice_payload
    bot_id, plan_id = map(int, payload.split(":"))
    user_id = message.from_user.id

    resp = await create_mock_payment(
        telegram_id=message.from_user.id,
        bot_id=bot_id,
        plan_id=plan_id
    )

    if resp.get("status") == "success":
        await message.answer("✅ Оплата через Telegram Stars прошла успешно!")
        try:
            if ADMIN_CHANNEL_ID:
                await bot.send_message(
                    ADMIN_CHANNEL_ID,
                    (
                        f"🛒 <b>Новая покупка</b>\n"
                        f"👤 Пользователь: <code>{user_id}</code> (@{message.from_user.username or '—'})\n"
                        f"Метод: <b>stub</b>\n"
                        f"План ID: <b>{plan_id}</b>\n"
                        f"Бот ID: <b>{bot_id}</b>"
                    ),
                    parse_mode="html"
                )
        except Exception as e:
            logger.exception("Failed to send admin notification: %s", e)
    else:
        await message.answer("⚠️ Оплата прошла, но не удалось активировать подписку.")
