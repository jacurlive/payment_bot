from aiogram import types, F, Router
from ..core.utils import get_bots_with_plans, get_user_language
from ..core.localization import get_localized_message
from ..keyboards.bots import bots_keyboard
import logging


router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "cancel")
async def handle_cancel(callback: types.CallbackQuery):
    """Возврат на главный экран выбора бота"""
    bots = await get_bots_with_plans()
    user_id = callback.from_user.id
    language = await get_user_language(user_id)

    if not bots:
        await callback.message.edit_text("❌ Нет доступных ботов для покупки.")
        await callback.answer()
        return

    localized_message = await get_localized_message(language, 'which_bot')
    await callback.message.edit_text(
        localized_message,
        reply_markup=bots_keyboard(bots),
        parse_mode="html"
    )
    await callback.answer()
