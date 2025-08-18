from flask import Flask, render_template, url_for, request

from src.account_logic import forget_pwd, parse_username

app = Flask(__name__)


@app.route("/")
def login():
    return render_template("login.html", title="Login")


@app.route("/forgot")
def forgot():
    return render_template("forgot_password.html", title="Forgot Password")


@app.route("/newstudent")
def contact():
    return render_template("new_student.html", title="Contact")


@app.post("/forgot-password")
def forgot_pwd():
    username = request.form.get("username")
    forget_pwd(username)
    return render_template("login.html", title="Login")


@app.post("/create")
def create_username():
    email = request.form.get("email")
    parse_username(email)


if __name__ == "__main__":
    app.run(debug=True)
