from django.db import models

class Bot(models.Model):
    username = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Бот"
        verbose_name_plural = "Боты"

    def __str__(self):
        return self.username


class SubscriptionPlan(models.Model):
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name="plan")
    name = models.CharField(max_length=64)
    duration_days = models.PositiveIntegerField(null=True, blank=True)

    price_usdt = models.DecimalField(max_digits=12, decimal_places=2)
    price_uzs = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_stars = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_rub = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "План подписки"
        verbose_name_plural = "Планы подписок"

    def __str__(self):
        return self.name


class Language(models.TextChoices):
    RU = "ru", "Русский"
    EN = "en", "English"
    UZ = "uz", "O'zbekcha"


class User(models.Model):
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=64, blank=True, null=True)
    first_name = models.CharField(max_length=200, blank=True, null=True)
    last_name = models.CharField(max_length=200, blank=True, null=True)
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.RU)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

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

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"

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

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"


class PaymentMethod(models.Model):
    name = models.CharField(max_length=100, unique=True)
    callback_data = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Способ оплаты"
        verbose_name_plural = "Способы оплаты"


class Messages(models.Model):
    identifier = models.CharField(max_length=255, unique=True)
    message_ru = models.TextField(null=True, blank=True)
    message_en = models.TextField(null=True, blank=True)
    message_uz = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
