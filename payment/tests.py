import json
from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse

from .models import Bot, SubscriptionPlan, User, Subscription, Payment
from . import platega_client


class PlategaWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("platega-webhook")
        self.bot = Bot.objects.create(username="testbot", title="Test Bot", bot_token="123:ABC")
        self.plan = SubscriptionPlan.objects.create(
            name="1 месяц", duration_days=30, price_usdt=10, price_rub=990, is_active=True
        )
        self.auth_headers = {
            "HTTP_X_MERCHANTID": platega_client.PLATEGA_MERCHANT_ID or "test-merchant",
            "HTTP_X_SECRET": platega_client.PLATEGA_SECRET or "test-secret",
        }

    def _post(self, body, headers=None):
        headers = headers if headers is not None else self.auth_headers
        return self.client.post(
            self.url,
            data=json.dumps(body) if body is not None else "",
            content_type="application/json",
            **headers
        )

    def test_empty_body_returns_200(self):
        """Platega шлёт пустой POST для проверки доступности URL"""
        response = self.client.post(self.url, data="", content_type="application/json")
        self.assertEqual(response.status_code, 200)

    def test_malformed_json_returns_200_without_crash(self):
        response = self.client.post(self.url, data="not-json", content_type="application/json")
        self.assertEqual(response.status_code, 200)

    def test_get_request_rejected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    @patch.object(platega_client, "PLATEGA_MERCHANT_ID", "real-merchant-id")
    @patch.object(platega_client, "PLATEGA_SECRET", "real-secret")
    def test_wrong_credentials_rejected(self):
        response = self._post(
            {"id": "tx-1", "amount": 990, "currency": "RUB", "status": "CONFIRMED", "paymentMethod": 11},
            headers={"HTTP_X_MERCHANTID": "wrong", "HTTP_X_SECRET": "wrong"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_canceled_status_does_not_activate(self):
        response = self._post(
            {"id": "tx-canceled", "amount": 990, "currency": "RUB", "status": "CANCELED", "paymentMethod": 11}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Subscription.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)

    @patch("payment.views.get_platega_transaction")
    def test_confirmed_card_activates_subscription(self, mock_get_tx):
        telegram_id = 555111
        mock_get_tx.return_value = {
            "id": "tx-card-1",
            "payload": f"{telegram_id}:{self.bot.id}:{self.plan.id}:platega_card",
        }

        response = self._post(
            {"id": "tx-card-1", "amount": 990, "currency": "RUB", "status": "CONFIRMED", "paymentMethod": 11}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Subscription.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)

        sub = Subscription.objects.get()
        self.assertEqual(sub.user.telegram_id, telegram_id)
        self.assertEqual(sub.bot_id, self.bot.id)
        self.assertEqual(sub.plan_id, self.plan.id)
        self.assertTrue(sub.is_active)

        payment = Payment.objects.get()
        self.assertEqual(payment.method, "platega_card")
        self.assertEqual(payment.status, "success")
        self.assertEqual(payment.transaction_id, "tx-card-1")
        self.assertEqual(payment.amount, self.plan.price_usdt)

    @patch("payment.views.get_platega_transaction")
    def test_confirmed_sbp_activates_subscription(self, mock_get_tx):
        telegram_id = 555222
        mock_get_tx.return_value = {
            "id": "tx-sbp-1",
            "payload": f"{telegram_id}:{self.bot.id}:{self.plan.id}:platega_sbp",
        }

        response = self._post(
            {"id": "tx-sbp-1", "amount": 990, "currency": "RUB", "status": "CONFIRMED", "paymentMethod": 2}
        )

        self.assertEqual(response.status_code, 200)
        payment = Payment.objects.get()
        self.assertEqual(payment.method, "platega_sbp")

    @patch("payment.views.get_platega_transaction")
    def test_duplicate_webhook_is_idempotent(self, mock_get_tx):
        """Platega ретраит вебхук до 3 раз — повторная доставка не должна дублировать подписку"""
        telegram_id = 555333
        mock_get_tx.return_value = {
            "id": "tx-dup-1",
            "payload": f"{telegram_id}:{self.bot.id}:{self.plan.id}:platega_card",
        }
        body = {"id": "tx-dup-1", "amount": 990, "currency": "RUB", "status": "CONFIRMED", "paymentMethod": 11}

        first = self._post(body)
        second = self._post(body)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Subscription.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)

    @patch("payment.views.get_platega_transaction")
    def test_unknown_bot_does_not_crash(self, mock_get_tx):
        mock_get_tx.return_value = {
            "id": "tx-badbot",
            "payload": "999999:99999:99999:platega_card",
        }
        response = self._post(
            {"id": "tx-badbot", "amount": 990, "currency": "RUB", "status": "CONFIRMED", "paymentMethod": 11}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Subscription.objects.count(), 0)

    @patch("payment.views.get_platega_transaction")
    def test_missing_payload_does_not_crash(self, mock_get_tx):
        mock_get_tx.return_value = {"id": "tx-nopayload", "payload": ""}
        response = self._post(
            {"id": "tx-nopayload", "amount": 990, "currency": "RUB", "status": "CONFIRMED", "paymentMethod": 11}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Subscription.objects.count(), 0)

    @patch("payment.views.get_platega_transaction")
    def test_transaction_lookup_failure_does_not_crash(self, mock_get_tx):
        mock_get_tx.return_value = None
        response = self._post(
            {"id": "tx-lookupfail", "amount": 990, "currency": "RUB", "status": "CONFIRMED", "paymentMethod": 11}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Subscription.objects.count(), 0)


class PaymentModelChoicesTests(TestCase):
    def test_platega_methods_registered(self):
        method_values = dict(Payment.PAYMENTS_METHODS)
        self.assertIn("platega_card", method_values)
        self.assertIn("platega_sbp", method_values)


class PlategaWebhookIPWhitelistTests(TestCase):
    """
    Убеждаемся, что /webhooks/platega/ не блокируется IPWhitelistMiddleware
    (он проверяет только пути, начинающиеся с /api/), а /api/ по-прежнему
    защищён для внешних IP как раньше.
    """
    EXTERNAL_IP = "116.202.184.149"  # IP Platega из документации

    def test_webhook_reachable_from_external_ip(self):
        response = self.client.post(
            reverse("platega-webhook"),
            data="",
            content_type="application/json",
            REMOTE_ADDR=self.EXTERNAL_IP
        )
        self.assertEqual(response.status_code, 200)

    def test_api_still_blocked_for_external_ip(self):
        response = self.client.get("/api/bots/", REMOTE_ADDR=self.EXTERNAL_IP)
        self.assertEqual(response.status_code, 403)
