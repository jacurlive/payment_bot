import io

from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from datetime import datetime

from .models import Bot, SubscriptionPlan, User, Subscription, Payment, PaymentMethod, Messages
from .serializers import (
    BotSerializer,
    SubscriptionPlanSerializer,
    UserSerializer,
    # SubscriptionSerializer,
    SubscriptionCreateSerializer,
    SubscriptionReadSerializer,
    PaymentCreateSerializer,
    PaymentReadSerializer,
    PaymentMethodSerializer,
    MessagesSerializer
)


class FullPaymentReportView(APIView):
    authentication_classes = []  # отключаем DRF авторизацию
    permission_classes = []

    def get(self, request):
        date_from_str = request.query_params.get("from")
        date_to_str = request.query_params.get("to")
        bot_id = request.query_params.get("bot_id")

        # Обработка диапазона дат
        if date_from_str and date_to_str:
            date_from = timezone.make_aware(datetime.strptime(date_from_str, "%Y-%m-%d"))
            date_to = timezone.make_aware(datetime.strptime(date_to_str, "%Y-%m-%d"))
        else:
            now = timezone.now()
            date_from = timezone.make_aware(datetime(now.year, now.month, 1))
            date_to = now

        payments = Payment.objects.filter(created_at__range=[date_from, date_to], status="success")
        if bot_id:
            payments = payments.filter(id=bot_id)

        total_payments = payments.count()
        total_revenue = sum(p.amount for p in payments)

        by_method = {}
        by_bot = {}
        for p in payments:
            by_method.setdefault(p.method, {"count": 0, "amount": 0})
            by_method[p.method]["count"] += 1
            by_method[p.method]["amount"] += p.amount

            bot_name = p.bot.username if p.bot else "—"
            by_bot.setdefault(bot_name, {"count": 0, "amount": 0})
            by_bot[bot_name]["count"] += 1
            by_bot[bot_name]["amount"] += p.amount

        wb = Workbook()
        ws = wb.active
        ws.title = "Payment Report"

        ws.append(["📊 Отчёт по оплатам"])
        ws.append(["Период", f"{date_from.date()} — {date_to.date()}"])
        ws.append(["Всего платежей", total_payments])
        ws.append(["Общая сумма", total_revenue])
        ws.append([])

        ws.append(["Разбивка по методам оплаты"])
        ws.append(["Метод", "Количество", "Сумма"])
        for m, v in by_method.items():
            ws.append([m, v["count"], v["amount"]])
        ws.append([])

        ws.append(["Разбивка по ботам"])
        ws.append(["Бот", "Количество", "Сумма"])
        for b, v in by_bot.items():
            ws.append([b, v["count"], v["amount"]])
        ws.append([])

        ws.append(["ID", "User (Telegram ID)", "Bot", "Plan", "Amount", "Method", "Status", "Дата покупки"])
        for p in payments:
            ws.append([
                p.id,
                p.user.telegram_id if p.user else "—",
                p.bot.username if p.bot else "—",
                p.subscription.plan.name if p.subscription and p.subscription.plan else "—",
                p.amount,
                p.method,
                p.status,
                p.created_at.strftime("%Y-%m-%d %H:%M:%S")
            ])

        for col in ws.columns:
            max_length = 0
            column = get_column_letter(col[0].column)
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except Exception as e:
                    print(e)
            ws.column_dimensions[column].width = max_length + 2

        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        filename = f"payments_report_{date_from.date()}_{date_to.date()}.xlsx"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response


class PaymentSummaryReportView(APIView):

    def get(self, request):
        date_from = request.query_params.get("from", "2025-10-01")
        date_to = request.query_params.get("to", "2025-10-30")

        payments = Payment.objects.filter(created_at__range=[date_from, date_to])

        total_revenue = payments.aggregate(Sum("amount"))["amount__sum"] or 0
        total_payments = payments.count()

        methods = payments.values("method").annotate(
            count=Count("id"),
            amount=Sum("amount")
        )

        bots = payments.values("bot__username").annotate(
            count=Count("id"),
            amount=Sum("amount")
        )

        wb = Workbook()
        ws = wb.active
        ws.title = "Payments Summary"

        bold = Font(bold=True)

        ws.append(["Total Revenue", total_revenue])
        ws.append(["Total Payments", total_payments])
        ws.append([])
        ws.append(["Period", f"{date_from} - {date_to}"])
        ws.append([])
        ws.append([])

        ws.append(["By Method"])
        ws.append(["Method", "Count", "Amount"])
        for m in methods:
            ws.append([
                m["method"],
                m["count"],
                m["amount"],
            ])
        ws.append([])
        ws.append([])

        ws.append(["By Bot"])
        ws.append(["Bot", "Count", "Amount"])
        for b in bots:
            ws.append([
                b["bot__username"] or "-",
                b["count"],
                b["amount"],
            ])

        for cell in ws["A1":"B1"][0]:
            cell.font = bold

        stream = io.BytesIO()
        wb.save(stream)
        stream.seek(0)

        response = FileResponse(
            stream,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="payments_summary_{date_from}_{date_to}.xlsx"'
        return response



class BotViewSet(viewsets.ModelViewSet):
    queryset = Bot.objects.all()
    serializer_class = BotSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        username = self.request.query_params.get("username")
        if username:
            qs = qs.filter(username__iexact=username)
        return qs


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer

    def get_queryset(self):
        queryset = SubscriptionPlan.objects.all()
        bot_id = self.request.query_params.get("bot_id")
        if bot_id:
            queryset = queryset.filter(bot_id=bot_id)
        return queryset.order_by("duration_days")


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = "telegram_id"


class PaymentMethodViewSet(viewsets.ModelViewSet):
    queryset = PaymentMethod.objects.filter()
    serializer_class = PaymentMethodSerializer


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Messages.objects.all()
    serializer_class = MessagesSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        identifier = self.request.query_params.get("identifier")

        if identifier:
            queryset = queryset.filter(identifier=identifier)

        return queryset


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return SubscriptionReadSerializer
        return SubscriptionCreateSerializer


# class SubscriptionViewSet(viewsets.ModelViewSet):
#     queryset = Subscription.objects.all()
#     serializer_class = SubscriptionSerializer
#
#     @action(detail=False, methods=["post"])
#     def activate(self, request):
#         """
#         Ручная активация подписки (бесплатная).
#         {
#           "telegram_id": 123456,
#           "bot_id": 1,
#           "plan_id": 2
#         }
#         """
#         telegram_id = request.data.get("telegram_id")
#         bot_id = request.data.get("bot_id")
#         plan_id = request.data.get("plan_id")
#
#         user, _ = User.objects.get_or_create(telegram_id=telegram_id)
#         bot = get_object_or_404(Bot, id=bot_id)
#         plan = get_object_or_404(SubscriptionPlan, id=plan_id)
#
#         start = timezone.now()
#         if plan.duration_days:
#             end = start + timezone.timedelta(days=plan.duration_days)
#         else:
#             end = None
#
#         sub = Subscription.objects.create(
#             user=user, bot=bot, plan=plan, start_date=start, end_date=end, is_active=True
#         )
#
#         return Response({"status": "activated", "subscription_id": sub.id})


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()

    def get_serializer_class(self):
        if self.action in ["create", "mock"]:
            return PaymentCreateSerializer
        return PaymentReadSerializer

    @action(detail=False, methods=["post"])
    def mock(self, request):
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
            user=user,
            bot=bot,
            plan=plan,
            start_date=start,
            end_date=end,
            is_active=True
        )

        payment = Payment.objects.create(
            user=user,
            bot=bot,
            subscription=sub,
            method=method,
            amount=plan.price_usdt,
            status="success"
        )

        return Response(
            PaymentReadSerializer(payment).data,
            status=201
        )


# class PaymentViewSet(viewsets.ModelViewSet):
#     queryset = Payment.objects.all()
#     serializer_class = PaymentSerializer
#
#     @action(detail=False, methods=["post"])
#     def mock(self, request):
#         """
#         Тестовая покупка (заглушка).
#         {
#           "telegram_id": 123456,
#           "bot_id": 1,
#           "plan_id": 2,
#           "method": "stub"
#         }
#         """
#         telegram_id = request.data.get("telegram_id")
#         bot_id = request.data.get("bot_id")
#         plan_id = request.data.get("plan_id")
#         method = request.data.get("method", "stub")
#
#         user, _ = User.objects.get_or_create(telegram_id=telegram_id)
#         bot = get_object_or_404(Bot, id=bot_id)
#         plan = get_object_or_404(SubscriptionPlan, id=plan_id)
#
#         start = timezone.now()
#         end = start + timezone.timedelta(days=plan.duration_days) if plan.duration_days else None
#
#         sub = Subscription.objects.create(
#             user=user, bot=bot, plan=plan, start_date=start, end_date=end, is_active=True
#         )
#
#         payment = Payment.objects.create(
#             user=user, bot=bot, subscription=sub, method=method,
#             amount=plan.price_usdt, status="success"
#         )
#
#         return Response({
#             "status": "success",
#             "subscription_id": sub.id,
#             "payment_id": payment.id
#         })
#
#
#     @action(detail=False, methods=["get"])
#     def report(self, request):
#
#         from_date = request.GET.get("from")
#         to_date = request.GET.get("to")
#
#         qs = Payment.objects.filter(status="success")
#
#         if from_date:
#             qs = qs.filter(created_at__date__gte=from_date)
#         if to_date:
#             qs = qs.filter(created_at__date__lte=to_date)
#
#         total_revenue = qs.aggregate(total=Sum("amount"))["total"] or 0
#         total_payments = qs.count()
#
#         by_method = (
#             qs.values("method")
#             .annotate(count=Count("id"), amount=Sum("amount"))
#             .order_by()
#         )
#         by_method_dict = {
#             item["method"]: {"count": item["count"], "amount": item["amount"] or 0}
#             for item in by_method
#         }
#
#         by_bot = (
#             qs.values("bot__username")
#             .annotate(count=Count("id"), amount=Sum("amount"))
#             .order_by()
#         )
#         by_bot_list = [
#             {"bot": item["bot__username"], "count": item["count"], "amount": item["amount"] or 0}
#             for item in by_bot
#         ]
#
#         return Response({
#             "total_revenue": total_revenue,
#             "total_payments": total_payments,
#             "by_method": by_method_dict,
#             "by_bot": by_bot_list,
#             "period": {"from": from_date, "to": to_date},
#         })


# --------- API for Bots ---------

@api_view(["GET"])
@permission_classes([AllowAny])
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
