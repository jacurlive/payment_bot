import requests
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BOT_SERVER_IP = os.getenv('BOT_SERVER_IP')


def add_subscription_to_bot(bot, user_id):
    """
    Добавление подписки на стороне бота

    Args:
        bot: объект Bot из БД
        user_id: Telegram ID пользователя

    Returns:
        dict: {"success": True/False, "message": "...", "active": True/False}
    """
    if not bot.request_port:
        logger.error(f"У бота {bot.username} не указан request_port")
        return {
            "success": False,
            "message": "❌ У бота не указан порт для запросов"
        }

    url = f"http://{BOT_SERVER_IP}:{bot.request_port}/v1/add_paid_subscription"
    params = {"chat_id": user_id}

    try:
        response = requests.post(url, params=params, timeout=10)
        data = response.json()

        if data.get("ok"):
            active_status = data.get("active", True)
            logger.info(
                f"✅ Подписка добавлена для пользователя {user_id} в боте {bot.username} (active={active_status})")
            return {
                "success": True,
                "message": f"✅ Подписка добавлена (active={active_status})",
                "active": active_status
            }
        else:
            logger.error(f"❌ Не удалось добавить подписку: {data}")
            return {
                "success": False,
                "message": "❌ Бот вернул ok=false"
            }

    except requests.exceptions.Timeout:
        logger.error(f"❌ Таймаут при запросе к боту {bot.username}")
        return {
            "success": False,
            "message": "❌ Превышено время ожидания ответа от бота"
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Ошибка запроса к боту {bot.username}: {e}")
        return {
            "success": False,
            "message": f"❌ Ошибка запроса: {str(e)}"
        }
    except Exception as e:
        logger.exception(f"❌ Неожиданная ошибка при добавлении подписки: {e}")
        return {
            "success": False,
            "message": f"❌ Неожиданная ошибка: {str(e)}"
        }


def delete_subscription_from_bot(bot, user_id):
    """
    Удаление подписки на стороне бота

    Args:
        bot: объект Bot из БД
        user_id: Telegram ID пользователя

    Returns:
        dict: {"success": True/False, "message": "..."}
    """
    if not bot.request_port:
        logger.error(f"У бота {bot.username} не указан request_port")
        return {
            "success": False,
            "message": "❌ У бота не указан порт для запросов"
        }

    url = f"http://{BOT_SERVER_IP}:{bot.request_port}/v1/delete_paid_subscription"
    params = {"chat_id": user_id}

    try:
        response = requests.post(url, params=params, timeout=10)
        data = response.json()

        if data.get("ok"):
            logger.info(f"✅ Подписка удалена для пользователя {user_id} в боте {bot.username}")
            return {
                "success": True,
                "message": "✅ Подписка удалена"
            }
        else:
            logger.error(f"❌ Не удалось удалить подписку: {data}")
            return {
                "success": False,
                "message": "❌ Бот вернул ok=false"
            }

    except requests.exceptions.Timeout:
        logger.error(f"❌ Таймаут при запросе к боту {bot.username}")
        return {
            "success": False,
            "message": "❌ Превышено время ожидания ответа от бота"
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Ошибка запроса к боту {bot.username}: {e}")
        return {
            "success": False,
            "message": f"❌ Ошибка запроса: {str(e)}"
        }
    except Exception as e:
        logger.exception(f"❌ Неожиданная ошибка при удалении подписки: {e}")
        return {
            "success": False,
            "message": f"❌ Неожиданная ошибка: {str(e)}"
        }


def check_subscription_on_bot(bot, user_id):
    """
    Проверка подписки на стороне бота (опционально)

    Args:
        bot: объект Bot из БД
        user_id: Telegram ID пользователя

    Returns:
        dict: {"success": True/False, "subscribed": True/False, "message": "..."}
    """
    if not bot.request_port:
        logger.error(f"У бота {bot.username} не указан request_port")
        return {
            "success": False,
            "message": "❌ У бота не указан порт для запросов",
            "subscribed": False
        }

    url = f"http://{BOT_SERVER_IP}:{bot.request_port}/v1/get_paid_subscription"
    params = {"chat_id": user_id}

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        subscribed = data.get("ok", False)

        logger.info(f"Проверка подписки для {user_id} в боте {bot.username}: {subscribed}")
        return {
            "success": True,
            "subscribed": subscribed,
            "message": f"✅ Подписка {'активна' if subscribed else 'не активна'}"
        }

    except requests.exceptions.Timeout:
        logger.error(f"❌ Таймаут при запросе к боту {bot.username}")
        return {
            "success": False,
            "message": "❌ Превышено время ожидания ответа от бота",
            "subscribed": False
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Ошибка запроса к боту {bot.username}: {e}")
        return {
            "success": False,
            "message": f"❌ Ошибка запроса: {str(e)}",
            "subscribed": False
        }
    except Exception as e:
        logger.exception(f"❌ Неожиданная ошибка при проверке подписки: {e}")
        return {
            "success": False,
            "message": f"❌ Неожиданная ошибка: {str(e)}",
            "subscribed": False
        }