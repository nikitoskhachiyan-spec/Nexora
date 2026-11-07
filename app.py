from flask import Flask, render_template, url_for, request, session, redirect, flash, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
import os

from auth import auth, init_auth_db, get_db


app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get(
    'FLASK_SECRET_KEY',
    'dev-only-change-this-secret-before-deployment'
)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
app.register_blueprint(auth)


@app.context_processor
def notification_context():
    unread_count = 0
    unread_sender = None

    if 'user_id' in session:
        with get_db() as conn:
            unread_count = conn.execute("""
                SELECT COUNT(*)
                FROM private_messages
                WHERE receiver_id = ?
                AND is_read = 0
            """, (session['user_id'],)).fetchone()[0]

            unread_sender = conn.execute("""
                SELECT m.sender_id, u.username
                FROM private_messages m
                JOIN users u ON u.id = m.sender_id
                WHERE m.receiver_id = ?
                AND m.is_read = 0
                ORDER BY m.id DESC
                LIMIT 1
            """, (session['user_id'],)).fetchone()

    return {
        'unread_count': unread_count,
        'unread_sender': unread_sender
    }


@app.after_request
def set_charset(response):
    if response.content_type and response.content_type.startswith('text/html'):
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    intro = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Article {self.id}>'


def clean(value):
    return (value or '').strip()


def norm(value):
    return clean(value).casefold().replace('ё', 'е')


def experience_matches(saved_value, selected_value):
    return norm(saved_value) == norm(selected_value)


def split_values(value):
    return [
        part.strip()
        for part in (value or '').replace(';', ',').split(',')
        if part.strip()
    ]


PROJECT_OPTIONS = [
    "API",
    "CRM-система",
    "Discord-бот",
    "ERP-система",
    "Telegram-бот",
    "UI/UX-дизайн",
    "Банковское приложение",
    "Блог",
    "Веб-приложение",
    "Веб-сайт",
    "Видеоплатформа",
    "Десктопное приложение",
    "Дизайн интерфейса",
    "Интернет-магазин",
    "Компьютерная игра",
    "Лендинг",
    "Мобильное приложение",
    "Музыкальный сервис",
    "Новостной портал",
    "Образовательная платформа",
    "Онлайн-курс",
    "Портфолио",
    "Сервис бронирования",
    "Сервис доставки",
    "Социальная сеть",
    "Система управления базой данных",
    "Финансовое приложение",
    "Форум",
    "Чат-бот",
    "Другое"
]


# ГЛАВНАЯ СТРАНИЦА
@app.route('/')
@app.route('/home')
def index():
    return render_template('index.html')


# ПОИСК НАПАРНИКОВ
@app.route('/partners.html')
def partners():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    search = norm(request.args.get('search', ''))
    specialization = clean(request.args.get('specialization'))
    experience = clean(request.args.get('experience'))
    language = clean(request.args.get('language'))
    project = clean(request.args.get('project'))

    current_user_id = session['user_id']

    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                u.id,
                u.username,
                p.full_name,
                p.profession AS specialization,
                p.skills,
                p.experience,
                p.projects AS project
            FROM users u
            LEFT JOIN profiles p ON p.user_id = u.id
            WHERE u.id != ?
            ORDER BY u.username COLLATE NOCASE
        """, (current_user_id,)).fetchall()

    users = [dict(row) for row in rows]

    if search:
        users = [
            user for user in users
            if any(
                search in norm(user.get(field))
                for field in (
                    'username',
                    'full_name',
                    'specialization',
                    'skills',
                    'project'
                )
            )
        ]

    if specialization:
        users = [
            user for user in users
            if norm(user.get('specialization')) == norm(specialization)
        ]

    if experience:
        users = [
            user for user in users
            if experience_matches(user.get('experience'), experience)
        ]

    if language:
        users = [
            user for user in users
            if any(
                norm(skill) == norm(language)
                for skill in split_values(user.get('skills'))
            )
        ]

    if project:
        users = [
            user for user in users
            if norm(user.get('project')) == norm(project)
        ]

    all_users = [dict(row) for row in rows]

    specializations = sorted({
        user['specialization']
        for user in all_users
        if user.get('specialization')
    }, key=str.casefold)

    languages = sorted({
        skill
        for user in all_users
        for skill in split_values(user.get('skills'))
    }, key=str.casefold)

    projects = sorted({
        user['project']
        for user in all_users
        if user.get('project')
    }, key=str.casefold)

    return render_template(
        'partners.html',
        users=users,
        specializations=specializations,
        languages=languages,
        projects=projects
    )


# О ПРОЕКТЕ
@app.route('/about')
def about():
    return render_template('about.html')


# ЛИЧНЫЕ СООБЩЕНИЯ
@app.route('/private_chat/<int:user_id>', methods=['GET', 'POST'])
def private_chat(user_id):

    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    current_user_id = session['user_id']

    with get_db() as conn:
        recipient = conn.execute(
            'SELECT id, username FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()

        if recipient is None:
            abort(404)

        if user_id == current_user_id:
            flash('Нельзя отправить сообщение самому себе.')
            return redirect(url_for('partners'))

        conn.execute("""
            UPDATE private_messages
            SET is_read = 1
            WHERE sender_id = ?
            AND receiver_id = ?
        """, (user_id, current_user_id))

        if request.method == 'POST':
            content = clean(request.form.get('content'))

            if content:
                conn.execute("""
                    INSERT INTO private_messages
                        (sender_id, receiver_id, text)
                    VALUES (?, ?, ?)
                """, (current_user_id, user_id, content))

            return redirect(url_for('private_chat', user_id=user_id))

        messages = conn.execute("""
            SELECT
                m.id,
                m.sender_id,
                m.receiver_id,
                m.text AS content,
                m.created_at,
                u.username AS sender_username
            FROM private_messages m
            JOIN users u ON u.id = m.sender_id
            WHERE
                (m.sender_id = ? AND m.receiver_id = ?)
                OR
                (m.sender_id = ? AND m.receiver_id = ?)
            ORDER BY m.id ASC
        """, (
            current_user_id,
            user_id,
            user_id,
            current_user_id
        )).fetchall()

    return render_template(
        'private_chat.html',
        recipient=recipient,
        messages=messages,
        current_user_id=current_user_id
    )


# ОБЩИЙ ЧАТ
@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    return render_template('chat.html')


@app.route('/api/chat/messages')
def get_messages():
    if 'user_id' not in session:
        return jsonify({'error': 'Необходимо войти'}), 401

    after_id = request.args.get('after', 0, type=int)

    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, username, text, created_at
            FROM messages
            WHERE id > ?
            ORDER BY id ASC
            LIMIT 100
        """, (after_id,)).fetchall()

    return jsonify([
        {
            'id': row['id'],
            'username': row['username'],
            'text': row['text'],
            'created_at': row['created_at']
        }
        for row in rows
    ])


@app.route('/api/chat/messages', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Необходимо войти'}), 401

    data = request.get_json(silent=True) or {}
    message_text = clean(data.get('text'))

    if not message_text:
        return jsonify({'error': 'Сообщение пустое'}), 400

    if len(message_text) > 1000:
        return jsonify({'error': 'Максимум 1000 символов'}), 400

    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO messages (user_id, username, text)
            VALUES (?, ?, ?)
        """, (
            session['user_id'],
            session['username'],
            message_text
        ))

        message_id = cursor.lastrowid

        row = conn.execute("""
            SELECT id, username, text, created_at
            FROM messages
            WHERE id = ?
        """, (message_id,)).fetchone()

    return jsonify({
        'id': row['id'],
        'username': row['username'],
        'text': row['text'],
        'created_at': row['created_at']
    }), 201


# ЛИЧНЫЙ ПРОФИЛЬ
@app.route('/profile', methods=['GET', 'POST'])
def profile():

    if 'user_id' not in session:
        flash('Сначала войди в аккаунт.', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    if request.method == 'POST':
        full_name = clean(request.form.get('full_name'))
        profession = clean(request.form.get('profession'))
        skills = ", ".join(request.form.getlist("skills"))
        experience = clean(request.form.get('experience'))
        about_text = clean(request.form.get('about'))
        portfolio_url = clean(request.form.get('portfolio_url'))
        projects = clean(request.form.get('projects'))

        with get_db() as conn:
            conn.execute("""
                INSERT INTO profiles
                    (user_id, full_name, profession, skills, experience,
                     about, portfolio_url, projects)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)

                ON CONFLICT(user_id) DO UPDATE SET
                    full_name = excluded.full_name,
                    profession = excluded.profession,
                    skills = excluded.skills,
                    experience = excluded.experience,
                    about = excluded.about,
                    portfolio_url = excluded.portfolio_url,
                    projects = excluded.projects
            """, (
                user_id,
                full_name,
                profession,
                skills,
                experience,
                about_text,
                portfolio_url,
                projects
            ))

        flash('Профиль успешно сохранён!', 'success')
        return redirect(url_for('profile'))

    with get_db() as conn:
        profile_data = conn.execute(
            'SELECT * FROM profiles WHERE user_id = ?',
            (user_id,)
        ).fetchone()

        if profile_data is None:
            conn.execute(
                'INSERT INTO profiles (user_id) VALUES (?)',
                (user_id,)
            )

            profile_data = conn.execute(
                'SELECT * FROM profiles WHERE user_id = ?',
                (user_id,)
            ).fetchone()

    return render_template(
        'profile.html',
        profile=profile_data,
        username=session.get('username', ''),
        project_options=PROJECT_OPTIONS
    )


# ПУБЛИЧНЫЙ ПРОФИЛЬ
@app.route('/user/<int:user_id>')
def user_profile(user_id):

    with get_db() as conn:
        user = conn.execute(
            'SELECT id, username FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()

        if user is None:
            abort(404)

        profile_data = conn.execute(
            'SELECT * FROM profiles WHERE user_id = ?',
            (user_id,)
        ).fetchone()

    return render_template(
        'user.html',
        user=user,
        profile=profile_data
    )


# ПРЕДЛОЖЕНИЕ СОТРУДНИЧЕСТВА
@app.route('/collaborate/<int:user_id>', methods=['POST'])
def collaborate(user_id):

    if 'user_id' not in session:
        flash('Сначала войди в аккаунт.', 'error')
        return redirect(url_for('auth.login'))

    if session['user_id'] == user_id:
        flash('Нельзя предложить сотрудничество самому себе.', 'error')
        return redirect(url_for('user_profile', user_id=user_id))

    with get_db() as conn:
        target = conn.execute(
            'SELECT id FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()

    if target is None:
        abort(404)

    message = clean(request.form.get('message'))

    if not message:
        flash('Напиши сообщение перед отправкой.', 'error')
    else:
        flash(
            'Сообщение заполнено. Сохранение предложений добавим отдельным шагом.',
            'success'
        )

    return redirect(url_for('user_profile', user_id=user_id))


# ОТПРАВКА ЖАЛОБЫ
@app.route('/report/<int:user_id>', methods=['POST'])
def submit_report(user_id):

    if 'user_id' not in session:
        flash('Сначала войди в аккаунт.', 'error')
        return redirect(url_for('auth.login'))

    reporter_id = session['user_id']

    if reporter_id == user_id:
        flash('Нельзя пожаловаться на самого себя.', 'error')
        return redirect(url_for('user_profile', user_id=user_id))

    reason = clean(request.form.get('reason'))
    description = clean(request.form.get('description'))

    allowed_reasons = [
        'Спам',
        'Оскорбления',
        'Мошенничество',
        'Неприемлемый контент',
        'Фейковый профиль',
        'Другое'
    ]

    if reason not in allowed_reasons:
        flash('Выбери причину жалобы.', 'error')
        return redirect(url_for('user_profile', user_id=user_id))

    if len(description) > 2000:
        flash('Описание слишком длинное.', 'error')
        return redirect(url_for('user_profile', user_id=user_id))

    with get_db() as conn:
        target = conn.execute(
            'SELECT id FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()

        if target is None:
            abort(404)

        conn.execute("""
            INSERT INTO reports
                (reporter_id, reported_user_id, reason, description)
            VALUES (?, ?, ?, ?)
        """, (reporter_id, user_id, reason, description))

    flash('Жалоба успешно отправлена!', 'success')
    return redirect(url_for('user_profile', user_id=user_id))


# ИНИЦИАЛИЗАЦИЯ БАЗЫ АВТОРИЗАЦИИ
init_auth_db()


# НАЗНАЧЕНИЕ АДМИНИСТРАТОРА ИЗ ПЕРЕМЕННОЙ ОКРУЖЕНИЯ
admin_username = os.environ.get("ADMIN_USERNAME", "").strip()

if admin_username:
    with get_db() as conn:
        conn.execute("""
            UPDATE users
            SET role = 'admin'
            WHERE username = ?
        """, (admin_username,))


# СОЗДАНИЕ ТАБЛИЦЫ ОБЩЕГО ЧАТА
with get_db() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


# ПРОВЕРКА АДМИНИСТРАТОРА
def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))

        with get_db() as conn:
            user = conn.execute("""
                SELECT id, username, role, is_blocked
                FROM users
                WHERE id = ?
            """, (session["user_id"],)).fetchone()

        if not user or user["is_blocked"]:
            session.clear()
            return redirect(url_for("auth.login"))

        if user["username"].lower() not in ("nikita_admine", "nekit"):
            abort(403)

        if user["role"] != "admin":
            print("ADMIN DEBUG:", dict(user))
            abort(403)

        return func(*args, **kwargs)
    return wrapper


# ПАНЕЛЬ АДМИНИСТРАТОРА
@app.route("/admin")
@admin_required
def admin_panel():

    with get_db() as conn:
        users = conn.execute("""
            SELECT id, username, email, role, is_blocked, created_at
            FROM users
            ORDER BY id DESC
        """).fetchall()

        reports = conn.execute("""
            SELECT
                reports.*,
                reporter.username AS reporter_name,
                reported.username AS reported_name
            FROM reports
            LEFT JOIN users reporter
                ON reporter.id = reports.reporter_id
            LEFT JOIN users reported
                ON reported.id = reports.reported_user_id
            ORDER BY reports.id DESC
        """).fetchall()

        stats = {
            "users": conn.execute(
                "SELECT COUNT(*) FROM users"
            ).fetchone()[0],

            "blocked": conn.execute(
                "SELECT COUNT(*) FROM users WHERE is_blocked = 1"
            ).fetchone()[0],

            "reports": conn.execute(
                "SELECT COUNT(*) FROM reports WHERE status = 'new'"
            ).fetchone()[0],

            "projects": conn.execute(
                "SELECT COUNT(*) FROM profiles WHERE projects != ''"
            ).fetchone()[0]
        }

    return render_template(
        "admin.html",
        users=users,
        reports=reports,
        stats=stats
    )


# БЛОКИРОВКА И РАЗБЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ
@app.route("/admin/user/<int:user_id>/block", methods=["POST"])
@admin_required
def admin_block_user(user_id):

    if user_id == session["user_id"]:
        flash("Нельзя заблокировать самого себя.", "error")
        return redirect(url_for("admin_panel"))

    with get_db() as conn:
        conn.execute("""
            UPDATE users
            SET is_blocked = CASE
                WHEN is_blocked = 1 THEN 0
                ELSE 1
            END
            WHERE id = ?
        """, (user_id,))

    flash("Статус пользователя изменён.", "success")
    return redirect(url_for("admin_panel"))


# ИЗМЕНЕНИЕ РОЛИ
@app.route("/admin/user/<int:user_id>/role", methods=["POST"])
@admin_required
def admin_change_role(user_id):

    if user_id == session["user_id"]:
        flash("Нельзя изменить собственную роль.", "error")
        return redirect(url_for("admin_panel"))

    role = request.form.get("role")

    if role not in ["user", "admin"]:
        abort(400)

    with get_db() as conn:
        conn.execute("""
            UPDATE users SET role = ?
            WHERE id = ?
        """, (role, user_id))

    flash("Роль пользователя изменена.", "success")
    return redirect(url_for("admin_panel"))


# УДАЛЕНИЕ ИНФОРМАЦИИ О ПРОЕКТЕ
@app.route("/admin/project/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_project(user_id):

    with get_db() as conn:
        conn.execute("""
            UPDATE profiles
            SET projects = ''
            WHERE user_id = ?
        """, (user_id,))

    flash("Информация о проекте удалена.", "success")
    return redirect(url_for("admin_panel"))


# ОБРАБОТКА ЖАЛОБЫ
@app.route("/admin/report/<int:report_id>/resolve", methods=["POST"])
@admin_required
def admin_resolve_report(report_id):

    with get_db() as conn:
        conn.execute("""
            UPDATE reports
            SET status = 'resolved'
            WHERE id = ?
        """, (report_id,))

    flash("Жалоба обработана.", "success")
    return redirect(url_for("admin_panel"))


# УДАЛЕНИЕ ЖАЛОБЫ
@app.route("/admin/report/<int:report_id>/delete", methods=["POST"])
@admin_required
def admin_delete_report(report_id):

    with get_db() as conn:
        conn.execute(
            "DELETE FROM reports WHERE id = ?",
            (report_id,)
        )

    flash("Жалоба удалена.", "success")
    return redirect(url_for("admin_panel"))


if __name__ == '__main__':
    app.run(debug=True)