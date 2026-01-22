from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from payment.models import Subscription, Messages, User
from payment.utils import send_test_message_sync, format_message


class Command(BaseCommand):
    help = 'Проверяет подписки, которые истекают через 3 дня или меньше, и отправляет уведомления'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=3,
            help='Количество дней до истечения (по умолчанию: 3)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Тестовый режим - показывает кому будут отправлены сообщения, но не отправляет их'
        )

    def handle(self, *args, **options):
        days_threshold = options['days']
        dry_run = options['dry_run']

        self.stdout.write(
            self.style.WARNING(f'\n🔍 Проверка подписок, истекающих через {days_threshold} дней или меньше...\n'))

        now = timezone.now()

        end_range = now + timedelta(days=days_threshold)

        expiring_subscriptions = Subscription.objects.filter(
            is_active=True,
            end_date__isnull=False,
            end_date__gte=now,
            end_date__lte=end_range
        ).select_related('user', 'bot', 'plan')

        total_count = expiring_subscriptions.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('✅ Нет подписок, которые истекают в ближайшие дни\n'))
            return

        self.stdout.write(self.style.WARNING(f'📊 Найдено подписок: {total_count}\n'))

        try:
            message_template = Messages.objects.get(identifier='subscription_expiring')
        except Messages.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ Ошибка: Сообщение "subscription_expiring" не найдено в базе данных'))
            self.stdout.write(
                self.style.WARNING('Создайте запись в таблице Messages с identifier="subscription_expiring"\n'))
            return

        success_count = 0
        error_count = 0

        for subscription in expiring_subscriptions:
            user = subscription.user
            days_left = (subscription.end_date - now).days

            language = user.language

            message_field = f'message_{language}'
            message_text = getattr(message_template, message_field, None)

            if not message_text:
                message_text = message_template.message_ru
                if not message_text:
                    self.stdout.write(self.style.ERROR(f'❌ Нет текста сообщения для пользователя {user.telegram_id}'))
                    error_count += 1
                    continue

            formatted_message = format_message(message_text, subscription.end_date)

            plan_name = subscription.plan.name if subscription.plan else "Неизвестный план"
            end_date_str = subscription.end_date.strftime("%d.%m.%Y %H:%M")

            self.stdout.write(f'\n👤 Пользователь: {user.telegram_id} (@{user.username or "без username"})')
            self.stdout.write(f'   📦 План: {plan_name}')
            self.stdout.write(f'   ⏰ Истекает: {end_date_str} (через {days_left} дней)')
            self.stdout.write(f'   🌐 Язык: {language.upper()}')

            if dry_run:
                self.stdout.write(self.style.WARNING('   🧪 [DRY RUN] Сообщение НЕ отправлено'))
                self.stdout.write(f'   📝 Текст: {formatted_message[:80]}...')
                success_count += 1
            else:
                result = send_test_message_sync(user.telegram_id, formatted_message)

                if result['success']:
                    self.stdout.write(self.style.SUCCESS(f'   ✅ {result["message"]}'))
                    success_count += 1
                else:
                    self.stdout.write(self.style.ERROR(f'   ❌ {result["message"]}'))
                    error_count += 1

        self.stdout.write(self.style.SUCCESS(f'\n{"=" * 60}'))
        self.stdout.write(self.style.SUCCESS(f'📊 ИТОГО:'))
        self.stdout.write(self.style.SUCCESS(f'   Всего подписок: {total_count}'))
        self.stdout.write(self.style.SUCCESS(f'   Успешно: {success_count}'))

        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'   Ошибок: {error_count}'))

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n⚠️  Это был тестовый запуск. Сообщения НЕ были отправлены.'))
            self.stdout.write(self.style.WARNING(f'Для реальной отправки запустите без флага --dry-run\n'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✅ Обработка завершена!\n'))