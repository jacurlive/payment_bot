from aiogram import types, F, Router
from aiogram.types import LabeledPrice, PreCheckoutQuery
from aiogram.exceptions import TelegramBadRequest
from aiocryptopay import AioCryptoPay, Networks

from ..config import bot
from ..core.utils import create_mock_payment, get_plans_for_bot, send_payment_notification, get_user_language
from ..core.localization import get_localized_message
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
    user_id = callback.from_user.id
    language = await get_user_language(user_id)
    try:
        _, bot_id_str, plan_id_str = callback.data.split(":")
        bot_id, plan_id = int(bot_id_str), int(plan_id_str)
    except Exception as e:
        localized_message = await get_localized_message(language, "button_data_error")
        await callback.answer(localized_message, show_alert=True)
        logger.exception(f"Error parsing callback data: {e}")
        return

    plans = await get_plans_for_bot(bot_id)
    plan = next((p for p in plans if p["id"] == plan_id), None)
    if not plan:
        localized_message = await get_localized_message(language, "not_plan")
        await callback.answer(localized_message, show_alert=True)
        return

    price_usdt = float(plan["price_usdt"])

    try:
        crypto = AioCryptoPay(token=CRYPTO_PAY_TOKEN, network=Networks.MAIN_NET)

        invoice = await crypto.create_invoice(
            asset="USDT",
            amount=int(price_usdt),
            description=f"Подписка {plan['name']} ({plan['duration_days']} дней)"
        )

        localized_message_1 = await get_localized_message(language, "pay_crypto_bot")
        localized_message_2 = await get_localized_message(language, "back_btn")
        await crypto.close()
        pay_url = invoice.bot_invoice_url

        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text=localized_message_1, url=pay_url)],
                [types.InlineKeyboardButton(text=localized_message_2, callback_data="cancel")]
            ]
        )

        localized_message_1 = await get_localized_message(language, "payment_from")
        localized_message_2 = await get_localized_message(language, 'plan')
        localized_message_3 = await get_localized_message(language, 'price')
        localized_message_4 = await get_localized_message(language, 'after_buy_text')
        await callback.message.edit_text(
            f"💸 {localized_message_1} <b>CryptoBot</b>\n\n"
            f"{localized_message_2}: <b>{plan['name']}</b>\n"
            f"{localized_message_3}: <b>{price_usdt} USDT</b>\n\n"
            f"{localized_message_4}",
            parse_mode="HTML",
            reply_markup=kb,
            disable_web_page_preview=True
        )
        await callback.answer()

    except Exception as e:
        localized_message = await get_localized_message(language, 'crypto_invoice_error')
        logger.exception(f"Ошибка при создании платежа через CryptoBot: {e}")
        await callback.message.answer(localized_message, reply_markup=back_keyboard())
        await callback.answer()


@router.callback_query(F.data.startswith("check_crypto:"))
async def check_crypto_payment(callback: types.CallbackQuery):
    _, invoice_id_str, bot_id_str, plan_id_str = callback.data.split(":")
    invoice_id = int(invoice_id_str)
    bot_id = int(bot_id_str)
    plan_id = int(plan_id_str)
    user_id = callback.message.from_user.id
    language = await get_user_language(user_id)

    crypto = AioCryptoPay(CRYPTO_PAY_TOKEN)
    invoice = await crypto.get_invoices(invoice_ids=[invoice_id])
    await crypto.close()

    if not invoice or invoice.status != "paid":
        localized_message = await get_localized_message(language, "not_paid")
        await callback.answer(localized_message, show_alert=True)
        return

    localized_message = await get_localized_message(language, "paid")
    await callback.message.edit_text(localized_message)
    resp = await create_mock_payment(
        telegram_id=callback.message.from_user.id,
        bot_id=bot_id,
        plan_id=plan_id
    )

    if resp.get("status") == "success":
        try:
            plans = await get_plans_for_bot(bot_id)
            plan = next((p for p in plans if p["id"] == plan_id), None)

            if plan:
                await send_payment_notification(
                    telegram_id=callback.from_user.id,
                    bot_id=bot_id,
                    plan_id=plan_id,
                    payment_method="crypto",
                    amount=plan["price_usdt"],
                    transaction_id=str(invoice_id)
                )
        except Exception as e:
            logger.exception("Failed to send admin notification: %s", e)
    else:
        localized_message = await get_localized_message(language, 'paid_but_not_activated')
        await callback.message.answer(localized_message, reply_markup=back_keyboard())


# ---------- Telegram Stars ---------
@router.callback_query(F.data.startswith("pay_stars:"))
async def handle_telegram_stars_payment(callback: types.CallbackQuery):
    """
    Обработка кнопки оплаты через Telegram Stars
    """
    user_id = callback.from_user.id
    language = await get_user_language(user_id)

    try:
        _, bot_id_str, plan_id_str = callback.data.split(":")
        bot_id, plan_id = int(bot_id_str), int(plan_id_str)
    except Exception as e:
        localized_message = await get_localized_message(language, 'button_data_error')
        await callback.answer(localized_message, show_alert=True)
        logger.exception(f"Error: {e}")
        return

    plans = await get_plans_for_bot(bot_id)
    plan = next((p for p in plans if p["id"] == plan_id), None)
    if not plan:
        localized_message = await get_localized_message(language, 'not_plan')
        await callback.answer(localized_message, show_alert=True)
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
        localized_message = await get_localized_message(language, 'stars_invoice_error')
        await callback.message.answer(localized_message, reply_markup=back_keyboard())
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
    language = await get_user_language(user_id)

    resp = await create_mock_payment(
        telegram_id=message.from_user.id,
        bot_id=bot_id,
        plan_id=plan_id
    )
    print(resp)
    if resp.get("status") == "success":
        localized_message = await get_localized_message(language, 'stars_payment_success')
        await message.answer(localized_message)
        try:
            plans = await get_plans_for_bot(bot_id)
            plan = next((p for p in plans if p["id"] == plan_id), None)

            if plan:
                await send_payment_notification(
                    telegram_id=user_id,
                    bot_id=bot_id,
                    plan_id=plan_id,
                    payment_method="stars",
                    amount=plan["price_stars"],
                    transaction_id=message.successful_payment.telegram_payment_charge_id
                )
        except Exception as e:
            logger.exception("Failed to send admin notification: %s", e)
    else:
        localized_message = await get_localized_message(language, 'paid_but_not_activated')
        await message.answer(localized_message, reply_markup=back_keyboard())
