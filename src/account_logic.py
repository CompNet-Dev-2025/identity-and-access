import os
from datetime import datetime
import requests

SERVER = os.getenv("KEYCLOAK_BASE_URL", "")
REALM = os.getenv("KEYCLOAK_REALM", "")
ADMIN_TOKEN = os.getenv("KEYCLOAK_ADMIN_TOKEN", "")


def _auth_headers():
    if not (SERVER and REALM and ADMIN_TOKEN):
        raise RuntimeError("Keycloak config missing (SERVER/REALM/TOKEN).")
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def get_user(username: str):
    try:
        r = requests.get(
            f"{SERVER}/admin/realms/{REALM}/users",
            headers=_auth_headers(),
            params={"username": username, "exact": "true"},
            timeout=10,
        )
        r.raise_for_status()
        users = r.json() or []
        return users[0] if users else None
    except requests.RequestException:
        return None


def parse_username(email: str):
    if "@" not in email:
        return "error: invalid email address"
    local, _, domain = email.partition("@")
    domain = domain.lower().strip()
    if domain != "torontomu.ca":
        return "error: please use your @torontomu.ca email"
    yy = f"{datetime.now().year % 100:02d}"
    return f"{local}{yy}"


def forget_pwd(username: str) -> bool:
    user = get_user(username)
    if not user:
        return True
    user_id = user.get("id")
    try:
        r = requests.put(
            f"{SERVER}/admin/realms/{REALM}/users/{user_id}/execute-actions-email",
            headers={**_auth_headers(), "Content-Type": "application/json"},
            params={"lifespan": 3600},
            json=["UPDATE_PASSWORD"],
            timeout=10,
        )
        return r.status_code in (200, 204)
    except requests.RequestException:
        return False
