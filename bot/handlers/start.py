from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from ..core.utils import get_all_bots, get_bot_by_username, get_plans_for_bot
from ..keyboards.bots import bots_keyboard
from ..keyboards.plans import plans_keyboard

router = Router()

@router.message(Command("start"))
async def start_handler(message: types.Message, command: CommandObject):
    args = command.args
    if args:
        bot_username = args.strip().lstrip("@")
        backend_bot = await get_bot_by_username(bot_username)
        if not backend_bot:
            await message.answer("❌ Бот не найден.")
            return

        plans = await get_plans_for_bot(backend_bot["id"])
        if not plans:
            await message.answer("Нет активных тарифов.")
            return

        await message.answer(
            f"Вы выбрали бота <b>{backend_bot['username']}</b>. Выберите тариф:",
            reply_markup=plans_keyboard(plans, backend_bot["id"]),
            parse_mode="html"
        )
        return

    bots = await get_all_bots()
    if not bots:
        await message.answer("Нет доступных ботов.")
        return

    await message.answer(
        "👋 Привет! Выберите, в каком боте хотите купить подписку:",
        reply_markup=bots_keyboard(bots)
    )


@router.callback_query(F.data.startswith("select_bot:"))
async def select_bot_callback(callback: types.CallbackQuery):
    bot_username = callback.data.split(":", 1)[1]
    backend_bot = await get_bot_by_username(bot_username)
    if not backend_bot:
        await callback.message.edit_text("❌ Ошибка: бот не найден.")
        await callback.answer()
        return

    plans = await get_plans_for_bot(backend_bot["id"])
    if not plans:
        await callback.message.edit_text("❌ Для этого бота нет тарифов.")
        await callback.answer()
        return

    await callback.message.edit_text(
        f"Вы выбрали бота <b>{backend_bot['username']}</b>. Выберите тариф:",
        reply_markup=plans_keyboard(plans, backend_bot["id"]),
        parse_mode="html"
    )
    await callback.answer()


