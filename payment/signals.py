import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Subscription
from .bot_api import add_subscription_to_bot, delete_subscription_from_bot


logger = logging.getLogger(__name__)


@receiver(post_save, sender=Subscription)
def subscription_changed(sender, instance, created, **kwargs):
    """
    Автоматически вызывается когда Subscription создаётся или обновляется.
    Синхронизирует состояние подписки с ботом клиента.

    Уведомление о новой подписке сюда не входит — оно отправляется явно
    через notify_new_subscription() там, где подписка реально создаётся
    (см. payment/notifications.py), чтобы не зависеть от порядка создания
    Subscription/Payment.
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
