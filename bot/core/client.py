import datetime
import logging
import httpx
from ..config import BACKEND_URL, BACKEND_USERNAME, BACKEND_PASSWORD

logger = logging.getLogger(__name__)
http_client = httpx.AsyncClient(timeout=15.0)

ACCESS_TOKEN = None
REFRESH_TOKEN = None
TOKEN_EXPIRES = None

async def get_jwt_token():
    global ACCESS_TOKEN, REFRESH_TOKEN, TOKEN_EXPIRES

    if ACCESS_TOKEN and TOKEN_EXPIRES and TOKEN_EXPIRES > datetime.datetime.utcnow():
        return ACCESS_TOKEN

    try:
        resp = await http_client.post(
            f"{BACKEND_URL}/api/token/",
            json={"username": BACKEND_USERNAME, "password": BACKEND_PASSWORD},
        )
        if resp.status_code == 200:
            data = resp.json()
            ACCESS_TOKEN = data["access"]
            REFRESH_TOKEN = data["refresh"]
            TOKEN_EXPIRES = datetime.datetime.utcnow() + datetime.timedelta(days=30)
            return ACCESS_TOKEN
        logger.error("JWT error: %s", resp.text)
    except Exception as e:
        logger.exception("get_jwt_token exception: %s", e)
    return None


async def request(method: str, url: str, **kwargs):
    token = await get_jwt_token()
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return await http_client.request(method, f"{BACKEND_URL}{url}", headers=headers, **kwargs)
