from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from payment.models import Subscription, Messages
from payment.utils import send_telegram_message_http, format_message


class Command(BaseCommand):
    help = 'Проверяет подписки и отправляет уведомления за 3, 2 и 1 день до окончания'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Тестовый режим - показывает кому будут отправлены сообщения, но не отправляет их'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write(self.style.WARNING('\n🔍 Проверка подписок на истечение...\n'))

        now = timezone.now()

        try:
            message_template = Messages.objects.get(identifier='subscription_expiring')
        except Messages.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ Ошибка: Сообщение "subscription_expiring" не найдено в базе данных'))
            self.stdout.write(
                self.style.WARNING('Создайте запись в таблице Messages с identifier="subscription_expiring"\n'))
            return

        active_subscriptions = Subscription.objects.filter(
            is_active=True,
            end_date__isnull=False,
            end_date__gt=now
        ).select_related('user', 'bot', 'plan')

        total_checked = 0
        total_sent = 0
        total_errors = 0

        for subscription in active_subscriptions:
            days_left = (subscription.end_date - now).days

            should_send = False
            notification_type = None

            if days_left == 3 and not subscription.expiring_3days_sent:
                should_send = True
                notification_type = '3 дня'
                flag_field = 'expiring_3days_sent'
            elif days_left == 2 and not subscription.expiring_2days_sent:
                should_send = True
                notification_type = '2 дня'
                flag_field = 'expiring_2days_sent'
            elif days_left == 1 and not subscription.expiring_1day_sent:
                should_send = True
                notification_type = '1 день'
                flag_field = 'expiring_1day_sent'

            if not should_send:
                continue

            total_checked += 1

            user = subscription.user
            bot = subscription.bot
            plan = subscription.plan

            language = user.language
            message_field = f'message_{language}'
            message_text = getattr(message_template, message_field, None)

            if not message_text:
                message_text = message_template.message_ru
                if not message_text:
                    self.stdout.write(self.style.ERROR(f'❌ Нет текста сообщения для пользователя {user.telegram_id}'))
                    total_errors += 1
                    continue

            formatted_message = format_message(message_text, subscription.end_date)

            plan_name = plan.name if plan else "Неизвестный план"
            end_date_str = subscription.end_date.strftime("%d.%m.%Y %H:%M")

            self.stdout.write(f'\n👤 Пользователь: {user.telegram_id} (@без username)')
            self.stdout.write(f'   📦 План: {plan_name}')
            self.stdout.write(f'   ⏰ Истекает: {end_date_str}')
            self.stdout.write(f'   ⚠️  Осталось: {notification_type}')
            self.stdout.write(f'   🌐 Язык: {language.upper()}')
            self.stdout.write(f'   🤖 Бот: @{bot.username}')

            if dry_run:
                self.stdout.write(self.style.WARNING('   🧪 [DRY RUN] Сообщение НЕ отправлено'))
                self.stdout.write(f'   📝 Текст: {formatted_message[:80]}...')
                total_sent += 1
            else:
                if not bot.bot_token:
                    self.stdout.write(self.style.ERROR(f'   ❌ У бота @{bot.username} не указан токен'))
                    total_errors += 1
                    continue

                result = send_telegram_message_http(
                    bot_token=bot.bot_token,
                    chat_id=user.telegram_id,
                    text=formatted_message
                )

                if result['success']:
                    self.stdout.write(self.style.SUCCESS(f'   ✅ {result["message"]}'))

                    setattr(subscription, flag_field, True)
                    subscription.save(update_fields=[flag_field])

                    total_sent += 1
                else:
                    self.stdout.write(self.style.ERROR(f'   ❌ {result["message"]}'))
                    total_errors += 1

        self.stdout.write(self.style.SUCCESS(f'\n{"=" * 60}'))
        self.stdout.write(self.style.SUCCESS(f'📊 ИТОГО:'))
        self.stdout.write(self.style.SUCCESS(f'   Проверено подписок: {total_checked}'))
        self.stdout.write(self.style.SUCCESS(f'   Отправлено уведомлений: {total_sent}'))

        if total_errors > 0:
            self.stdout.write(self.style.ERROR(f'   Ошибок: {total_errors}'))

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n⚠️  Это был тестовый запуск. Сообщения НЕ были отправлены.'))
            self.stdout.write(self.style.WARNING(f'Для реальной отправки запустите без флага --dry-run\n'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✅ Обработка завершена!\n'))
