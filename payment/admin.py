from django.contrib import admin
from django.urls import path, reverse
from django.db.models import Count, Sum
from django.utils import timezone
from django.template.response import TemplateResponse
from datetime import datetime

from .models import User, Bot, SubscriptionPlan, Subscription, Payment


old_index = admin.site.index


admin.site.site_header = "Payment Bot"
admin.site.site_title = "Admin"
admin.site.index_title = "Site administration"


def custom_index(request, extra_context=None):
    if extra_context is None:
        extra_context = {}
    extra_context["custom_links"] = [
        {
            "title": "📊 Отчёты по подпискам",
            "url": reverse("admin:subscriptions-report"),
            "description": "Просмотр статистики, выгрузка отчётов и аналитика"
        },
    ]
    return old_index(request, extra_context=extra_context)

admin.site.index = custom_index


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


MONTHS_MAP = {
    "Jan.": "01", "Feb.": "02", "Mar.": "03", "Apr.": "04", "May.": "05", "Jun.": "06",
    "Jul.": "07", "Aug.": "08", "Sep.": "09", "Oct.": "10", "Nov.": "11", "Dec.": "12"
}


def normalize_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            parts = date_str.replace(",", "").split()
            month = MONTHS_MAP.get(parts[0])
            day = parts[1].zfill(2)
            year = parts[2]
            return datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
        except Exception:
            return None


def make_aware_if_needed(dt):
    if timezone.is_naive(dt):
        return timezone.make_aware(dt)
    return dt


def reports_view(request):
    date_from_str = request.GET.get("from")
    date_to_str = request.GET.get("to")

    if date_from_str and date_to_str:
        date_from = normalize_date(date_from_str)
        date_to = normalize_date(date_to_str)
        if not date_from or not date_to:
            now = timezone.now()
            date_from = datetime(now.year, now.month, 1)
            date_to = now
    else:
        now = timezone.now()
        date_from = datetime(now.year, now.month, 1)
        date_to = now

    date_from = make_aware_if_needed(date_from)
    date_to = make_aware_if_needed(date_to)

    payments = Payment.objects.filter(created_at__range=[date_from, date_to], status="success")

    stats = {
        "total_revenue": payments.aggregate(Sum("amount"))["amount__sum"] or 0,
        "total_count": payments.count(),
        "by_method": payments.values("method").annotate(count=Count("id"), amount=Sum("amount")),
        "by_bot": payments.values("bot__username").annotate(count=Count("id"), amount=Sum("amount")),
    }

    if request.GET.get("download") == "1":
        from .views import FullPaymentReportView
        view = FullPaymentReportView.as_view()
        request.GET = request.GET.copy()
        request.GET["from"] = date_from.strftime("%Y-%m-%d")
        request.GET["to"] = date_to.strftime("%Y-%m-%d")
        return view(request)

    context = {
        **admin.site.each_context(request),
        "title": "📊 Отчёты по подпискам",
        "stats": stats,
        "date_from": date_from.date(),
        "date_to": date_to.date(),
    }
    return TemplateResponse(request, "admin/subscriptions_report.html", context)


admin.site.get_urls = lambda old_get_urls=admin.site.get_urls: (
    lambda: [path("reports/", admin.site.admin_view(reports_view), name="subscriptions-report")] + old_get_urls()
)()