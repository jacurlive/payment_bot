import os

from dotenv import load_dotenv
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
ADMIN_CHANNEL_ID = int(os.getenv("ADMIN_CHANNEL_ID", "0"))
BACKEND_USERNAME = os.getenv("BACKEND_USERNAME")
BACKEND_PASSWORD = os.getenv("BACKEND_PASSWORD")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing in .env")
