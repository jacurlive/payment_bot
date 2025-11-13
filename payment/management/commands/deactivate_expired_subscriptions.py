from django.core.management.base import BaseCommand
from django.utils import timezone
from payment.models import Subscription

class Command(BaseCommand):
    help = "Деактивирует подписки, срок которых истёк"

    def handle(self, *args, **options):
        now = timezone.now()
        expired = Subscription.objects.filter(is_active=True, end_date__lt=now)
        count = expired.update(is_active=False)
        self.stdout.write(self.style.SUCCESS(f"✅ Деактивировано {count} подписок"))
