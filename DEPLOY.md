# Развёртывание Payment Bot на новом сервере

## Требования к серверу
- Ubuntu 20.04 / 22.04
- Минимум 1 CPU, 1 GB RAM
- Python 3.10+, Git, Docker

---

## 1. Установка зависимостей системы

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3 python3-pip python3-venv nginx curl

# Docker (для PostgreSQL)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# Перелогинься или выполни: newgrp docker
```

---

## 2. Клонирование проекта

```bash
cd /var/www
sudo git clone https://github.com/jacurlive/payment_bot.git
sudo chown -R $USER:$USER /var/www/payment_bot
cd /var/www/payment_bot
```

---

## 3. Python окружение

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 4. База данных (PostgreSQL через Docker)

```bash
docker-compose up -d
```

Поднимет PostgreSQL на localhost:5432 с базой payment_db.

---

## 5. Файл .env

Создай /var/www/payment_bot/.env со следующим содержимым:

```
# ===== TELEGRAM BOT =====
BOT_TOKEN=<токен от @BotFather>
ADMIN_CHANNEL_ID=<ID группы/канала для уведомлений об оплатах>

# ===== BACKEND =====
BACKEND_URL=http://127.0.0.1:8000
BACKEND_USERNAME=admin
BACKEND_PASSWORD=<придумай надёжный пароль>

# ===== БАЗА ДАННЫХ =====
DB_NAME=payment_db
DB_USER=payment_user
DB_PASS=payment_pass
DB_PORT=5432

# ===== DJANGO =====
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,<IP или домен сервера>
SECRET_KEY=<сгенерируй командой ниже>

# ===== БЕЗОПАСНОСТЬ API =====
# IP адреса которым разрешён доступ к /api/
# Если бот на том же сервере — достаточно 127.0.0.1
# Если бот на другом сервере — добавь его IP через запятую
ALLOWED_IPS=127.0.0.1,::1

# ===== ПЛАТЁЖНЫЕ СИСТЕМЫ =====
CRYPTO_PAY_TOKEN=<токен от @CryptoBot>
STARS_RATE=0.017

# ===== PLATEGA (карта / СБП) =====
PLATEGA_MERCHANT_ID=<Merchant ID из личного кабинета Platega>
PLATEGA_SECRET=<API ключ из личного кабинета Platega>
PLATEGA_BASE_URL=https://app.platega.io
# Редиректы после оплаты (показываются пользователю в браузере) — под конкретный деплой/бота
PLATEGA_RETURN_URL=https://t.me/<username_бота>
PLATEGA_FAILED_URL=https://t.me/<username_бота>
```

Сгенерировать SECRET_KEY:
```bash
source venv/bin/activate
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 6. Миграции, статика и суперпользователь

```bash
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

Логин/пароль суперпользователя должны совпадать с BACKEND_USERNAME / BACKEND_PASSWORD из .env.

---

## 7. Systemd сервис — Django backend (Gunicorn)

Создай файл /etc/systemd/system/payment_django.service:

```
[Unit]
Description=Payment Bot Django Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/payment_bot
ExecStart=/var/www/payment_bot/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    root.wsgi:application
Restart=always
RestartSec=5
EnvironmentFile=/var/www/payment_bot/.env

[Install]
WantedBy=multi-user.target
```

Установить gunicorn если не установлен:
```bash
source venv/bin/activate
pip install gunicorn
```

Запустить сервис:
```bash
sudo chown -R www-data:www-data /var/www/payment_bot
sudo systemctl daemon-reload
sudo systemctl enable payment_django
sudo systemctl start payment_django
sudo systemctl status payment_django
```

---

## 8. Systemd сервис — Telegram Bot

Создай файл /etc/systemd/system/payment_bot.service:

```
[Unit]
Description=Payment Telegram Bot
After=network.target payment_django.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/payment_bot
ExecStart=/var/www/payment_bot/venv/bin/python -m bot.main
Restart=always
RestartSec=10
EnvironmentFile=/var/www/payment_bot/.env

[Install]
WantedBy=multi-user.target
```

Запустить сервис:
```bash
sudo systemctl daemon-reload
sudo systemctl enable payment_bot
sudo systemctl start payment_bot
sudo systemctl status payment_bot
```

---

## 9. Nginx

Создай файл /etc/nginx/sites-available/payment_bot:

```
server {
    listen 80;
    server_name <IP или домен сервера>;

    location /static/ {
        alias /var/www/payment_bot/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Активировать:
```bash
sudo ln -s /etc/nginx/sites-available/payment_bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 10. HTTPS через Let's Encrypt (если есть домен)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d <твой-домен.com>
sudo systemctl reload nginx
```

Сертификат обновляется автоматически.

---

## 11. Заполнить данные через Django Admin

Открой http://<IP или домен>/admin/ и создай:

1. Payment → Боты
   - username: юзернейм целевого бота (без @)
   - title: название бота
   - bot_token: токен целевого бота (нужен для отправки сообщений пользователям)
   - notification_group_id: ID группы для уведомлений (необязательно)

2. Payment → Планы подписок
   - name: название плана (например "1 месяц")
   - duration_days: количество дней
   - price_usdt: цена в USDT
   - price_stars: цена в Telegram Stars
   - is_active: включить

3. Payment → Планы для ботов
   - Привязать созданные планы к боту
   - is_active: включить нужные

4. Payment → Способы оплаты
   - Добавить нужные методы (crypto, stars, platega_card, platega_sbp — callback_data должен быть pay_card / pay_sbp)
   - is_active: включить

5. Payment → Сообщения
   - identifier: subscription_purchased
   - message_ru / message_en / message_uz: текст после покупки
   - Можно использовать {end_date} — подставится дата окончания подписки
   - Пример: "✅ Подписка активирована!\nДействует до: {end_date}"
   - После обновления кода выполнить `python manage.py populated_messages` — добавит/обновит
     тексты кнопок и сообщений для Platega (pay_platega_card_btn, pay_platega_sbp_btn,
     platega_invoice_error, platega_payment_confirmed)

6. Platega — личный кабинет мерчанта
   - В настройках вебхука указать URL: `https://<домен_сервера>/webhooks/platega/`
     (HTTPS, публичный домен с валидным SSL — самоподписанные сертификаты не принимаются)
   - Этот путь специально вынесен за пределы /api/, чтобы не попадать под IP-фильтр
     (ALLOWED_IPS) — сервер Platega обращается к нему напрямую извне

---

## 12. Проверка работы

```bash
# Логи Django
sudo journalctl -u payment_django -f

# Логи бота
sudo journalctl -u payment_bot -f

# Проверить API (должен вернуть access + refresh токены)
curl http://localhost:8000/api/token/ \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<пароль>"}'

# Статус сервисов
sudo systemctl status payment_django payment_bot nginx
```

---

## 13. Полезные команды при обновлении

```bash
cd /var/www/payment_bot

# Получить обновления из git
git pull

# Применить новые миграции (если есть)
source venv/bin/activate
python manage.py migrate

# Обновить тексты сообщений/кнопок (безопасно запускать всегда — только create/update)
python manage.py populated_messages

# Обновить статику
python manage.py collectstatic --noinput

# Перезапустить сервисы
sudo systemctl restart payment_django payment_bot
```

---

## Важные замечания

- SECRET_KEY — уникальный для каждого деплоя, никогда не публиковать
- Порт 5432 (PostgreSQL) не должен быть открыт наружу — только localhost
- BOT_TOKEN — новый токен от @BotFather для каждого клиента
- ALLOWED_IPS — если бот и Django на одном сервере, достаточно 127.0.0.1
- .env файл не попадает в git (добавлен в .gitignore) — создавать вручную на каждом сервере
