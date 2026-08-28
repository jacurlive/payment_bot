import logging

from .utils import send_notification_to_group_sync

logger = logging.getLogger(__name__)

# (отображаемое название, единица измерения суммы) для каждого метода оплаты.
# Чтобы добавить новый способ оплаты — достаточно добавить сюда запись,
# формат уведомления менять не нужно.
PAYMENT_METHOD_DISPLAY = {
    "payme": ("PayMe", "UZS"),
    "click": ("Click", "UZS"),
    "crypto": ("CryptoBot", "USDT"),
    "stars": ("Telegram Stars", "Stars"),
    "russian_card": ("Russian Card", "RUB"),
    "platega_card": ("Platega Card", "RUB"),
    "platega_sbp": ("Platega SBP", "RUB"),
    "Stub": ("Stub", ""),
}

ADMIN_METHOD_LABEL = "Админ"


def notify_new_subscription(subscription, payment=None):
    """
    Отправляет в группу бота (Bot.notification_group_id) уведомление о новой
    подписке. Единственная точка входа для этого уведомления — вызывается
    явно там, где подписка реально создаётся (mock-оплата, вебхук Platega,
    прямое создание через /api/subscriptions/), а не через Django-сигналы,
    чтобы не зависеть от порядка создания Subscription/Payment.

    Если подписка создана без реального платежа (например, вручную с фронта),
    payment не передаётся — в уведомлении используются значения по умолчанию.
    """
    bot = subscription.bot
    if not bot.notification_group_id:
        logger.info(f"У бота {bot.username} не указана группа для уведомлений")
        return

    if payment is not None:
        method_name, unit = PAYMENT_METHOD_DISPLAY.get(payment.method, (payment.method, ""))
        amount = f"{payment.amount} {unit}".strip()
        transaction_id = payment.transaction_id or ""
    else:
        method_name = ADMIN_METHOD_LABEL
        amount = "0"
        transaction_id = ""

    plan_name = subscription.plan.name if subscription.plan else "Неизвестный план"
    username = bot.username.lstrip("@")

    message = (
        "🎉 <b>Новая подписка!</b>\n\n"
        f"├ Пользователь: <code>{subscription.user.telegram_id}</code>\n"
        f"├ Подписка: {plan_name}\n"
        f"├ Сумма: {amount}\n"
        f"├ Метод: {method_name}\n"
        f"└ ID транзакции: <code>{transaction_id}</code>\n\n"
        f"🤖 Бот: @{username}"
    )

    result = send_notification_to_group_sync(
        group_id=bot.notification_group_id,
        message_text=message
    )

    if result["success"]:
        logger.info(f"✅ Уведомление о подписке отправлено в группу {bot.notification_group_id}")
    else:
        logger.error(f"❌ Не удалось отправить уведомление о подписке: {result['message']}")
