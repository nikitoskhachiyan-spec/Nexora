
import sqlite3
import re
from pathlib import Path

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash
)
from werkzeug.security import generate_password_hash, check_password_hash

auth = Blueprint("auth", __name__)

DB_PATH = Path(__file__).resolve().parent / "users.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn




def init_auth_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT DEFAULT '',
                profession TEXT DEFAULT '',
                skills TEXT DEFAULT '',
                experience TEXT DEFAULT '',
                about TEXT DEFAULT '',
                portfolio_url TEXT DEFAULT '',
                avatar TEXT DEFAULT '',
                projects TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Добавляем projects в существующую таблицу,
        # если колонка ещё не существует.
        columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(profiles)"
            ).fetchall()
        }

        if "projects" not in columns:
            conn.execute(
                "ALTER TABLE profiles ADD COLUMN projects TEXT DEFAULT ''"
            )





@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if len(username) < 3 or len(username) > 30:
            flash("Имя должно содержать от 3 до 30 символов.", "error")
            return render_template("register.html")

        if not re.fullmatch(r"[A-Za-zА-Яа-яЁё0-9_-]+", username):
            flash("В имени разрешены буквы, цифры, _ и -.", "error")
            return render_template("register.html")

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Введи корректный email.", "error")
            return render_template("register.html")

        if len(password) < 8:
            flash("Пароль должен содержать минимум 8 символов.", "error")
            return render_template("register.html")

        if password != confirm:
            flash("Пароли не совпадают.", "error")
            return render_template("register.html")

        try:
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO users
                       (username, email, password_hash)
                       VALUES (?, ?, ?)""",
                    (username, email, generate_password_hash(password))
                )
        except sqlite3.IntegrityError:
            flash("Это имя или email уже заняты.", "error")
            return render_template("register.html")

        flash("Регистрация успешна! Теперь войди в аккаунт.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("index"))

        flash("Неверный email или пароль.", "error")

    return render_template("login.html")


@auth.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))
