import os
import logging
import aiohttp
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

PLATEGA_BASE_URL = os.getenv("PLATEGA_BASE_URL", "https://app.platega.io").rstrip("/")
PLATEGA_MERCHANT_ID = os.getenv("PLATEGA_MERCHANT_ID")
PLATEGA_SECRET = os.getenv("PLATEGA_SECRET")
PLATEGA_RETURN_URL = os.getenv("PLATEGA_RETURN_URL", "https://t.me")
PLATEGA_FAILED_URL = os.getenv("PLATEGA_FAILED_URL", "https://t.me")

PLATEGA_METHOD_SBP = 2
PLATEGA_METHOD_CARD = 11


def _headers():
    return {
        "X-MerchantId": PLATEGA_MERCHANT_ID,
        "X-Secret": PLATEGA_SECRET,
    }


async def create_platega_transaction(payment_method: int, amount, description: str, payload: str):
    """
    Создание платежа через Platega (карта/СБП)
    """
    body = {
        "paymentMethod": payment_method,
        "paymentDetails": {
            "amount": float(amount),
            "currency": "RUB"
        },
        "description": description,
        "return": PLATEGA_RETURN_URL,
        "failedUrl": PLATEGA_FAILED_URL,
        "payload": payload,
    }

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            async with session.post(
                f"{PLATEGA_BASE_URL}/transaction/process",
                json=body,
                headers=_headers()
            ) as response:
                data = await response.json()

                if response.status not in (200, 201):
                    logger.error(f"Platega: ошибка создания платежа: {response.status} {data}")
                    return None

                return data
    except Exception as e:
        logger.exception(f"Platega: исключение при создании платежа: {e}")
        return None


async def check_platega_transaction(transaction_id: str):
    """
    Проверка статуса платежа Platega
    """
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            async with session.get(
                f"{PLATEGA_BASE_URL}/transaction/{transaction_id}",
                headers=_headers()
            ) as response:
                if response.status != 200:
                    logger.error(f"Platega: ошибка проверки транзакции {transaction_id}: {response.status}")
                    return None

                return await response.json()
    except Exception as e:
        logger.exception(f"Platega: исключение при проверке транзакции {transaction_id}: {e}")
        return None
