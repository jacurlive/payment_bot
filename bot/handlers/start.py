from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject

from ..core.localization import get_localized_message
from ..core.utils import get_all_bots, get_bot_by_username, get_plans_for_bot, get_user_language, create_user, update_user_language
from ..keyboards.bots import bots_keyboard
from ..keyboards.language import language_selection_keyboard
from ..keyboards.plans import plans_keyboard
from ..keyboards.common import back_keyboard

router = Router()

@router.message(Command("start"))
async def start_handler(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    args = command.args

    language = await get_user_language(user_id)

    if not language:
        if args:
            language = "ru"
            await create_user(user_id, language)
        else:
            welcome_text = await get_localized_message("none", "welcome")
            await message.answer(
                welcome_text,
                reply_markup=language_selection_keyboard()
            )
            return

    if args:
        bot_username = args.strip().lstrip("@")
        backend_bot = await get_bot_by_username(bot_username)

        if not backend_bot:
            await message.answer(
                await get_localized_message(language, "not_bot")
            )
            return

        plans = await get_plans_for_bot(backend_bot["id"])
        if not plans:
            await message.answer(
                await get_localized_message(language, "not_active_plan")
            )
            return

        await message.answer(
            f"{await get_localized_message(language, 'choice_bot')} "
            f"<b>{backend_bot['username']}</b>. "
            f"{await get_localized_message(language, 'choice_plan')}",
            reply_markup=plans_keyboard(plans, backend_bot["id"]),
            parse_mode="html"
        )
        return

    bots = await get_all_bots()
    if not bots:
        await message.answer(
            await get_localized_message(language, "not_available_bot")
        )
        return

    await message.answer(
        await get_localized_message(language, "which_bot"),
        reply_markup=bots_keyboard(bots)
    )


@router.callback_query(F.data.startswith("lang:"))
async def select_language(callback: types.CallbackQuery):
    language = callback.data.split(":")[1]
    user_id = callback.from_user.id
    data = await get_user_language(user_id)
    if data:
        await update_user_language(user_id, language)
    await create_user(user_id, language)

    await callback.message.edit_text(
        await get_localized_message(language, "which_bot"),
        reply_markup=bots_keyboard(await get_all_bots())
    )
    await callback.answer()


@router.message(Command("language"))
async def language_handler(message: types.Message):
    await message.answer(
        "🌍 Выберите язык / Choose language / Tilni tanlang:",
        reply_markup=language_selection_keyboard()
    )


@router.callback_query(F.data.startswith("select_bot:"))
async def select_bot_callback(callback: types.CallbackQuery):
    bot_username = callback.data.split(":", 1)[1]
    backend_bot = await get_bot_by_username(bot_username)
    user_id = callback.from_user.id
    language = await get_user_language(user_id)
    if not backend_bot:
        localized_message = await get_localized_message(language, "not_bot")
        await callback.message.edit_text(localized_message, reply_markup=back_keyboard())
        await callback.answer()
        return

    plans = await get_plans_for_bot(backend_bot["id"])
    if not plans:
        localized_message = await get_localized_message(language, "not_active_plan")
        await callback.message.edit_text(localized_message, reply_markup=back_keyboard())
        await callback.answer()
        return

    localized_message_1 = await get_localized_message(language, "choice_bot")
    localized_message_2 = await get_localized_message(language, "choice_plan")
    await callback.message.edit_text(
        f"{localized_message_1} <b>{backend_bot['username']}</b>. {localized_message_2}:",
        reply_markup=plans_keyboard(plans, backend_bot["id"]),
        parse_mode="html"
    )
    await callback.answer()
