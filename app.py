
from flask import (
    Flask, render_template, url_for, request,
    session, redirect, flash, abort
)
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

from auth import auth, init_auth_db, get_db


app = Flask(__name__)

@app.after_request
def set_charset(response):
    if response.content_type.startswith("text/html"):
        response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response

app.config["SECRET_KEY"] = os.environ.get(
    "FLASK_SECRET_KEY",
    "dev-only-change-this-secret-before-deployment"
)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

app.register_blueprint(auth)


# Модель статьи
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    intro = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<Title %r>' % self.id


# Главная страница
@app.route('/')
@app.route('/home')
def index():
    return render_template('index.html')


# Поиск напарников
@app.route('/partners.html')
def partners():
    query = request.args.get("q", "").strip().casefold()
    specialization = request.args.get("specialization", "")
    experience = request.args.get("experience", "")
    mode = request.args.get("mode", "")
    language = request.args.get("language", "")
    project_type = request.args.get("project_type", "")

    partners_data = [
        {
            "name": "Алексей",
            "role": "Frontend-разработчик",
            "specialization": "Frontend",
            "skills": "HTML, CSS, JavaScript",
            "experience": "Начинающий",
            "mode": "Онлайн",
            "languages": ["JavaScript"],
            "project_type": "Веб-сайт",
            "project": "Создание современного сайта"
        },
        {
            "name": "Мария",
            "role": "UI/UX дизайнер",
            "specialization": "UI/UX",
            "skills": "Figma, Photoshop",
            "experience": "Средний",
            "mode": "Онлайн",
            "languages": [],
            "project_type": "Дизайн",
            "project": "Дизайн мобильного приложения"
        },
        {
            "name": "Иван",
            "role": "Backend-разработчик",
            "specialization": "Backend",
            "skills": "Python, Flask, Django",
            "experience": "Опытный",
            "mode": "Офлайн",
            "languages": ["Python"],
            "project_type": "Telegram-бот",
            "project": "Разработка Telegram-бота"
        },
        {
            "name": "Денис",
            "role": "Mobile-разработчик",
            "specialization": "Mobile",
            "skills": "Flutter, Android, Dart",
            "experience": "Средний",
            "mode": "Онлайн",
            "languages": ["Dart", "Java"],
            "project_type": "Мобильное приложение",
            "project": "Разработка мобильного приложения"
        },
        {
            "name": "София",
            "role": "QA-инженер",
            "specialization": "QA",
            "skills": "Тестирование, Selenium",
            "experience": "Начинающий",
            "mode": "Онлайн",
            "languages": ["Python", "Java"],
            "project_type": "Веб-сайт",
            "project": "Тестирование веб-приложения"
        },
        {
            "name": "Максим",
            "role": "DevOps-инженер",
            "specialization": "DevOps",
            "skills": "Docker, Linux, CI/CD",
            "experience": "Опытный",
            "mode": "Офлайн",
            "languages": ["Python"],
            "project_type": "Веб-сайт",
            "project": "Автоматизация развёртывания"
        },
        {
            "name": "Анна",
            "role": "Fullstack-разработчик",
            "specialization": "Fullstack",
            "skills": "Python, JavaScript, React",
            "experience": "Средний",
            "mode": "Онлайн",
            "languages": ["Python", "JavaScript"],
            "project_type": "Веб-сайт",
            "project": "Создание веб-сервиса"
        }
    ]

    filtered_partners = []

    for partner in partners_data:
        if query:
            searchable = " ".join([
                partner["name"],
                partner["role"],
                partner["skills"],
                partner["project"]
            ]).casefold()

            if query not in searchable:
                continue

        if specialization and partner["specialization"] != specialization:
            continue

        if experience and partner["experience"] != experience:
            continue

        if mode and partner["mode"] != mode:
            continue

        if language and language not in partner["languages"]:
            continue

        if project_type and partner["project_type"] != project_type:
            continue

        filtered_partners.append(partner)

    return render_template(
        "partners.html",
        partners=filtered_partners,
        query=request.args.get("q", ""),
        specialization=specialization,
        experience=experience,
        mode=mode,
        language=language,
        project_type=project_type
    )


# Страница «О нас»
@app.route('/about')
def about():
    return render_template('about.html')


# Редактирование своего профиля
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Сначала войди в аккаунт.', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        profession = request.form.get('profession', '').strip()
        skills = request.form.get('skills', '').strip()
        experience = request.form.get('experience', '').strip()
        about_text = request.form.get('about', '').strip()
        portfolio_url = request.form.get('portfolio_url', '').strip()
        projects = request.form.get('projects', '').strip()

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO profiles
                    (user_id, full_name, profession, skills,
                     experience, about, portfolio_url, projects)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    full_name = excluded.full_name,
                    profession = excluded.profession,
                    skills = excluded.skills,
                    experience = excluded.experience,
                    about = excluded.about,
                    portfolio_url = excluded.portfolio_url,
                    projects = excluded.projects
                """,
                (
                    user_id, full_name, profession, skills,
                    experience, about_text, portfolio_url, projects
                )
            )
            profiles = conn.fetchall()

        flash('Профиль успешно сохранён!', 'success')
        return redirect(url_for('profile'))

    with get_db() as conn:
        profile_data = conn.execute(
            'SELECT * FROM profiles WHERE user_id = ?',
            (user_id,)
        ).fetchone()

        if not profile_data:
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
        username=session.get('username', '')
    )


# Публичный профиль пользователя
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


# Обработка предложения о сотрудничестве
@app.route('/collaborate/<int:user_id>', methods=['POST'])
def collaborate(user_id):
    if 'user_id' not in session:
        flash('Сначала войди в аккаунт.', 'error')
        return redirect(url_for('auth.login'))

    current_user_id = session['user_id']

    if current_user_id == user_id:
        flash(
            'Нельзя предложить сотрудничество самому себе.',
            'error'
        )
        return redirect(
            url_for('user_profile', user_id=user_id)
        )

    message = request.form.get('message', '').strip()

    if not message:
        flash('Напиши сообщение перед отправкой.', 'error')
        return redirect(
            url_for('user_profile', user_id=user_id)
        )

    # Пока проверяем форму, но сообщение в базу не сохраняем.
    flash(
        'Форма работает! Сохранение предложений добавим следующим шагом.',
        'success'
    )

    return redirect(
        url_for('user_profile', user_id=user_id)
    )


# Инициализация базы авторизации
init_auth_db()


if __name__ == "__main__":
    app.run(debug=True)
