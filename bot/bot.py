import os
import logging
import asyncio
import datetime
from typing import Optional

from dotenv import load_dotenv
import httpx
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# -----------------------
# Настройки и окружение
# -----------------------
load_dotenv()

ACCESS_TOKEN = None
REFRESH_TOKEN = None
TOKEN_EXPIRES = None

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
ADMIN_CHANNEL_ID = int(os.getenv("ADMIN_CHANNEL_ID", "0"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

http_client = httpx.AsyncClient(timeout=15.0)

# -----------------------
# Утилиты
# -----------------------

async def get_jwt_token():
    global ACCESS_TOKEN, REFRESH_TOKEN, TOKEN_EXPIRES

    # 🔹 Если токен ещё валиден — просто возвращаем
    if ACCESS_TOKEN and TOKEN_EXPIRES and TOKEN_EXPIRES > datetime.datetime.utcnow():
        return ACCESS_TOKEN

    login_url = f"{BACKEND_URL}/api/token/"
    credentials = {
        "username": os.getenv("BACKEND_USERNAME"),
        "password": os.getenv("BACKEND_PASSWORD"),
    }

    try:
        resp = await http_client.post(login_url, json=credentials)
        if resp.status_code == 200:
            data = resp.json()
            ACCESS_TOKEN = data.get("access")
            REFRESH_TOKEN = data.get("refresh")

            # 🔹 Токен живёт 30 дней
            TOKEN_EXPIRES = datetime.datetime.utcnow() + datetime.timedelta(days=30)

            logger.info("JWT token successfully obtained, valid until %s", TOKEN_EXPIRES)
            return ACCESS_TOKEN
        else:
            logger.error("Failed to obtain JWT token: %s", resp.text)
            return None

    except Exception as e:
        logger.exception("get_jwt_token exception: %s", e)
        return None


async def get_all_bots_from_backend() -> list:
    token = await get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        resp = await http_client.get(f"{BACKEND_URL}/api/bots/", headers=headers)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.exception("get_all_bots_from_backend error: %s", e)
    return []


async def get_bot_by_username_from_backend(botusername: str) -> Optional[dict]:
    token = await get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        resp = await http_client.get(f"{BACKEND_URL}/api/bots/", params={"username": botusername}, headers=headers)
        if resp.status_code == 200:
            items = resp.json()
            if isinstance(items, list) and len(items) == 1:
                return items[0]
            if isinstance(items, dict) and "results" in items and items["results"]:
                return items["results"][0]
        return None
    except Exception as e:
        logger.exception("get_bot_by_username error: %s", e)
        return None


async def get_plans_for_bot(bot_id: int) -> list:
    token = await get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        resp = await http_client.get(f"{BACKEND_URL}/api/plans/", params={"bot": bot_id}, headers=headers)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.exception("get_plans_for_bot error: %s", e)
    return []


async def create_mock_payment(telegram_id: int, bot_id: int, plan_id: int, method: str = "stub"):
    token = await get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    payload = {"telegram_id": telegram_id, "bot_id": bot_id, "plan_id": plan_id, "method": method}
    try:
        resp = await http_client.post(f"{BACKEND_URL}/api/payments/mock/", json=payload, headers=headers)
        if resp.status_code in (200, 201):
            return resp.json()
        logger.error("create_mock_payment failed: %s %s", resp.status_code, resp.text)
        return {"error": resp.text, "status_code": resp.status_code}
    except Exception as e:
        logger.exception("create_mock_payment exception: %s", e)
        return {"error": str(e)}

# -----------------------
# Клавиатуры
# -----------------------

def plans_to_kb(plans: list, bot_id: int):
    builder = InlineKeyboardBuilder()
    for plan in plans:
        if not plan.get("is_active"):
            continue
        pid = plan["id"]
        name = plan.get("name") or f"{plan.get('duration_days') or '∞'} дней"
        price = plan.get("price") or "0"
        builder.button(
            text=f"{name} — {price}",
            callback_data=f"buy:{bot_id}:{pid}",
        )
    builder.button(text="Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()


def bots_to_kb(bots: list):
    builder = InlineKeyboardBuilder()
    for b in bots:
        builder.button(
            text=b.get("display_name") or b["username"],
            callback_data=f"select_bot:{b['username']}",
        )
    builder.adjust(1)
    return builder.as_markup()

# -----------------------
# Хендлеры
# -----------------------

@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject, state: FSMContext):
    args = command.args
    user_id = message.from_user.id
    logger.info("User %s started with args: %s", user_id, args)

    # ✅ Если пользователь передал username — сразу загружаем этого бота
    if args:
        botusername = args.strip().lstrip("@")
        backend_bot = await get_bot_by_username_from_backend(botusername)
        if not backend_bot:
            await message.answer("❌ Бот не найден. Попробуйте позже.")
            return

        plans = await get_plans_for_bot(backend_bot["id"])
        if not plans:
            await message.answer("Для этого бота пока нет активных тарифов.")
            return

        kb = plans_to_kb(plans, backend_bot["id"])
        await message.answer(f"Вы выбрали бота <b>{backend_bot['username']}</b>. Выберите тариф:", reply_markup=kb)
        return

    # ✅ Если аргументов нет — показываем список всех ботов
    bots = await get_all_bots_from_backend()
    if not bots:
        await message.answer("❌ Нет доступных ботов для покупки подписки.")
        return

    kb = bots_to_kb(bots)
    await message.answer("👋 Привет! Выберите, в каком боте хотите купить подписку:", reply_markup=kb)


@dp.callback_query(F.data.startswith("select_bot:"))
async def select_bot_callback(callback: types.CallbackQuery):
    botusername = callback.data.split(":", 1)[1]
    backend_bot = await get_bot_by_username_from_backend(botusername)
    if not backend_bot:
        await callback.message.edit_text("❌ Ошибка: бот не найден.")
        await callback.answer()
        return

    plans = await get_plans_for_bot(backend_bot["id"])
    if not plans:
        await callback.message.edit_text("❌ Для этого бота пока нет активных тарифов.")
        await callback.answer()
        return

    kb = plans_to_kb(plans, backend_bot["id"])
    await callback.message.edit_text(f"Вы выбрали бота <b>{backend_bot['username']}</b>. Выберите тариф:", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "cancel")
async def cancel_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Операция отменена.")
    await callback.answer()
    await state.clear()


@dp.callback_query(F.data.startswith("buy:"))
async def handle_buy(callback: types.CallbackQuery, state: FSMContext):
    try:
        _, bot_id_str, plan_id_str = callback.data.split(":")
        bot_id, plan_id = int(bot_id_str), int(plan_id_str)
    except Exception:
        await callback.answer("Ошибка в данных кнопки", show_alert=True)
        return

    plans = await get_plans_for_bot(bot_id)
    plan = next((p for p in plans if p["id"] == plan_id), None)
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    text = (
        f"Вы выбрали: <b>{plan['name']}</b>\n"
        f"💰 Цена: <b>{plan['price']}</b>\n\n"
        "Для теста нажмите кнопку ниже — это имитация оплаты."
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить (тест)", callback_data=f"do_payment:{bot_id}:{plan_id}")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("do_payment:"))
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

        # уведомление в админ-канал
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
                )
        except Exception as e:
            logger.exception("Failed to send admin notification: %s", e)

    else:
        await callback.message.edit_text("❗ Платёж не удался или в статусе pending.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
