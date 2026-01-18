from aiogram import types, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from ..core.utils import get_plans_for_bot, create_mock_payment, get_payment_methods
from ..config import ADMIN_CHANNEL_ID, bot
from ..keyboards.buy import payment_methods_keyboard
import logging


router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("buy:"))
async def handle_buy(callback: types.CallbackQuery, state: FSMContext):
    try:
        _, bot_id_str, plan_id_str = callback.data.split(":")
        bot_id, plan_id = int(bot_id_str), int(plan_id_str)
    except Exception as e:
        logger.exception(f"Error: {e}")
        await callback.answer("Ошибка в данных кнопки", show_alert=True)
        return

    plans = await get_plans_for_bot(bot_id)
    plan = next((p for p in plans if p["id"] == plan_id), None)
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    text = (
        f"Вы выбрали: <b>{plan['name']}</b>\n"
        f"💰 Цена: <b>{plan['price_usdt']}$</b>\n\n"
        "Выберите способ оплаты:"
    )

    payment_methods = await get_payment_methods()

    await callback.message.edit_text(text, reply_markup=payment_methods_keyboard(bot_id, plan_id, plan, payment_methods), parse_mode="html")
    await callback.answer()


@router.callback_query(F.data.startswith("do_payment:"))
async def handle_payment(callback: types.CallbackQuery):
    _, bot_id_str, plan_id_str = callback.data.split(":")
    bot_id, plan_id = int(bot_id_str), int(plan_id_str)
    user_id = callback.from_user.id

    await callback.message.edit_text("🔄 Инициализация платежа (тест)...")
    resp = await create_mock_payment(telegram_id=user_id, bot_id=bot_id, plan_id=plan_id)

    if not resp or resp.get("error"):
        await callback.message.edit_text("❌ Ошибка при создании платежа. Попробуйте позже.")
        logger.error("Payment failed: %s", resp)
        return

    if resp.get("status") == "success":
        await callback.message.edit_text("✅ Оплата успешна! Подписка активирована.")

        try:
            if ADMIN_CHANNEL_ID:
                await bot.send_message(
                    ADMIN_CHANNEL_ID,
                    (
                        f"🛒 <b>Новая покупка</b>\n"
                        f"👤 Пользователь: <code>{user_id}</code> (@{callback.from_user.username or '—'})\n"
                        f"Метод: <b>stub</b>\n"
                        f"План ID: <b>{plan_id}</b>\n"
                        f"Бот ID: <b>{bot_id}</b>"
                    ),
                    parse_mode="html"
                )
        except Exception as e:
            logger.exception("Failed to send admin notification: %s", e)
    else:
        await callback.message.edit_text("❗ Платёж не удался или в статусе pending.")


@router.message(Command("refund"))
async def cmd_refund(message: types.Message):
    t_id = "stxXpydIU27cMOF4cBda3U9H6554KpeGUnsL5lDXjXZ1CczakYNl772iEPY0YUOtTr7D24uTn-6KB6riv65pDQOApGyDiav21RIxzNZvF19Re4"

    if t_id is None:
        await message.answer("Transaction not found!")
        return

    try:
        await bot.refund_star_payment(
            user_id=message.from_user.id,
            telegram_payment_charge_id=t_id
        )
        await message.answer("Done")

    except TelegramBadRequest as e:
        print(e)
