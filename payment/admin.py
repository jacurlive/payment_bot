from django.contrib import admin
from .models import User, Bot, SubscriptionPlan, Subscription, Payment


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "username", "first_name", "last_name", "created_at")
    list_display_links = ("telegram_id", "username", "first_name", "last_name", "created_at")


@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "title", "created_at")
    list_display_links = ("username", "title", "created_at")


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("bot", "name", "duration_days", "price", "is_active", "created_at")
    list_display_links = ("bot", "name", "duration_days", "price")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "bot", "plan", "start_date", "end_date", "is_active", "created_at")
    list_display_links = ("user", "bot", "plan")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("user", "bot", "subscription", "method", "amount", "status", "transaction_id", "created_at")
    list_display_links = ("user", "bot", "subscription", "method", "amount", "status")
