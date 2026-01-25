import asyncio
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict
from asgiref.sync import async_to_sync
import os

logger = logging.getLogger(__name__)


def send_telegram_message_http(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()

        if data.get("ok"):
            return {
                "success": True,
                "message": f"✅ Сообщение отправлено пользователю {chat_id}"
            }
        else:
            error_description = data.get("description", "Unknown error")

            if "chat not found" in error_description.lower():
                return {
                    "success": False,
                    "message": f"❌ Пользователь {chat_id} не найден (не запускал бота)"
                }
            elif "bot was blocked" in error_description.lower():
                return {
                    "success": False,
                    "message": f"❌ Пользователь {chat_id} заблокировал бота"
                }
            else:
                return {
                    "success": False,
                    "message": f"❌ Ошибка API: {error_description}"
                }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": "❌ Превышено время ожидания ответа от Telegram"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"❌ Ошибка сети: {str(e)}"
        }
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при отправке сообщения: {e}")
        return {
            "success": False,
            "message": f"❌ Неожиданная ошибка: {str(e)}"
        }

def get_bot_token():
    try:
        from bot.config import BOT_TOKEN
        return BOT_TOKEN
    except ImportError:
        from dotenv import load_dotenv
        load_dotenv()
        return os.getenv("BOT_TOKEN")


async def _send_message_async(user_id: int, message_text: str) -> Dict[str, any]:
    from aiogram import Bot

    token = get_bot_token()
    if not token:
        return {
            "success": False,
            "message": "❌ Токен бота не найден"
        }

    # Создаём НОВЫЙ экземпляр бота (не используем глобальный)
    bot = Bot(token=token)

    try:
        await bot.send_message(chat_id=user_id, text=message_text)
        return {
            "success": True,
            "message": f"✅ Сообщение успешно отправлено пользователю {user_id}"
        }
    except Exception as e:
        error_message = str(e)

        if "chat not found" in error_message.lower():
            return {
                "success": False,
                "message": f"❌ Пользователь {user_id} не найден. Убедитесь, что он запустил бота (/start)"
            }
        elif "bot was blocked" in error_message.lower():
            return {
                "success": False,
                "message": f"❌ Пользователь {user_id} заблокировал бота"
            }
        elif "user is deactivated" in error_message.lower():
            return {
                "success": False,
                "message": f"❌ Аккаунт пользователя {user_id} деактивирован"
            }
        else:
            return {
                "success": False,
                "message": f"❌ Ошибка отправки: {error_message}"
            }
    finally:
        # ВАЖНО: закрываем сессию бота
        await bot.session.close()


def send_test_message_sync(user_id: int, message_text: str) -> Dict[str, any]:
    """
    Синхронная обёртка для отправки сообщения через Telegram

    Args:
        user_id: Telegram ID пользователя
        message_text: Текст сообщения

    Returns:
        dict: {"success": True/False, "message": "..."}
    """
    try:
        # Используем asyncio.run для создания нового event loop
        if hasattr(asyncio, '_nest_patched'):
            # Если nest_asyncio применён
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(_send_message_async(user_id, message_text))
        else:
            # Стандартный способ
            return asyncio.run(_send_message_async(user_id, message_text))
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            # Если loop закрыт, создаём новый
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_send_message_async(user_id, message_text))
            finally:
                loop.close()
        else:
            return {
                "success": False,
                "message": f"❌ Ошибка event loop: {str(e)}"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Критическая ошибка: {str(e)}"
        }


def format_message(template: str, end_date=None) -> str:
    """
    Форматирование сообщения с подстановкой переменных

    Args:
        template: Шаблон сообщения с {end_date}
        end_date: Дата окончания (если None, используется тестовая дата через 3 дня)

    Returns:
        str: Отформатированное сообщение
    """
    if not template:
        return ""

    if end_date is None:
        end_date = datetime.now() + timedelta(days=3)

    formatted_date = end_date.strftime("%d.%m.%Y")
    return template.replace("{end_date}", formatted_date)


async def _send_notification_to_group_async(group_id: int, message_text: str) -> Dict[str, any]:
    """
    Асинхронная функция для отправки уведомления в группу
    """
    from aiogram import Bot

    token = get_bot_token()
    if not token:
        return {
            "success": False,
            "message": "❌ Токен бота не найден"
        }

    bot = Bot(token=token)

    try:
        await bot.send_message(chat_id=group_id, text=message_text, parse_mode="HTML")
        return {
            "success": True,
            "message": f"✅ Уведомление отправлено в группу {group_id}"
        }
    except Exception as e:
        error_message = str(e)
        return {
            "success": False,
            "message": f"❌ Ошибка отправки в группу: {error_message}"
        }
    finally:
        await bot.session.close()


def send_notification_to_group_sync(group_id: int, message_text: str) -> Dict[str, any]:
    return async_to_sync(_send_notification_to_group_async)(
        group_id,
        message_text
    )
