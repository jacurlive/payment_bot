import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Subscription, Payment
from .bot_api import add_subscription_to_bot, delete_subscription_from_bot
from .utils import send_telegram_message_http


logger = logging.getLogger(__name__)


@receiver(post_save, sender=Subscription)
def subscription_changed(sender, instance, created, **kwargs):
    """
    Автоматически вызывается когда Subscription создаётся или обновляется.

    1. Синхронизирует состояние подписки с ботом клиента
    2. Отправляет уведомление в группу бота (только при создании)
    """
    try:
        if instance.is_active:
            logger.info(f"[Signal] Активация подписки для {instance.user.telegram_id} в боте @{instance.bot.username}")
            result = add_subscription_to_bot(instance.bot, instance.user.telegram_id)

            if not result['success']:
                logger.error(f"[Signal] Не удалось добавить подписку: {result['message']}")
            else:
                logger.info(f"[Signal] {result['message']}")
        else:
            logger.info(
                f"[Signal] Деактивация подписки для {instance.user.telegram_id} в боте @{instance.bot.username}")
            result = delete_subscription_from_bot(instance.bot, instance.user.telegram_id)

            if not result['success']:
                logger.error(f"[Signal] Не удалось удалить подписку: {result['message']}")
            else:
                logger.info(f"[Signal] {result['message']}")

        if created and instance.is_active:
            send_subscription_notification(instance)

    except Exception as e:
        logger.exception(f"[Signal] Ошибка при обработке подписки: {e}")


@receiver(post_delete, sender=Subscription)
def subscription_deleted(sender, instance, **kwargs):
    """
    Автоматически вызывается когда Subscription удаляется из БД.
    """
    try:
        logger.info(f"[Signal] Удаление подписки для {instance.user.telegram_id} в боте @{instance.bot.username}")
        result = delete_subscription_from_bot(instance.bot, instance.user.telegram_id)

        if not result['success']:
            logger.error(f"[Signal] Не удалось удалить подписку: {result['message']}")
        else:
            logger.info(f"[Signal] {result['message']}")

    except Exception as e:
        logger.exception(f"[Signal] Ошибка при удалении подписки: {e}")


@receiver(post_save, sender=Payment)
def payment_created(sender, instance, created, **kwargs):
    """
    Автоматически вызывается когда Payment создаётся.
    Отправляет уведомление в группу бота.
    """
    if created and instance.status == 'success':
        try:
            send_payment_notification(instance)
            print(instance)
        except Exception as e:
            logger.exception(f"[Signal] Ошибка при отправке уведомления о платеже: {e}")


def get_global_bot_token():
    """
    Получение токена глобального платёжного бота из .env
    """
    import os
    from dotenv import load_dotenv
    load_dotenv()
    return os.getenv("BOT_TOKEN")


def send_subscription_notification(subscription):
    """
    Отправка уведомления о новой подписке в группу бота
    Отправляется от имени глобального платёжного бота

    Args:
        subscription: объект Subscription
    """
    bot = subscription.bot
    user = subscription.user
    bot_plan = subscription.plan

    if not bot.notification_group_id:
        logger.info(f"У бота {bot.username} не указана группа для уведомлений")
        return

    global_bot_token = get_global_bot_token()
    if not global_bot_token:
        logger.error("Токен глобального бота не найден в .env")
        return

    plan_name = bot_plan.name if bot_plan else "Неизвестный план"
    duration = bot_plan.duration_days if bot_plan else "?"
    end_date = subscription.end_date.strftime("%d.%m.%Y %H:%M") if subscription.end_date else "Бессрочно"

    message = f"""
🎉 <b>Новая подписка!</b>

👤 <b>Пользователь:</b>
├ ID: <code>{user.telegram_id}</code>

📦 <b>Подписка:</b>
├ План: <b>{plan_name}</b>
├ Длительность: {duration} дней
└ Истекает: {end_date}

🤖 <b>Бот:</b> @{bot.username}
    """.strip()

    result = send_telegram_message_http(
        bot_token=global_bot_token,
        chat_id=bot.notification_group_id,
        text=message
    )

    if result['success']:
        logger.info(f"✅ Уведомление о подписке отправлено в группу {bot.notification_group_id}")
    else:
        logger.error(f"❌ Не удалось отправить уведомление о подписке: {result['message']}")


def send_payment_notification(payment):
    """
    Отправка уведомления о платеже в группу бота
    Отправляется от имени глобального платёжного бота

    Args:
        payment: объект Payment
    """
    bot = payment.bot
    user = payment.user

    if not bot.notification_group_id:
        logger.info(f"У бота {bot.username} не указана группа для уведомлений")
        return

    global_bot_token = get_global_bot_token()
    if not global_bot_token:
        logger.error("Токен глобального бота не найден в .env")
        return

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

    method_name = payment_methods_display.get(payment.method, payment.method)

    message = f"""
💰 <b>Новый платёж!</b>

👤 <b>Пользователь:</b>
├ ID: <code>{user.telegram_id}</code>

💳 <b>Платёж:</b>
├ Сумма: <b>{payment.amount}</b>
├ Метод: <b>{method_name}</b>
├ Статус: <b>{"✅ Успешно" if payment.status == "success" else payment.status}</b>
└ ID транзакции: <code>{payment.transaction_id or 'N/A'}</code>

🤖 <b>Бот:</b> @{bot.username}
    """.strip()

    result = send_telegram_message_http(
        bot_token=global_bot_token,
        chat_id=bot.notification_group_id,
        text=message
    )

    if result['success']:
        logger.info(f"✅ Уведомление о платеже отправлено в группу {bot.notification_group_id}")
    else:
        logger.error(f"❌ Не удалось отправить уведомление о платеже: {result['message']}")
