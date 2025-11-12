from .client import request

async def get_all_bots():
    resp = await request("GET", "/api/bots/")
    return resp.json() if resp.status_code == 200 else []

async def get_bot_by_username(username):
    resp = await request("GET", "/api/bots/", params={"username": username})
    return resp.json()[0] if resp.status_code == 200 and resp.json() else []

async def get_plans_for_bot(bot_id):
    resp = await request("GET", f"/api/plans/", params={"bot_id": bot_id})
    return resp.json() if resp.status_code == 200 else []

async def get_payment_methods():
    resp = await request("GET", f"/api/methods/")
    return resp.json() if resp.status_code == 200 else []

async def create_mock_payment(telegram_id, bot_id, plan_id):
    payload = {"telegram_id": telegram_id, "bot_id": bot_id, "plan_id": plan_id, "method": "stub"}
    resp = await request("POST", "/api/payments/mock/", json=payload)
    return resp.json() if resp.status_code in (200, 201) else []

async def create_user(user):
    payload = {"telegram_id": user.id, "username": user.username, "first_name": user.first_name, "last_name": user.last_name, "language": "ru", "is_active": True}
    resp = await request("POST", "/api/users/", json=payload)
    return resp.json() if resp.status_code in (200, 201) else []

async def change_language(telegram_id, language):
    payload = {"language": language}
    resp = await request("PATCH", f"/api/users/{telegram_id}", json=payload)
    return resp.json() if resp.status_code in (200, 201) else []

async def get_user_data(telegram_id):
    resp = await request("GET", f"/api/users/{telegram_id}")
    return resp.json() if resp.status_code == 200 else []
