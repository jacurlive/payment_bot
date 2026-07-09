from django.core.management.base import BaseCommand
from payment.models import Messages


class Command(BaseCommand):
    help = 'Заполняет таблицу Messages стандартными текстами'

    def handle(self, *args, **options):
        messages_data = [
            {
                'identifier': 'welcome',
                'message_ru': 'Здравствуйте! Добро пожаловать. Пожалуйста, выберите язык. 🇷🇺',
                'message_en': 'Hello! Welcome. Please select a language. 🇺🇸',
                'message_uz': 'Assalomu alaykum! Xush kelibsiz. Iltimos, tilni tanlang. 🇺🇿',
            },
            {
                'identifier': 'choice_bot',
                'message_ru': 'Вы выбрали бота',
                'message_en': 'You have selected the bot',
                'message_uz': 'Siz tanlagan bot',
            },
            {
                'identifier': 'choice_plan',
                'message_ru': 'Выберите тариф',
                'message_en': 'Select a subscription plan',
                'message_uz': 'Tarifni tanlang',
            },
            {
                'identifier': 'not_bot',
                'message_ru': '❌ Бот не найден.',
                'message_en': '❌ Bot not found.',
                'message_uz': '❌ Bot topilmadi.',
            },
            {
                'identifier': 'not_active_plan',
                'message_ru': '❌ Для этого бота нет тарифов.',
                'message_en': '❌ There are no available plans for this bot.',
                'message_uz': '❌ Ushbu bot uchun tariflar mavjud emas.',
            },
            {
                'identifier': 'not_available_bot',
                'message_ru': 'Нет доступных ботов.',
                'message_en': 'No available bots.',
                'message_uz': 'Mavjud botlar yo\'q.',
            },
            {
                'identifier': 'which_bot',
                'message_ru': '👋 Привет! Выберите, в каком боте хотите купить подписку:',
                'message_en': '👋 Hi! Choose which bot you want to purchase a subscription for:',
                'message_uz': '👋 Salom! Qaysi bot uchun obuna sotib olmoqchisiz:',
            },
            {
                'identifier': 'button_data_error',
                'message_ru': 'Ошибка данных кнопки',
                'message_en': 'Button data error',
                'message_uz': 'Tugma maʼlumotlarida xatolik',
            },
            {
                'identifier': 'not_plan',
                'message_ru': 'Тариф не найден',
                'message_en': 'Subscription plan not found',
                'message_uz': 'Tarif topilmadi',
            },
            {
                'identifier': 'pay_crypto_bot',
                'message_ru': '💳 Оплатить через CryptoBot',
                'message_en': '💳 Pay via CryptoBot',
                'message_uz': '💳 CryptoBot orqali to\'lash',
            },
            {
                'identifier': 'back_btn',
                'message_ru': '🔙 Назад',
                'message_en': '🔙 Back',
                'message_uz': '🔙 Orqaga',
            },
            {
                'identifier': 'payment_from',
                'message_ru': 'Оплата через',
                'message_en': 'Payment via',
                'message_uz': 'To\'lov usuli',
            },
            {
                'identifier': 'plan',
                'message_ru': 'Тариф',
                'message_en': 'Plan',
                'message_uz': 'Tarif',
            },
            {
                'identifier': 'price',
                'message_ru': 'Сумма',
                'message_en': 'Amount',
                'message_uz': 'Summa',
            },
            {
                'identifier': 'after_buy_text',
                'message_ru': 'После оплаты бот активирует подписку автоматически ✅',
                'message_en': 'After payment, the bot will activate your subscription automatically ✅',
                'message_uz': 'To\'lovdan so\'ng obuna avtomatik tarzda faollashtiriladi ✅',
            },
            {
                'identifier': 'crypto_invoice_error',
                'message_ru': '❌ Ошибка при создании платежа через CryptoBot.',
                'message_en': '❌ Failed to create a CryptoBot invoice.',
                'message_uz': '❌ CryptoBot orqali hisob yaratishda xatolik yuz berdi.',
            },
            {
                'identifier': 'not_paid',
                'message_ru': '❗ Оплата ещё не получена',
                'message_en': '❗ Payment has not been received yet',
                'message_uz': '❗ To\'lov hali qabul qilinmadi',
            },
            {
                'identifier': 'paid',
                'message_ru': '✅ Оплата получена! Подписка активирована.',
                'message_en': '✅ Payment received! Subscription activated.',
                'message_uz': '✅ To\'lov qabul qilindi! Obuna faollashtirildi.',
            },
            {
                'identifier': 'paid_but_not_activated',
                'message_ru': '⚠️ Оплата прошла, но не удалось активировать подписку.',
                'message_en': '⚠️ Payment was successful, but the subscription could not be activated.',
                'message_uz': '⚠️ To\'lov muvaffaqiyatli, ammo obuna faollashtirilmadi.',
            },
            {
                'identifier': 'stars_invoice_error',
                'message_ru': '❌ Не удалось создать счёт через Telegram Stars.',
                'message_en': '❌ Failed to create a Telegram Stars invoice.',
                'message_uz': '❌ Telegram Stars orqali hisob yaratib bo\'lmadi.',
            },
            {
                'identifier': 'stars_payment_success',
                'message_ru': '✅ Оплата через Telegram Stars прошла успешно!',
                'message_en': '✅ Payment via Telegram Stars was successful!',
                'message_uz': '✅ Telegram Stars orqali to\'lov muvaffaqiyatli amalga oshirildi!',
            },
            {
                'identifier': 'you_choice',
                'message_ru': 'Вы выбрали',
                'message_en': 'You selected',
                'message_uz': 'Siz tanladingiz',
            },
            {
                'identifier': 'price_1',
                'message_ru': '💰 Цена',
                'message_en': '💰 Price',
                'message_uz': '💰 Narx',
            },
            {
                'identifier': 'choice_payment_type',
                'message_ru': 'Выберите способ оплаты',
                'message_en': 'Select a payment method',
                'message_uz': 'To\'lov usulini tanlang',
            },
            {
                'identifier': 'check_crypto_pay',
                'message_ru': '✅ Проверить оплату',
                'message_en': '✅ Check payment',
                'message_uz': '✅ To\'lovni tekshirish',
            },
            {
                'identifier': 'message_check_crypto_pay',
                'message_ru': '⚠️ После оплаты нажмите кнопку ✅ Проверить оплату',
                'message_en': '⚠️ After payment, click the ✅ Check payment button',
                'message_uz': '⚠️ Toʻlovni amalga oshirgandan soʻng ✅ Toʻlovni tekshirish tugmasini bosing',
            },
            {
                'identifier': 'pay_platega_card_btn',
                'message_ru': '💳 Оплатить картой',
                'message_en': '💳 Pay by card',
                'message_uz': '💳 Karta orqali to\'lash',
            },
            {
                'identifier': 'pay_platega_sbp_btn',
                'message_ru': '🏦 Оплатить через СБП',
                'message_en': '🏦 Pay via SBP',
                'message_uz': '🏦 SBP orqali to\'lash',
            },
            {
                'identifier': 'platega_invoice_error',
                'message_ru': '❌ Ошибка при создании платежа. Попробуйте позже.',
                'message_en': '❌ Failed to create a payment. Please try again later.',
                'message_uz': '❌ To\'lov yaratishda xatolik. Keyinroq urinib ko\'ring.',
            },
            {
                'identifier': 'platega_payment_confirmed',
                'message_ru': '✅ Оплата подтверждена! Подписка будет активирована в течение нескольких секунд.',
                'message_en': '✅ Payment confirmed! Your subscription will be activated within a few seconds.',
                'message_uz': '✅ To\'lov tasdiqlandi! Obuna bir necha soniya ichida faollashtiriladi.',
            }
        ]

        created_count = 0
        skipped_count = 0

        for data in messages_data:
            message, created = Messages.objects.get_or_create(
                identifier=data['identifier'],
                defaults={
                    'message_ru': data['message_ru'],
                    'message_en': data['message_en'],
                    'message_uz': data['message_uz'],
                }
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✅ Создано: {data["identifier"]}'))
            else:
                skipped_count += 1
                self.stdout.write(self.style.WARNING(f'⏭️ Пропущено (уже существует): {data["identifier"]}'))

        self.stdout.write(self.style.SUCCESS(f'\n📊 Итого:'))
        self.stdout.write(self.style.SUCCESS(f'   Создано: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'   Пропущено (уже существовало): {skipped_count}'))
