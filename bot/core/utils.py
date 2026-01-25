import aiohttp
import logging

from .client import request
from .notifications import send_purchase_notification

logger = logging.getLogger(__name__)

async def get_all_bots():
    resp = await request("GET", "/api/bots/")
    return resp.json() if resp.status_code == 200 else []

async def get_user_language(telegram_id):
    resp = await request("GET", f"/api/users/{telegram_id}/")
    if resp.status_code == 200:
        data = resp.json()
        language = data["language"]
        return language
    return None

async def get_bot_by_username(username):
    resp = await request("GET", "/api/bots/", params={"username": username})
    return resp.json()[0] if resp.status_code == 200 and resp.json() else []

async def get_plans_for_bot(bot_id):
    resp = await request("GET", f"/api/plans/", params={"bot_id": bot_id})
    return resp.json() if resp.status_code == 200 else []

async def get_payment_methods():
    resp = await request("GET", f"/api/methods/")
    return resp.json() if resp.status_code == 200 else []

async def create_mock_payment(telegram_id, bot_id, plan_id):
    payload = {"telegram_id": telegram_id, "bot_id": bot_id, "plan_id": plan_id, "method": "stub"}
    resp = await request("POST", "/api/payments/mock/", json=payload)
    return resp.json() if resp.status_code in (200, 201) else []

async def create_user(user_id, language):
    payload = {"telegram_id": user_id, "language": language, "is_active": True}
    resp = await request("POST", "/api/users/", json=payload)
    return resp.json() if resp.status_code in (200, 201) else []

async def update_user_language(telegram_id, language):
    payload = {"telegram_id": telegram_id, "language": language}
    resp = await request("PUT", f"/api/users/{telegram_id}/", json=payload)
    return resp.json() if resp.status_code in (200, 201) else None

async def change_language(telegram_id, language):
    payload = {"language": language}
    resp = await request("PATCH", f"/api/users/{telegram_id}", json=payload)
    return resp.json() if resp.status_code in (200, 201) else []

async def get_user_data(telegram_id):
    resp = await request("GET", f"/api/users/{telegram_id}")
    return resp.json() if resp.status_code == 200 else None


async def send_payment_notification(telegram_id, bot_id, plan_id, payment_method, amount, transaction_id=None):
    try:
        user_resp = await request("GET", f"/api/users/{telegram_id}/")
        bot_resp = await request("GET", f"/api/bots/{bot_id}/")
        plan_resp = await request("GET", f"/api/plans/{plan_id}/")

        if user_resp.status_code != 200 or bot_resp.status_code != 200 or plan_resp.status_code != 200:
            return

        user_data = user_resp.json()
        bot_data = bot_resp.json()
        plan_data = plan_resp.json()

        class FakeObject:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)

        user_obj = FakeObject(user_data)
        bot_obj = FakeObject(bot_data)
        plan_obj = FakeObject(plan_data)

        await send_purchase_notification(
            user=user_obj,
            bot_obj=bot_obj,
            plan=plan_obj,
            payment_method=payment_method,
            amount=amount,
            transaction_id=transaction_id
        )

    except Exception as e:
        logger.exception(f"Ошибка при отправке уведомления о покупке: {e}")

async def send_telegram_message_http(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.post(url, json=payload) as response:
                data = await response.json()

        if data.get("ok"):
            return {
                "success": True,
                "message": f"✅ Сообщение отправлено пользователю {chat_id}"
            }

        error_description = data.get("description", "").lower()

        if "chat not found" in error_description:
            return {
                "success": False,
                "message": f"❌ Пользователь {chat_id} не найден"
            }
        elif "bot was blocked" in error_description:
            return {
                "success": False,
                "message": f"❌ Пользователь {chat_id} заблокировал бота"
            }

        return {
            "success": False,
            "message": f"❌ Ошибка API: {data.get('description')}"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Ошибка: {str(e)}"
        }


async def send_purchase_message_to_user(user_id, bot_id, plan_id, language):
    try:
        bot_resp = await request("GET", f"/api/bots/{bot_id}/")
        if bot_resp.status_code != 200:
            logger.error(f"Не удалось получить данные бота {bot_id}: {bot_resp.status_code}")
            return

        bot_data = bot_resp.json()
        bot_token = bot_data.get("bot_token")

        if not bot_token:
            logger.error(f"У бота {bot_id} (@{bot_data.get('username')}) не указан токен")
            return

        plan_resp = await request("GET", f"/api/plans/{plan_id}/")
        if plan_resp.status_code != 200:
            logger.error(f"Не удалось получить данные плана {plan_id}: {plan_resp.status_code}")
            return

        plan_data = plan_resp.json()
        duration_days = plan_data.get('duration_days', 30)

        message_resp = await request("GET", "/api/messages/", params={"identifier": "subscription_purchased"})
        if message_resp.status_code != 200:
            logger.error(f"Не удалось получить сообщение 'subscription_purchased': {message_resp.status_code}")
            return

        messages_data = message_resp.json()
        if not messages_data or len(messages_data) == 0:
            logger.error("Сообщение 'subscription_purchased' не найдено в БД")
            return

        message_template = messages_data[0]

        message_field = f'message_{language}'
        message_text = message_template.get(message_field)

        if not message_text:
            message_text = message_template.get('message_ru')
            if not message_text:
                logger.error(f"Нет текста сообщения для языка {language}")
                return

        from datetime import datetime, timedelta
        end_date = datetime.now() + timedelta(days=duration_days)

        from payment.utils import format_message, send_telegram_message_http
        formatted_message = format_message(message_text, end_date)

        result = send_telegram_message_http(
            bot_token=bot_token,
            chat_id=user_id,
            text=formatted_message
        )

        if result['success']:
            logger.info(f"✅ Сообщение о покупке отправлено пользователю {user_id} от бота @{bot_data.get('username')}")
        else:
            logger.error(f"❌ Не удалось отправить сообщение пользователю {user_id}: {result['message']}")

    except Exception as e:
        logger.exception(f"Ошибка при отправке сообщения о покупке пользователю {user_id}: {e}")
