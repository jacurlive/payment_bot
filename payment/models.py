from django.db import models

class Bot(models.Model):
    username = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username


class SubscriptionPlan(models.Model):
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name="plan")
    name = models.CharField(max_length=64)
    duration_days = models.PositiveIntegerField(null=True, blank=True)

    price = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class User(models.Model):
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=64, blank=True, null=True)
    first_name = models.CharField(max_length=200, blank=True, null=True)
    last_name = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.telegram_id)

class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscription")
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)

    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.plan)


class Payment(models.Model):
    PAYMENTS_METHODS = (
        ("payme", "PayMe"),
        ("click", "Click"),
        ("crypto", "CryptoBot"),
        ("stars", "Telegram Stars"),
        ("russian_card", "Russian Card"),
        ("Stub", "Stub")
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name="payments")
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True)
    method = models.CharField(max_length=32, choices=PAYMENTS_METHODS)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=16, choices=(("pending", "Pending"),("success", "Success"),("failed", "Failed")))
    transaction_id = models.CharField(max_length=128, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
