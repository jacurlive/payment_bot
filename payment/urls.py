from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BotViewSet,
    SubscriptionPlanViewSet,
    UserViewSet,
    SubscriptionViewSet,
    PaymentViewSet,
    is_subscribed,
    subscribers,
)

router = DefaultRouter()
router.register(r"bots", BotViewSet)
router.register(r"plans", SubscriptionPlanViewSet)
router.register(r"users", UserViewSet)
router.register(r"subscriptions", SubscriptionViewSet)
router.register(r"payments", PaymentViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("is_subscribed/", is_subscribed),
    path("subscribers/", subscribers),
]
