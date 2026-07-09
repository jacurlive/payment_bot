from aiogram import types, F, Router
from aiogram.types import LabeledPrice, PreCheckoutQuery
from aiogram.exceptions import TelegramBadRequest
from aiocryptopay import AioCryptoPay, Networks

from ..config import bot
from ..core.utils import create_mock_payment, get_plans_for_bot, get_user_language, \
    send_purchase_message_to_user
from ..core.localization import get_localized_message
from ..core.platega import create_platega_transaction, check_platega_transaction, \
    PLATEGA_METHOD_CARD, PLATEGA_METHOD_SBP
from ..keyboards.common import back_keyboard

import logging
import os


router = Router()
logger = logging.getLogger(__name__)

STARS_RATE = float(os.getenv("STARS_RATE", 0.017))


CRYPTO_PAY_TOKEN = os.getenv("CRYPTO_PAY_TOKEN")

# ------------- CRYPTO -----------------
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

        await crypto.close()
        pay_url = invoice.bot_invoice_url
        invoice_id = invoice.invoice_id

        localized_message_1 = await get_localized_message(language, "pay_crypto_bot")
        localized_message_2 = await get_localized_message(language, "check_crypto_pay")
        localized_message_3 = await get_localized_message(language, "back_btn")

        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text=localized_message_1, url=pay_url)],
                [types.InlineKeyboardButton(
                    text=localized_message_2,
                    callback_data=f"check_crypto:{invoice_id}:{bot_id}:{plan_id}"  # ← передаём invoice_id
                )],
                [types.InlineKeyboardButton(text=localized_message_3, callback_data="cancel")]
            ]
        )

        localized_message_1 = await get_localized_message(language, "payment_from")
        localized_message_2 = await get_localized_message(language, 'plan')
        localized_message_3 = await get_localized_message(language, 'price')
        localized_message_4 = await get_localized_message(language, 'after_buy_text')
        localized_message_5 = await get_localized_message(language, 'message_check_crypto_pay')

        await callback.message.edit_text(
            f"💸 {localized_message_1} <b>CryptoBot</b>\n\n"
            f"{localized_message_2}: <b>{plan['name']}</b>\n"
            f"{localized_message_3}: <b>{price_usdt} USDT</b>\n\n"
            f"{localized_message_4}\n\n"
            f"{localized_message_5}",  # ← подсказка
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
    """
    Проверка оплаты через CryptoBot
    """
    try:
        _, invoice_id_str, bot_id_str, plan_id_str = callback.data.split(":")
        invoice_id = int(invoice_id_str)
        bot_id = int(bot_id_str)
        plan_id = int(plan_id_str)
    except Exception as e:
        logger.exception(f"Ошибка парсинга callback_data: {e}")
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return

    user_id = callback.from_user.id
    language = await get_user_language(user_id)

    crypto = AioCryptoPay(CRYPTO_PAY_TOKEN)

    try:
        invoices = await crypto.get_invoices(invoice_ids=[invoice_id])
        await crypto.close()

        if not invoices or len(invoices) == 0:
            localized_message = await get_localized_message(language, "not_paid")
            await callback.answer(localized_message, show_alert=True)
            return

        invoice = invoices[0]

        if invoice.status != "paid":
            localized_message = await get_localized_message(language, "not_paid")
            await callback.answer(localized_message, show_alert=True)
            return

    except Exception as e:
        logger.exception(f"Ошибка при проверке инвойса: {e}")
        await callback.answer("❌ Ошибка проверки оплаты", show_alert=True)
        return

    localized_message = await get_localized_message(language, "paid")
    await callback.message.edit_text(localized_message)

    resp = await create_mock_payment(
        telegram_id=user_id,
        bot_id=bot_id,
        plan_id=plan_id,
        method="crypto"
    )

    if resp.get("status") == "success":
        try:
            plans = await get_plans_for_bot(bot_id)
            plan = next((p for p in plans if p["id"] == plan_id), None)

            if plan:
                await send_purchase_message_to_user(
                    user_id=user_id,
                    bot_id=bot_id,
                    plan_id=plan_id,
                    language=language
                )
        except Exception as e:
            logger.exception("Failed to send purchase notification: %s", e)
    else:
        localized_message = await get_localized_message(language, 'paid_but_not_activated')
        await callback.message.answer(localized_message, reply_markup=back_keyboard())


# ------------- PLATEGA (карта / СБП) -----------------
async def _handle_platega_payment(
    callback: types.CallbackQuery,
    payment_method_code: int,
    method_name: str,
    display_name: str,
    emoji: str,
    btn_message_key: str
):
    """
    Общая логика создания платежа через Platega (карта / СБП)
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

    price_rub = plan["price_rub"]
    if not price_rub:
        localized_message = await get_localized_message(language, "not_plan")
        await callback.answer(localized_message, show_alert=True)
        return

    payload = f"{user_id}:{bot_id}:{plan_id}:{method_name}"

    try:
        transaction = await create_platega_transaction(
            payment_method=payment_method_code,
            amount=price_rub,
            description=f"Подписка {plan['name']} ({plan['duration_days']} дней)",
            payload=payload
        )

        if not transaction or not transaction.get("redirect") or not transaction.get("transactionId"):
            raise ValueError(f"Некорректный ответ Platega: {transaction}")

        pay_url = transaction["redirect"]
        transaction_id = transaction["transactionId"]

        localized_message_1 = await get_localized_message(language, btn_message_key)
        localized_message_2 = await get_localized_message(language, "check_crypto_pay")
        localized_message_3 = await get_localized_message(language, "back_btn")

        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text=localized_message_1, url=pay_url)],
                [types.InlineKeyboardButton(
                    text=localized_message_2,
                    callback_data=f"check_platega:{transaction_id}"
                )],
                [types.InlineKeyboardButton(text=localized_message_3, callback_data="cancel")]
            ]
        )

        localized_message_1 = await get_localized_message(language, "payment_from")
        localized_message_2 = await get_localized_message(language, 'plan')
        localized_message_3 = await get_localized_message(language, 'price')
        localized_message_4 = await get_localized_message(language, 'after_buy_text')
        localized_message_5 = await get_localized_message(language, 'message_check_crypto_pay')

        await callback.message.edit_text(
            f"{emoji} {localized_message_1} <b>{display_name}</b>\n\n"
            f"{localized_message_2}: <b>{plan['name']}</b>\n"
            f"{localized_message_3}: <b>{price_rub} RUB</b>\n\n"
            f"{localized_message_4}\n\n"
            f"{localized_message_5}",
            parse_mode="HTML",
            reply_markup=kb,
            disable_web_page_preview=True
        )
        await callback.answer()

    except Exception as e:
        localized_message = await get_localized_message(language, 'platega_invoice_error')
        logger.exception(f"Ошибка при создании платежа через Platega ({method_name}): {e}")
        await callback.message.answer(localized_message, reply_markup=back_keyboard())
        await callback.answer()


@router.callback_query(F.data.startswith("pay_card:"))
async def handle_platega_card_payment(callback: types.CallbackQuery):
    """
    Обработка кнопки оплаты картой через Platega
    """
    await _handle_platega_payment(
        callback, PLATEGA_METHOD_CARD, "platega_card", "Картой", "💳", "pay_platega_card_btn"
    )


@router.callback_query(F.data.startswith("pay_sbp:"))
async def handle_platega_sbp_payment(callback: types.CallbackQuery):
    """
    Обработка кнопки оплаты через СБП (Platega)
    """
    await _handle_platega_payment(
        callback, PLATEGA_METHOD_SBP, "platega_sbp", "СБП", "🏦", "pay_platega_sbp_btn"
    )


@router.callback_query(F.data.startswith("check_platega:"))
async def check_platega_payment(callback: types.CallbackQuery):
    """
    Проверка статуса оплаты Platega (карта / СБП).
    Активацию подписки выполняет вебхук — здесь только информируем пользователя.
    """
    try:
        _, transaction_id = callback.data.split(":", 1)
    except Exception as e:
        logger.exception(f"Ошибка парсинга callback_data: {e}")
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return

    user_id = callback.from_user.id
    language = await get_user_language(user_id)

    transaction = await check_platega_transaction(transaction_id)

    if not transaction:
        await callback.answer("❌ Ошибка проверки оплаты", show_alert=True)
        return

    if transaction.get("status") != "CONFIRMED":
        localized_message = await get_localized_message(language, "not_paid")
        await callback.answer(localized_message, show_alert=True)
        return

    localized_message = await get_localized_message(language, "platega_payment_confirmed")
    await callback.message.edit_text(localized_message)
    await callback.answer()


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
        plan_id=plan_id,
        method='stars'
    )
    if resp.get("status") == "success":
        localized_message = await get_localized_message(language, 'stars_payment_success')
        await message.answer(localized_message)
        try:
            plans = await get_plans_for_bot(bot_id)
            plan = next((p for p in plans if p["id"] == plan_id), None)

            if plan:
                await send_purchase_message_to_user(
                    user_id=user_id,
                    bot_id=bot_id,
                    plan_id=plan_id,
                    language=language
                )
        except Exception as e:
            logger.exception("Failed to send admin notification: %s", e)
    else:
        localized_message = await get_localized_message(language, 'paid_but_not_activated')
        await message.answer(localized_message, reply_markup=back_keyboard())
