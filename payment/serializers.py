from rest_framework import serializers
from .models import Bot, SubscriptionPlan, User, Subscription, Payment, PaymentMethod, Messages, BotPlan


class MessagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Messages
        fields = "__all__"


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = "__all__"


class BotPlanSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlan.objects.all(),
        source='plan',
        write_only=True
    )
    bot_id = serializers.PrimaryKeyRelatedField(
        queryset=Bot.objects.all(),
        source='bot',
        write_only=True
    )

    bot_username = serializers.CharField(source='bot.username', read_only=True)
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    duration_days = serializers.IntegerField(source='plan.duration_days', read_only=True)

    class Meta:
        model = BotPlan
        fields = [
            'id',
            'bot',
            'bot_id',
            'bot_username',
            'plan',
            'plan_id',
            'plan_name',
            'duration_days',
            'is_active',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class BotSerializer(serializers.ModelSerializer):
    bot_plans = BotPlanSerializer(many=True, read_only=True)

    class Meta:
        model = Bot
        fields = [
            'id',
            'username',
            'title',
            'bot_token',
            'notification_group_id',
            'request_port',
            'order',
            'created_at',
            'bot_plans'
        ]


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


class PaymentCreateSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(write_only=True)
    bot_id = serializers.IntegerField(write_only=True)
    subscription_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Payment
        fields = [
            "user_id",
            "bot_id",
            "subscription_id",
            "method",
            "amount",
            "status",
        ]

    def create(self, validated_data):
        user = User.objects.get(telegram_id=validated_data.pop("user_id"))
        bot = Bot.objects.get(id=validated_data.pop("bot_id"))
        subscription = Subscription.objects.get(id=validated_data.pop("subscription_id"))

        return Payment.objects.create(
            user=user,
            bot=bot,
            subscription=subscription,
            **validated_data
        )


class PaymentReadSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    bot = BotSerializer(read_only=True)
    subscription = SubscriptionReadSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = "__all__"


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = "__all__"
