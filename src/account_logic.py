import os
import re
import time
from datetime import datetime
import requests

SERVER = os.getenv("KEYCLOAK_BASE_URL", "http://10.10.124.59:7080")
REALM = os.getenv("KEYCLOAK_REALM", "master")
ADMIN_TOKEN = os.getenv("KEYCLOAK_ADMIN_TOKEN")


def keycloak_admin_token():
    url = f"{SERVER}/realms/{REALM}/protocol/openid-connect/token"
    body = {
        "client_id": "admin-cli",
        "username": "admin",
        "password": "admin",
        "grant_type": "password"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    print(f"[TOKEN] POST {url}")
    print(f"[TOKEN] body: client_id={body['client_id']}, username={body['username']}, "
          f"password={'***'}, grant_type={body['grant_type']}")

    response = requests.post(url, data=body, headers=headers, timeout=10)
    print(f"[TOKEN] status={response.status_code}")
    # print a short preview of response body
    print(f"[TOKEN] resp: {response.text[:300]}")

    response.raise_for_status()

    data = response.json()
    token = data["access_token"]
    expires_in = int(data.get("expires_in", 300))

    os.environ["KEYCLOAK_ADMIN_TOKEN"] = token
    os.environ["KEYCLOAK_ADMIN_TOKEN_EXPIRES_AT"] = str(int(time.time()) + expires_in)

    print(f"[TOKEN] saved env KEYCLOAK_ADMIN_TOKEN (len={len(token)})")
    print(f"[TOKEN] expires_in={expires_in}s")
    return token


def get_admin_token_cached():
    exp = int(os.getenv("KEYCLOAK_ADMIN_TOKEN_EXPIRES_AT", "0"))
    now = int(time.time())
    if exp - 30 > now:
        tok = os.getenv("KEYCLOAK_ADMIN_TOKEN")
        if tok:
            print(f"[TOKEN] using cached token (seconds left={exp - now})")
            return tok
        else:
            print("[TOKEN] exp set but token missing in env → refreshing")
    else:
        print("[TOKEN] no valid cached token → refreshing")
    return keycloak_admin_token()


def auth_headers():
    token = os.getenv("KEYCLOAK_ADMIN_TOKEN")
    if not token:
        print("[AUTH] KEYCLOAK_ADMIN_TOKEN not set. Call keycloak_admin_token() first.")
        raise RuntimeError("KEYCLOAK_ADMIN_TOKEN not set. Call keycloak_admin_token() first.")
    return {"Authorization": f"Bearer {token}"}


def get_user(username: str):
    try:
        url = f"{os.getenv('KEYCLOAK_BASE_URL', 'http://10.10.124.59:7080')}/admin/realms/{os.getenv('KEYCLOAK_REALM', 'master')}/users"
        params = {"username": username, "exact": "true"}
        headers = auth_headers()

        print(f"[GET_USER] GET {url} params={params}")
        r = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"[GET_USER] status={r.status_code}")
        print(f"[GET_USER] resp: {r.text[:300]}")
        r.raise_for_status()

        users = r.json() or []
        if users:
            print(f"[GET_USER] found user id={users[0].get('id')}")
            return users[0]
        print("[GET_USER] user not found")
        return None

    except requests.RequestException as e:
        print("[GET_USER] error:", e)
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


def create_user_from_email(email: str):
    get_admin_token_cached()

    username = parse_username(email)
    if isinstance(username, str) and username.lower().startswith("error:"):
        print(f"[CREATE_FROM_EMAIL] invalid email: {username}")
        return None

    existing = get_user(username)
    if existing:
        print(f"[CREATE_FROM_EMAIL] user already exists id={existing.get('id')}")
        return existing

    base = os.getenv('KEYCLOAK_BASE_URL', SERVER)
    realm = os.getenv('KEYCLOAK_REALM', REALM)
    url = f"{base}/admin/realms/{realm}/users"
    headers = {**auth_headers(), "Content-Type": "application/json"}
    payload = {"username": username, "email": email, "enabled": True}

    print(f"[CREATE_FROM_EMAIL] POST {url}")
    print(f"[CREATE_FROM_EMAIL] payload={payload}")
    r = requests.post(url, headers=headers, json=payload, timeout=10)
    print(f"[CREATE_FROM_EMAIL] status={r.status_code}")
    print(f"[CREATE_FROM_EMAIL] resp: {r.text[:300]}")

    if r.status_code in (201, 409):
        u = get_user(username)
        print(f"[CREATE_FROM_EMAIL] created/loaded user id={u.get('id') if u else None}")
        return u

    try:
        r.raise_for_status()
    except requests.RequestException as e:
        print("[CREATE_FROM_EMAIL] error:", e)
    return None


def forget_pwd(username: str):
    get_admin_token_cached()
    user = get_user(username)
    if not user:
        print("[FORGOT] user not found; treating as success to avoid leakage")
        return True
    user_id = user.get("id")

    try:
        url = f"{os.getenv('KEYCLOAK_BASE_URL', 'http://10.10.124.59:7080')}/admin/realms/{os.getenv('KEYCLOAK_REALM', 'master')}/users/{user_id}/execute-actions-email"
        headers = {**auth_headers(), "Content-Type": "application/json"}
        params = {"lifespan": 3600}
        body = ["UPDATE_PASSWORD"]

        print(f"[FORGOT] PUT {url} params={params} body={body}")
        r = requests.put(url, headers=headers, params=params, json=body, timeout=10)
        print(f"[FORGOT] status={r.status_code}")
        print(f"[FORGOT] resp: {r.text[:300]}")
        r.raise_for_status()

        ok = r.status_code in (200, 204)
        print(f"[FORGOT] success={ok}")
        return ok

    except requests.RequestException as e:
        print("[FORGOT] error:", e)
        return False


def update_password(username, new_password):
    user = get_user(username)
    if not user:
        return False, "no user of that name"

    user_id = user["id"]
    url = f"{SERVER}/admin/realms/{REALM}/users/{user_id}/reset-password"
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "type": "password",
        "value": new_password,
        "temporary": False
    }
    r = requests.put(url, headers=headers, json=payload)
    if r.status_code == 204:
        return True, "password updated successfully"
    else:
        return False, "password update failed"


def change_password_flow(username, new_password, confirm_password):
    if new_password != confirm_password:
        return False, "passwords do not match"

    valid, msg = validate_password(new_password)
    if not valid:
        return False, msg

    success, msg = update_password(username, new_password)
    return success, msg


# detect first time password needs updating
def is_password_temporary(username):
    user = get_user(username)
    if not user:
        return False
    return "UPDATE_PASSWORD" in user.get("requiredActions", [])


# we should use keycloak itself for password criteria validation but here is some code
def validate_password(password):
    if len(password) < 8:
        return False, "password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "password must contain at least one uppercase letter"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "password must contain at least one special character"
    return True, "password is valid"
