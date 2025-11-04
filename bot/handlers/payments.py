from aiogram import types, F, Router
from aiogram.types import LabeledPrice, PreCheckoutQuery
from aiogram.exceptions import TelegramBadRequest
from aiocryptopay import AioCryptoPay, Networks

from ..config import bot, ADMIN_CHANNEL_ID
from ..core.utils import create_mock_payment, get_plans_for_bot
from ..keyboards.common import back_keyboard

import logging
import os


router = Router()
logger = logging.getLogger(__name__)

STARS_RATE = float(os.getenv("STARS_RATE", 0.017))


CRYPTO_PAY_TOKEN = os.getenv("CRYPTO_PAY_TOKEN")

# ---------- CRYPTO ----------
@router.callback_query(F.data.startswith("pay_crypto:"))
async def handle_crypto_payment(callback: types.CallbackQuery):
    """
    Обработка кнопки оплаты через CryptoBot
    """
    try:
        _, bot_id_str, plan_id_str = callback.data.split(":")
        bot_id, plan_id = int(bot_id_str), int(plan_id_str)
    except Exception as e:
        await callback.answer("Ошибка данных кнопки", show_alert=True)
        logger.exception(f"Error parsing callback data: {e}")
        return

    plans = await get_plans_for_bot(bot_id)
    plan = next((p for p in plans if p["id"] == plan_id), None)
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    price_usdt = float(plan["price_usdt"])

    try:
        crypto = AioCryptoPay(token=CRYPTO_PAY_TOKEN, network=Networks.MAIN_NET)

        invoice = await crypto.create_invoice(
            asset="USDT",
            amount=int(price_usdt),
            description=f"Подписка {plan['name']} ({plan['duration_days']} дней)"
        )

        await crypto.close()
        pay_url = invoice.bot_invoice_url  # ✅ актуальное поле

        # Клавиатура с кнопкой оплаты
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="💳 Оплатить через CryptoBot", url=pay_url)],
                [types.InlineKeyboardButton(text="🔙 Назад", callback_data="cancel")]
            ]
        )

        await callback.message.edit_text(
            f"💸 Оплата через <b>CryptoBot</b>\n\n"
            f"Тариф: <b>{plan['name']}</b>\n"
            f"Сумма: <b>{price_usdt} USDT</b>\n\n"
            "После оплаты бот активирует подписку автоматически ✅",
            parse_mode="HTML",
            reply_markup=kb,
            disable_web_page_preview=True
        )
        await callback.answer()

    except Exception as e:
        logger.exception(f"Ошибка при создании платежа через CryptoBot: {e}")
        await callback.message.answer("❌ Ошибка при создании платежа через CryptoBot.", reply_markup=back_keyboard())
        await callback.answer()



@router.callback_query(F.data.startswith("check_crypto:"))
async def check_crypto_payment(callback: types.CallbackQuery):
    _, invoice_id_str, bot_id_str, plan_id_str = callback.data.split(":")
    invoice_id = int(invoice_id_str)
    bot_id = int(bot_id_str)
    plan_id = int(plan_id_str)

    crypto = AioCryptoPay(CRYPTO_PAY_TOKEN)
    invoice = await crypto.get_invoices(invoice_ids=[invoice_id])
    await crypto.close()

    if not invoice or invoice.status != "paid":
        await callback.answer("❗ Оплата ещё не получена", show_alert=True)
        return

    await callback.message.edit_text("✅ Оплата получена! Подписка активирована.")
    resp = await create_mock_payment(
        telegram_id=callback.message.from_user.id,
        bot_id=bot_id,
        plan_id=plan_id
    )

    if resp.get("status") == "success":
        try:
            if ADMIN_CHANNEL_ID:
                await callback.bot.send_message(
                    ADMIN_CHANNEL_ID,
                    f"💰 <b>CryptoBot оплата</b>\n"
                    f"👤 @{callback.from_user.username or '—'} ({callback.from_user.id})\n"
                    f"План ID: {plan_id}\n"
                    f"Бот ID: {bot_id}"
                )
        except Exception as e:
            logger.exception("Failed to send admin notification: %s", e)
    else:
        await callback.message.answer("⚠️ Оплата прошла, но не удалось активировать подписку.", reply_markup=back_keyboard())


# ---------- Telegram Stars ---------
@router.callback_query(F.data.startswith("pay_stars:"))
async def handle_telegram_stars_payment(callback: types.CallbackQuery):
    """
    Обработка кнопки оплаты через Telegram Stars
    """
    try:
        _, bot_id_str, plan_id_str = callback.data.split(":")
        bot_id, plan_id = int(bot_id_str), int(plan_id_str)
    except Exception as e:
        await callback.answer("Ошибка данных кнопки", show_alert=True)
        logger.exception(f"Error: {e}")
        return

    plans = await get_plans_for_bot(bot_id)
    plan = next((p for p in plans if p["id"] == plan_id), None)
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    price_stars = plan["price_stars"]
    # logger.info(f"Converted {price_usd} USD → {price_stars} Stars (rate {STARS_RATE})")

    price = [LabeledPrice(label=plan["name"], amount=price_stars)]
    title = plan["name"]
    description = f"Подписка на {plan['duration_days']} дней"

    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=title,
            description=description,
            payload=f"{bot_id}:{plan_id}",
            provider_token="",
            currency="XTR",
            prices=price,
        )
        await callback.answer()
    except TelegramBadRequest as e:
        await callback.message.answer("❌ Не удалось создать счёт через Telegram Stars.", reply_markup=back_keyboard())
        print("Telegram invoice error:", e)
        await callback.answer()


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
        await message.answer("⚠️ Оплата прошла, но не удалось активировать подписку.", reply_markup=back_keyboard())
