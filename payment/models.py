from django.db import models

class Bot(models.Model):
    username = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=150, blank=True)
    notification_group_id = models.BigIntegerField(null=True, blank=True)
    bot_token = models.CharField(max_length=255, null=True, blank=True)
    request_port = models.IntegerField(null=True, blank=True)
    order = models.PositiveIntegerField(null=True, blank=True, verbose_name="Очерёдность")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Бот"
        verbose_name_plural = "Боты"

    def __str__(self):
        return self.username


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=64)
    duration_days = models.PositiveIntegerField(null=True, blank=True)

    price_usdt = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Цена USDT")
    price_uzs = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Цена UZS")
    price_stars = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Цена Stars")
    price_rub = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Цена RUB")

    is_active = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    # Какое поле цены использовать для какого способа оплаты.
    # Чтобы добавить новый способ — достаточно добавить запись сюда.
    PRICE_FIELD_BY_METHOD = {
        "payme": "price_uzs",
        "click": "price_uzs",
        "crypto": "price_usdt",
        "stars": "price_stars",
        "russian_card": "price_rub",
        "platega_card": "price_rub",
        "platega_sbp": "price_rub",
    }

    class Meta:
        verbose_name = "План подписки"
        verbose_name_plural = "Планы подписок"

    def __str__(self):
        return self.name

    def price_for_method(self, method):
        field = self.PRICE_FIELD_BY_METHOD.get(method, "price_usdt")
        return getattr(self, field, None) or self.price_usdt


class BotPlan(models.Model):
    bot = models.ForeignKey(
        Bot,
        on_delete=models.CASCADE,
        related_name="bot_plans",
        verbose_name="Бот"
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        related_name="bot_plans",
        verbose_name="План"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "План для бота"
        verbose_name_plural = "Планы для ботов"
        unique_together = ('bot', 'plan')
        ordering = ['plan__duration_days']

    def __str__(self):
        return f"{self.bot.username} - {self.plan.name}"


class Language(models.TextChoices):
    RU = "ru", "Русский"
    EN = "en", "English"
    UZ = "uz", "O'zbekcha"


class User(models.Model):
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
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

    expiring_3days_sent = models.BooleanField(default=False, verbose_name="Отправлено уведомление за 3 дня")
    expiring_2days_sent = models.BooleanField(default=False, verbose_name="Отправлено уведомление за 2 дня")
    expiring_1day_sent = models.BooleanField(default=False, verbose_name="Отправлено уведомление за 1 день")

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
        ("platega_card", "Platega Card"),
        ("platega_sbp", "Platega SBP"),
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
    order = models.PositiveIntegerField(null=True, blank=True, verbose_name="Очерёдность")

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
