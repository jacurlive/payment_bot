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
    is_subscribed,
    subscribers,
)

router = DefaultRouter()
router.register(r"bots", BotViewSet)
router.register(r"plans", SubscriptionPlanViewSet)
router.register(r"users", UserViewSet)
router.register(r"subscriptions", SubscriptionViewSet)
router.register(r"payments", PaymentViewSet)
router.register(r"methods", PaymentMethodViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("is_subscribed/", is_subscribed),
    path("subscribers/", subscribers),
    path("reports/payments/", FullPaymentReportView.as_view()),
    path("reports/payments/summary/", PaymentSummaryReportView.as_view())
]
