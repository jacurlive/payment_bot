import requests
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BOT_SERVER_IP = os.getenv('BOT_SERVER_IP')


def _make_request(bot, endpoint, user_id):
    """
    Базовая функция для GET запросов к боту клиента

    Args:
        bot: объект Bot из БД
        endpoint: путь (add_paid_subscription / delete_paid_subscription / get_paid_subscription)
        user_id: Telegram ID пользователя

    Returns:
        dict: ответ от сервера бота
    """
    if not bot.request_port:
        return {"ok": False, "error": f"У бота {bot.username} не указан request_port"}

    url = f"http://{BOT_SERVER_IP}:{bot.request_port}/v1/{endpoint}"
    print(url, user_id)
    params = {"chat_id": user_id}

    try:
        response = requests.get(url, params=params, timeout=10)
        print(response.json())
        return response.json()
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "Превышено время ожидания"}
    except requests.exceptions.RequestException as e:
        return {"ok": False, "error": f"Ошибка запроса: {str(e)}"}
    except Exception as e:
        return {"ok": False, "error": f"Неожиданная ошибка: {str(e)}"}


def check_subscription(bot, user_id):
    """
    Проверка подписки на стороне бота
    GET http://IP:PORT/v1/get_paid_subscription?chat_id=123

    Returns:
        {"ok": true, "active": true/false}
        {"ok": false}
    """
    return _make_request(bot, "get_paid_subscription", user_id)


def add_subscription_to_bot(bot, user_id):
    """
    1. Делаем GET на add_paid_subscription
    2. Проверяем через get_paid_subscription что active=true

    Returns:
        {"success": True/False, "message": "...", "active": True/False}
    """
    logger.info(f"Добавление подписки для {user_id} в боте @{bot.username}")

    add_result = _make_request(bot, "add_paid_subscription", user_id)

    if not add_result.get("ok"):
        error = add_result.get("error", "Неизвестная ошибка")
        logger.error(f"❌ Не удалось добавить подписку для {user_id}: {error}")
        return {
            "success": False,
            "message": f"❌ Ошибка при добавлении подписки: {error}",
            "active": False
        }

    check_result = check_subscription(bot, user_id)

    if not check_result.get("ok"):
        error = check_result.get("error", "Неизвестная ошибка")
        logger.error(f"❌ Не удалось проверить подписку для {user_id}: {error}")
        return {
            "success": False,
            "message": f"❌ Подписка добавлена, но проверка не прошла: {error}",
            "active": False
        }

    active = check_result.get("active", False)

    if active:
        logger.info(f"✅ Подписка активна для {user_id} в боте @{bot.username}")
        return {
            "success": True,
            "message": f"✅ Подписка успешно добавлена и активна",
            "active": True
        }
    else:
        logger.error(f"❌ Подписка не активна для {user_id} после добавления")
        return {
            "success": False,
            "message": "❌ Подписка добавлена, но не активна",
            "active": False
        }


def delete_subscription_from_bot(bot, user_id):
    """
    1. Делаем GET на delete_paid_subscription
    2. Проверяем через get_paid_subscription что active=false

    Returns:
        {"success": True/False, "message": "..."}
    """
    logger.info(f"Удаление подписки для {user_id} в боте @{bot.username}")

    delete_result = _make_request(bot, "delete_paid_subscription", user_id)

    if not delete_result.get("ok"):
        error = delete_result.get("error", "Неизвестная ошибка")
        logger.error(f"❌ Не удалось удалить подписку для {user_id}: {error}")
        return {
            "success": False,
            "message": f"❌ Ошибка при удалении подписки: {error}"
        }

    check_result = check_subscription(bot, user_id)

    if not check_result.get("ok"):
        error = check_result.get("error", "Неизвестная ошибка")
        logger.error(f"❌ Не удалось проверить подписку для {user_id}: {error}")
        return {
            "success": False,
            "message": f"❌ Подписка удалена, но проверка не прошла: {error}"
        }

    active = check_result.get("active", True)

    if not active:
        logger.info(f"✅ Подписка удалена для {user_id} в боте @{bot.username}")
        return {
            "success": True,
            "message": "✅ Подписка успешно удалена"
        }
    else:
        logger.error(f"❌ Подписка всё ещё активна для {user_id} после удаления")
        return {
            "success": False,
            "message": "❌ Подписка удалена, но всё ещё активна"
        }
