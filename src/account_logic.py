from datetime import datetime

import requests

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
