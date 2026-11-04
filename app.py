from flask import Flask, render_template, url_for, request, session, redirect, flash, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
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


@app.route('/')
@app.route('/home')
def index():
    return render_template('index.html')


# ПОИСК НАПАРНИКОВ
@app.route('/partners.html')
def partners():

    query = clean(request.args.get('q'))
    specialization = clean(request.args.get('specialization'))
    experience = clean(request.args.get('experience'))
    language = clean(request.args.get('language'))
    project_type = clean(request.args.get('project_type'))

    with get_db() as conn:
        rows = conn.execute('''
            SELECT
                users.id AS id,
                users.username AS username,
                profiles.full_name AS full_name,
                profiles.profession AS profession,
                profiles.skills AS skills,
                profiles.experience AS experience,
                profiles.about AS about,
                profiles.portfolio_url AS portfolio_url,
                profiles.projects AS projects,
                profiles.avatar AS avatar
            FROM users
            LEFT JOIN profiles ON profiles.user_id = users.id
            ORDER BY users.created_at DESC, users.id DESC
        ''').fetchall()

    found = []
    current_user_id = session.get('user_id')

    for row in rows:

        if current_user_id is not None and row['id'] == current_user_id:
            continue

        name = clean(row['full_name']) or clean(row['username'])
        role = clean(row['profession']) or 'Специализация не указана'
        skills = clean(row['skills'])
        exp = clean(row['experience'])
        about_text = clean(row['about'])
        projects = clean(row['projects'])
        portfolio = clean(row['portfolio_url'])

        if not any([
            clean(row['full_name']),
            clean(row['profession']),
            skills,
            exp,
            about_text,
            projects,
            portfolio
        ]):
            continue

        searchable = norm(' '.join([
            name, role, skills, exp, about_text, projects
        ]))

        if query and norm(query) not in searchable:
            continue

        if specialization and norm(specialization) not in norm(role):
            continue

        if experience and norm(exp) != norm(experience):
            continue

        # Поиск языка среди всех навыков пользователя
        if language:
            skill_values = [
                norm(item)
                for item in split_values(skills)
            ]

            if norm(language) not in skill_values:
                continue

        if project_type and norm(project_type) not in norm(projects):
            continue

        found.append({
            'id': row['id'],
            'name': name,
            'role': role,
            'skills': skills or 'Пока не указаны',
            'experience': exp or 'Не указан',
            'project': projects or 'Пока не указан',
            'about': about_text,
            'portfolio_url': portfolio,
            'avatar': clean(row['avatar'])
        })

    return render_template(
        'partners.html',
        partners=found,
        query=query,
        specialization=specialization,
        experience=experience,
        language=language,
        project_type=project_type
    )


@app.route('/about')
def about():
    return render_template('about.html')


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
            conn.execute('''
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
            ''', (
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
        username=session.get('username', '')
    )


# ПУБЛИЧНЫЙ ПРОФИЛЬ ДРУГОГО ПОЛЬЗОВАТЕЛЯ
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


init_auth_db()


if __name__ == '__main__':
    app.run(debug=True)