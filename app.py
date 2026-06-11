import os
import secrets
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug import Response
from werkzeug.security import check_password_hash

import db
import sanitizer

app = Flask(__name__)
app.config["SECRET_KEY"] = secrets.token_hex(64)


def _verify_key(password: str) -> bool:
    load_dotenv()
    hashed = os.getenv("ADMIN_KEY_HASH")
    if hashed is None:
        return False
    return check_password_hash(hashed, password)


def is_mobile() -> bool:
    ua = request.headers.get("User-Agent", "").lower()
    return any(x in ua for x in ["iphone", "android", "mobile", "ipad"])


def is_legacy() -> bool:
    return session.get("legacy", False)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("manage"))
        return f(*args, **kwargs)

    return decorated


@app.route("/")
def index() -> str:
    mobile = is_mobile()
    legacy = is_legacy()
    if legacy:
        return redirect(url_for("home"))
    return render_template(
        "index.html" if mobile else "desktop.html", mobile=mobile, legacy=legacy
    )


@app.route("/home")
def home():
    return render_template("index.html", mobile=is_mobile(), legacy=is_legacy())


@app.route("/legacy")
def legacy_enter():
    session["legacy"] = True
    return redirect(url_for("home"))


@app.route("/legacy/exit")
def legacy_exit():
    session.pop("legacy", None)
    return redirect(url_for("index"))


@app.route("/writings")
def writings():
    return render_template(
        "writings.html",
        mobile=is_mobile(),
        legacy=is_legacy(),
        content=db.get_all("writings"),
    )


@app.route("/messages")
def messages():
    return render_template(
        "messages.html",
        mobile=is_mobile(),
        legacy=is_legacy(),
        content=db.get_all("messages"),
    )


@app.route("/read/<int:post_id>")
def read(post_id: int) -> str:
    return render_template(
        "read.html",
        mobile=is_mobile(),
        legacy=is_legacy(),
        post=db.get_post("writings", post_id),
    )


@app.route("/contact")
def contact() -> str:
    return render_template("contact.html", legacy=is_legacy(), mobile=is_mobile())


@app.route("/create-messages", methods=["GET", "POST"])
def create_messages() -> Response | str:

    if request.method == "POST":
        username: str = request.form.get("username", "").strip()
        content: str = request.form.get("content", "").strip()
        safe_content = sanitizer.sanitize(content)
        db.create_post("messages", username, safe_content)
        return redirect(url_for("messages"))

    return render_template(
        "create_messages.html", legacy=is_legacy(), mobile=is_mobile()
    )


@app.route("/manage", methods=["GET", "POST"])
def manage():
    if request.method == "POST":
        action: str | None = request.form.get("action")
        if action == "login":
            password: str = request.form.get("password", "")
            if _verify_key(password):
                session["admin"] = True
                return redirect(url_for("manage"))
            return render_template(
                "manage.html", authenticated=False, error="Incorrect password."
            )

    if not session.get("admin"):
        return render_template("manage.html", authenticated=False, error=None)

    if request.method == "POST":
        action: str | None = request.form.get("action")

        if action == "new_writing":
            username: str = request.form.get("username", "").strip()
            content: str = request.form.get("content", "").strip()
            safe_content = sanitizer.sanitize(content)
            db.create_post("writings", username, safe_content)
            return redirect(url_for("manage"))

    return render_template(
        "manage.html",
        authenticated=True,
        messages=db.get_all("messages"),
        writings=db.get_all("writings"),
    )


@app.route("/manage/logout")
def manage_logout():
    session.pop("admin", None)
    return redirect(url_for("index"))


@app.route("/delete/<table>/<int:post_id>", methods=["POST"])
@admin_required
def delete_post(table: str, post_id: int):
    if table not in ("messages", "writings"):
        return redirect(url_for("manage"))
    db.delete_post(table, post_id)
    return redirect(url_for("manage"))


@app.route("/course/<name>")
def course_page(name: str):
    return render_template(
        f"courses/{name}.html", legacy=is_legacy(), mobile=is_mobile()
    )


@app.route("/courses")
def courses():
    return render_template("courses.html", legacy=is_legacy(), mobile=is_mobile())


if __name__ == "__main__":
    db.create_table()
    app.run(debug=False)
