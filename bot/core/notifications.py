import logging
from payment.utils import send_notification_to_group_sync, _send_notification_to_group_async

logger = logging.getLogger(__name__)


async def send_purchase_notification(user, bot_obj, plan, payment_method, amount, transaction_id=None):
    """
    Отправка уведомления о покупке в группу бота

    Args:
        user: объект User из базы данных
        bot_obj: объект Bot из базы данных
        plan: объект SubscriptionPlan
        payment_method: метод оплаты (str)
        amount: сумма платежа
        transaction_id: ID транзакции (опционально)
    """
    # Проверяем что у бота указана группа для уведомлений
    if not bot_obj.notification_group_id:
        logger.info(f"У бота {bot_obj.username} не указана группа для уведомлений")
        return

    # Формируем красивое сообщение
    payment_methods_display = {
        "payme": "PayMe",
        "click": "Click",
        "crypto": "CryptoBot",
        "stars": "Telegram Stars",
        "russian_card": "Russian Card",
        "platega_card": "Platega Card",
        "platega_sbp": "Platega SBP",
        "stub": "Stub"
    }

    method_name = payment_methods_display.get(payment_method, payment_method)

    message = f"""
🎉 <b>Новая покупка подписки!</b>

👤 <b>Пользователь:</b>
├ ID: <code>{user.telegram_id}</code>

📦 <b>Подписка:</b>
├ План: <b>{plan.name}</b>
└ Длительность: {plan.duration_days} дней

💰 <b>Платёж:</b>
├ Сумма: <b>{amount}</b>
├ Метод: <b>{method_name}</b>
└ ID транзакции: <code>{transaction_id or 'N/A'}</code>

🤖 <b>Бот:</b> @{bot_obj.username}
    """.strip()

    # Отправляем уведомление
    result = await _send_notification_to_group_async(
        group_id=bot_obj.notification_group_id,
        message_text=message
    )

    if result['success']:
        logger.info(f"✅ Уведомление отправлено в группу {bot_obj.notification_group_id} для бота {bot_obj.username}")
    else:
        logger.error(
            f"❌ Не удалось отправить уведомление в группу {bot_obj.notification_group_id}: {result['message']}")
