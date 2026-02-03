from django.core.management.base import BaseCommand
from django.utils import timezone
from payment.models import Subscription


class Command(BaseCommand):
    help = "Деактивирует подписки, срок которых истёк"

    def handle(self, *args, **options):
        now = timezone.now()
        expired = Subscription.objects.filter(is_active=True, end_date__lt=now)

        count = 0
        for subscription in expired:
            subscription.is_active = False
            subscription.save()
            count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Деактивировано {count} подписок"))
