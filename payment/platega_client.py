import os
import logging
import requests

logger = logging.getLogger(__name__)

PLATEGA_BASE_URL = os.getenv("PLATEGA_BASE_URL", "https://app.platega.io").rstrip("/")
PLATEGA_MERCHANT_ID = os.getenv("PLATEGA_MERCHANT_ID")
PLATEGA_SECRET = os.getenv("PLATEGA_SECRET")


def get_platega_transaction(transaction_id):
    """
    Получение данных транзакции Platega по её ID (используется вебхуком
    для получения payload, т.к. сам callback его не передаёт)
    """
    headers = {
        "X-MerchantId": PLATEGA_MERCHANT_ID,
        "X-Secret": PLATEGA_SECRET,
    }

    try:
        response = requests.get(
            f"{PLATEGA_BASE_URL}/transaction/{transaction_id}",
            headers=headers,
            timeout=15
        )

        if response.status_code != 200:
            logger.error(f"Platega: не удалось получить транзакцию {transaction_id}: {response.status_code}")
            return None

        return response.json()

    except requests.exceptions.RequestException as e:
        logger.exception(f"Platega: ошибка запроса транзакции {transaction_id}: {e}")
        return None
