import asyncio
import logging
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from .config import bot
from .handlers import start, payments, common, buy

logging.basicConfig(level=logging.INFO)
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(start.router)
dp.include_router(buy.router)
dp.include_router(payments.router)
dp.include_router(common.router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
