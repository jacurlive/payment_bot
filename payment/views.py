from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate

from .models import Bot, SubscriptionPlan, User, Subscription, Payment
from .serializers import (
    BotSerializer,
    SubscriptionPlanSerializer,
    UserSerializer,
    SubscriptionSerializer,
    PaymentSerializer,
)


# --------- CRUD ViewSets ---------

class BotViewSet(viewsets.ModelViewSet):
    queryset = Bot.objects.all()
    serializer_class = BotSerializer


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer

    @action(detail=False, methods=["post"])
    def activate(self, request):
        """
        Ручная активация подписки (бесплатная).
        {
          "telegram_id": 123456,
          "bot_id": 1,
          "plan_id": 2
        }
        """
        telegram_id = request.data.get("telegram_id")
        bot_id = request.data.get("bot_id")
        plan_id = request.data.get("plan_id")

        user, _ = User.objects.get_or_create(telegram_id=telegram_id)
        bot = get_object_or_404(Bot, id=bot_id)
        plan = get_object_or_404(SubscriptionPlan, id=plan_id)

        start = timezone.now()
        if plan.duration_days:
            end = start + timezone.timedelta(days=plan.duration_days)
        else:
            end = None

        sub = Subscription.objects.create(
            user=user, bot=bot, plan=plan, start_date=start, end_date=end, is_active=True
        )

        return Response({"status": "activated", "subscription_id": sub.id})


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    @action(detail=False, methods=["post"])
    def mock(self, request):
        """
        Тестовая покупка (заглушка).
        {
          "telegram_id": 123456,
          "bot_id": 1,
          "plan_id": 2,
          "method": "stub"
        }
        """
        telegram_id = request.data.get("telegram_id")
        bot_id = request.data.get("bot_id")
        plan_id = request.data.get("plan_id")
        method = request.data.get("method", "stub")

        user, _ = User.objects.get_or_create(telegram_id=telegram_id)
        bot = get_object_or_404(Bot, id=bot_id)
        plan = get_object_or_404(SubscriptionPlan, id=plan_id)

        start = timezone.now()
        end = start + timezone.timedelta(days=plan.duration_days) if plan.duration_days else None

        sub = Subscription.objects.create(
            user=user, bot=bot, plan=plan, start_date=start, end_date=end, is_active=True
        )

        payment = Payment.objects.create(
            user=user, bot=bot, subscription=sub, method=method,
            amount=plan.price, status="success"
        )

        return Response({
            "status": "success",
            "subscription_id": sub.id,
            "payment_id": payment.id
        })


    @action(detail=False, methods=["get"])
    def report(self, request):

        """
        Возвращает агрегированные данные о платежах за выбранный период.
        Пример запроса:
        /api/payments/report/?from=2025-09-01&to=2025-09-30
        """

        from_date = request.GET.get("from")
        to_date = request.GET.get("to")

        qs = Payment.objects.filter(status="success")

        if from_date:
            qs = qs.filter(created_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(created_at__date__lte=to_date)

        total_revenue = qs.aggregate(total=Sum("amount"))["total"] or 0
        total_payments = qs.count()

        by_method = (
            qs.values("method")
            .annotate(count=Count("id"), amount=Sum("amount"))
            .order_by()
        )
        by_method_dict = {
            item["method"]: {"count": item["count"], "amount": item["amount"] or 0}
            for item in by_method
        }

        by_bot = (
            qs.values("bot__username")
            .annotate(count=Count("id"), amount=Sum("amount"))
            .order_by()
        )
        by_bot_list = [
            {"bot": item["bot__username"], "count": item["count"], "amount": item["amount"] or 0}
            for item in by_bot
        ]

        return Response({
            "total_revenue": total_revenue,
            "total_payments": total_payments,
            "by_method": by_method_dict,
            "by_bot": by_bot_list,
            "period": {"from": from_date, "to": to_date},
        })


# --------- API for Bots ---------

@api_view(["GET"])
def is_subscribed(request):
    user_id = request.GET.get("user_id")
    bot_username = request.GET.get("botusername")

    bot = get_object_or_404(Bot, username=bot_username)
    user = User.objects.filter(telegram_id=user_id).first()

    if not user:
        return Response({"is_subscribed": False})

    sub = Subscription.objects.filter(user=user, bot=bot, is_active=True).order_by("-end_date").first()

    if not sub:
        return Response({"is_subscribed": False})

    return Response({
        "is_subscribed": True,
        "subscription_start_date": int(sub.start_date.timestamp()) if sub.start_date else None,
        "subscription_end_date": int(sub.end_date.timestamp()) if sub.end_date else None
    })


@api_view(["GET"])
def subscribers(request):
    bot_username = request.GET.get("botusername")
    bot = get_object_or_404(Bot, username=bot_username)

    subs = Subscription.objects.filter(bot=bot, is_active=True)
    user_ids = list(subs.values_list("user__telegram_id", flat=True))

    return Response(user_ids)
