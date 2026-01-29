from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BotViewSet,
    SubscriptionPlanViewSet,
    UserViewSet,
    SubscriptionViewSet,
    PaymentViewSet,
    FullPaymentReportView,
    PaymentSummaryReportView,
    PaymentMethodViewSet,
    MessageViewSet,
    is_subscribed,
    subscribers,
    send_test_message,
    send_purchase_notification
)

router = DefaultRouter()
router.register(r"bots", BotViewSet)
router.register(r"plans", SubscriptionPlanViewSet)
router.register(r"users", UserViewSet)
router.register(r"subscriptions", SubscriptionViewSet)
router.register(r"payments", PaymentViewSet)
router.register(r"methods", PaymentMethodViewSet)
router.register(r"messages", MessageViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("is_subscribed/", is_subscribed),
    path("subscribers/", subscribers),
    path("send_test_message/", send_test_message),
    path("reports/payments/", FullPaymentReportView.as_view()),
    path("reports/payments/summary/", PaymentSummaryReportView.as_view()),
    path("send_purchase_notification/", send_purchase_notification),
]
