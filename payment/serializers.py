from rest_framework import serializers
from .models import Bot, SubscriptionPlan, User, Subscription, Payment, PaymentMethod, Messages


class MessagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Messages
        fields = "__all__"


class BotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bot
        fields = "__all__"


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(
        slug_field="telegram_id",
        queryset=User.objects.all()
    )
    bot = serializers.PrimaryKeyRelatedField(
        queryset=Bot.objects.all()
    )
    plan = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlan.objects.all()
    )

    class Meta:
        model = Subscription
        fields = "__all__"


class SubscriptionReadSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    bot = BotSerializer(read_only=True)
    plan = SubscriptionPlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = "__all__"


# class SubscriptionSerializer(serializers.ModelSerializer):
#     user = UserSerializer(read_only=True)
#     bot = BotSerializer(read_only=True)
#     plan = SubscriptionPlanSerializer(read_only=True)
#
#     class Meta:
#         model = Subscription
#         fields = "__all__"


class PaymentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    bot = BotSerializer(read_only=True)
    subscription = SubscriptionCreateSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = "__all__"


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = "__all__"
