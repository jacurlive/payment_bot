import logging
from .client import request

logger = logging.getLogger(__name__)

FALLBACK_TRANSLATIONS = {
    'none': {
        "welcome": "Assalomu alaykum! Xush kelibsiz. Iltimos, tilni tanlang. 🇺🇿\n\nЗдравствуйте! Добро пожаловать. Пожалуйста, выберите язык. 🇷🇺\n\nHello! Welcome. Please select a language. 🇺🇸",
    },
    'ru': {
        "not_found": "❌ Сообщение не найдено",
    },
    'en': {
        "not_found": "❌ Message not found",
    },
    'uz': {
        "not_found": "❌ Xabar topilmadi",
    }
}


async def get_localized_message(language: str, key: str) -> str:
    """
    Получение локализованного сообщения из API

    Args:
        language: код языка (ru/en/uz/none)
        key: идентификатор сообщения (identifier в таблице Messages)

    Returns:
        str: локализованное сообщение
    """
    try:
        if language == 'none':
            return FALLBACK_TRANSLATIONS['none'].get(key, key)

        response = await request("GET", "/api/messages/", params={"identifier": key})

        if response.status_code != 200:
            logger.warning(f"Не удалось получить сообщение '{key}' из API: {response.status_code}")
            return get_fallback_message(language, key)

        messages_data = response.json()

        if not messages_data or len(messages_data) == 0:
            logger.warning(f"Сообщение с identifier '{key}' не найдено в БД")
            return get_fallback_message(language, key)

        message = messages_data[0]  # Берём первый результат

        message_field = f'message_{language}'
        message_text = message.get(message_field)

        if not message_text:
            message_text = message.get('message_ru')

        if not message_text:
            message_text = (
                    message.get('message_en') or
                    message.get('message_uz') or
                    key
            )

        return message_text

    except Exception as e:
        logger.exception(f"Ошибка при получении локализованного сообщения '{key}': {e}")
        return get_fallback_message(language, key)


def get_fallback_message(language: str, key: str) -> str:
    """
    Получение fallback сообщения если API недоступен

    Args:
        language: код языка
        key: ключ сообщения

    Returns:
        str: fallback сообщение или сам ключ
    """
    fallback = FALLBACK_TRANSLATIONS.get(language, {}).get(key)
    if fallback:
        return fallback

    logger.warning(f"Fallback сообщение для '{key}' ({language}) не найдено")
    return key


class Localization:
    """
    Класс для обратной совместимости
    Теперь просто wrapper над новой асинхронной функцией
    """

    @staticmethod
    def get_translation(language, key):
        """
        Синхронная версия - использует fallback
        """
        logger.warning("Использование синхронного Localization.get_translation устарело")
        return get_fallback_message(language, key)


# class Localization:
#     translation = {
#         'none': {
#             "welcome":"Assalomu alaykum! Xush kelibsiz. Iltimos, tilni tanlang. 🇺🇿\n\nЗдравствуйте! Добро пожаловать. Пожалуйста, выберите язык. 🇷🇺\n\nHello! Welcome. Please select a language. 🇺🇸",
#         },
#
#         'ru': {
#             "choice_bot": "Вы выбрали бота",
#             "choice_plan": "Выберите тариф",
#             "not_bot": "❌ Бот не найден.",
#             "not_active_plan": "❌ Для этого бота нет тарифов.",
#             "not_available_bot": "Нет доступных ботов.",
#             "which_bot": "👋 Привет! Выберите, в каком боте хотите купить подписку:",
#             "button_data_error": "Ошибка данных кнопки",
#             "not_plan": "Тариф не найден",
#             "pay_crypto_bot": "💳 Оплатить через CryptoBot",
#             "back_btn": "🔙 Назад",
#             "payment_from": "Оплата через",
#             "plan": "Тариф",
#             "price": "Сумма",
#             "after_buy_text": "После оплаты бот активирует подписку автоматически ✅",
#             "crypto_invoice_error": "❌ Ошибка при создании платежа через CryptoBot.",
#             "not_paid": "❗ Оплата ещё не получена",
#             "paid": "✅ Оплата получена! Подписка активирована.",
#             "paid_but_not_activated": "⚠️ Оплата прошла, но не удалось активировать подписку.",
#             "stars_invoice_error": "❌ Не удалось создать счёт через Telegram Stars.",
#             "stars_payment_success": "✅ Оплата через Telegram Stars прошла успешно!",
#             "you_choice": "Вы выбрали",
#             "price_1": "💰 Цена",
#             "choice_payment_type": "Выберите способ оплаты",
#         },
#
#         'en': {
#             "choice_bot": "You have selected the bot",
#             "choice_plan": "Select a subscription plan",
#             "not_bot": "❌ Bot not found.",
#             "not_active_plan": "❌ There are no available plans for this bot.",
#             "not_available_bot": "No available bots.",
#             "which_bot": "👋 Hi! Choose which bot you want to purchase a subscription for:",
#             "button_data_error": "Button data error",
#             "not_plan": "Subscription plan not found",
#             "pay_crypto_bot": "💳 Pay via CryptoBot",
#             "back_btn": "🔙 Back",
#             "payment_from": "Payment via",
#             "plan": "Plan",
#             "price": "Amount",
#             "after_buy_text": "After payment, the bot will activate your subscription automatically ✅",
#             "crypto_invoice_error": "❌ Failed to create a CryptoBot invoice.",
#             "not_paid": "❗ Payment has not been received yet",
#             "paid": "✅ Payment received! Subscription activated.",
#             "paid_but_not_activated": "⚠️ Payment was successful, but the subscription could not be activated.",
#             "stars_invoice_error": "❌ Failed to create a Telegram Stars invoice.",
#             "stars_payment_success": "✅ Payment via Telegram Stars was successful!",
#             "you_choice": "You selected",
#             "price_1": "💰 Price",
#             "choice_payment_type": "Select a payment method",
#         },
#
#         'uz': {
#             "choice_bot": "Siz tanlagan bot",
#             "choice_plan": "Tarifni tanlang",
#             "not_bot": "❌ Bot topilmadi.",
#             "not_active_plan": "❌ Ushbu bot uchun tariflar mavjud emas.",
#             "not_available_bot": "Mavjud botlar yo‘q.",
#             "which_bot": "👋 Salom! Qaysi bot uchun obuna sotib olmoqchisiz:",
#             "button_data_error": "Tugma maʼlumotlarida xatolik",
#             "not_plan": "Tarif topilmadi",
#             "pay_crypto_bot": "💳 CryptoBot orqali to‘lash",
#             "back_btn": "🔙 Orqaga",
#             "payment_from": "To‘lov usuli",
#             "plan": "Tarif",
#             "price": "Summa",
#             "after_buy_text": "To‘lovdan so‘ng obuna avtomatik tarzda faollashtiriladi ✅",
#             "crypto_invoice_error": "❌ CryptoBot orqali hisob yaratishda xatolik yuz berdi.",
#             "not_paid": "❗ To‘lov hali qabul qilinmadi",
#             "paid": "✅ To‘lov qabul qilindi! Obuna faollashtirildi.",
#             "paid_but_not_activated": "⚠️ To‘lov muvaffaqiyatli, ammo obuna faollashtirilmadi.",
#             "stars_invoice_error": "❌ Telegram Stars orqali hisob yaratib bo‘lmadi.",
#             "stars_payment_success": "✅ Telegram Stars orqali to‘lov muvaffaqiyatli amalga oshirildi!",
#             "you_choice": "Siz tanladingiz",
#             "price_1": "💰 Narx",
#             "choice_payment_type": "To‘lov usulini tanlang",
#         }
#     }
#
#     @staticmethod
#     def get_translation(language, key):
#         return Localization.translation.get(language, {}).get(key, key)
#
#
# async def get_localized_message(language, key):
#     translation = Localization.get_translation(language, key)
#     return translation
