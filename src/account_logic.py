from datetime import datetime

import requests
import re 

SERVER = "NEED FROM INFRASTRUCTURE TEAM"
REALM = "NEED FROM INFRASTRUCTURE"
ADMIN_TOKEN = "NEED FROM INFRASTRUCTURE"


def get_user(username):
    url = f"{SERVER}/admin/realms/{REALM}/users"
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    params = {"username": username, "exact": "true"}
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    users = r.json()
    if not users:
        return None
    return users[0]


def parse_username(email):
    username = email.split("@")[0]
    domain = email.split("@")[1]

    if domain != "torontomu.ca":
        return "wrong domain"

    current_year = datetime.now().year
    last_two_digits = current_year % 100
    username += str(last_two_digits)

    return username


def reset_pwd(username):
    user = get_user(username)
    if user:
        user_id = user["id"]
    else:
        return "no user of that name"

    url = f"{SERVER}/admin/realms/{REALM}/users/{user_id}/execute-actions-email"
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}",
               "Content-Type": "application/json"}
    params = {"lifespan": 3600}
    r = requests.put(url, headers=headers, params=params, json=["UPDATE_PASSWORD"])

    if r.status_code == 200:
        return "password reset email sent"
    else:
        return "password reset email not sent"


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

#detect first time password needs updating 
def is_password_temporary(username):
    user = get_user(username)
    if not user:
        return False
    return "UPDATE_PASSWORD" in user.get("requiredActions", [])

#we should use keycloak itself for password criteria validation but here is some code  
def validate_password(password):
    if len(password) < 8:
        return False, "password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "password must contain at least one uppercase letter"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "password must contain at least one special character"
    return True, "password is valid"