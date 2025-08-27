from flask import Flask, render_template, request, redirect, url_for, flash
from src.account_logic import forget_pwd, parse_username, create_user_from_email

app = Flask(__name__)


@app.route("/")
def index():
    return redirect(url_for("login"))


@app.get("/login")
def login():
    return render_template("login.html", title="Login")


@app.get("/forgot")
def forgot():
    return render_template("forgot_password.html", title="Forgot Password")


@app.get("/new_student")
def contact():
    return render_template("new_student.html", title="Contact")


# POST: send reset email
@app.post("/forgot-password")
def forgot_password():
    username = request.form.get("username", "").strip()
    if not username:
        return redirect(url_for("forgot"))
    forget_pwd(username)
    return redirect(url_for("login"))


@app.post("/create")
def create_username():
    email = request.form.get("email", "").strip()
    create_user_from_email(email)
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
