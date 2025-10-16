from aiogram import types, F, Router
from ..core.utils import get_all_bots
from ..keyboards.bots import bots_keyboard
import logging


router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "cancel")
async def handle_cancel(callback: types.CallbackQuery):
    """Возврат на главный экран выбора бота"""
    bots = await get_all_bots()

    if not bots:
        await callback.message.edit_text("❌ Нет доступных ботов для покупки.")
        await callback.answer()
        return

    text = "👋 Привет! Выберите бота, в котором хотите купить подписку:"
    await callback.message.edit_text(
        text,
        reply_markup=bots_keyboard(bots),
        parse_mode="html"
    )
    await callback.answer()
