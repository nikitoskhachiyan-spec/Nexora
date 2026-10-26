from flask import Flask, render_template, url_for, request, session, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from auth import auth, init_auth_db, get_db

import os
from auth import auth, init_auth_db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "FLASK_SECRET_KEY",
    "dev-only-change-this-secret-before-deployment"
)

app.register_blueprint(auth)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    intro = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<Title %r>' % self.id
@app.route('/')
@app.route('/home')
def index():
    return render_template('index.html')



@app.route("/partners.html")
def partners():
    query = request.args.get("q", "").strip().casefold()
    specialization = request.args.get("specialization", "")
    experience = request.args.get("experience", "")
    mode = request.args.get("mode", "")
    language = request.args.get("language", "")
    project_type = request.args.get("project_type", "")

    partners_data = [
        {
            "name": "РђР»РµРєСЃРµР№",
            "role": "Frontend-СЂР°Р·СЂР°Р±РѕС‚С‡РёРє",
            "specialization": "Frontend",
            "skills": "HTML, CSS, JavaScript",
            "experience": "РќР°С‡РёРЅР°СЋС‰РёР№",
            "mode": "РћРЅР»Р°Р№РЅ",
            "languages": ["JavaScript"],
            "project_type": "Р’РµР±-СЃР°Р№С‚",
            "project": "РЎРѕР·РґР°РЅРёРµ СЃРѕРІСЂРµРјРµРЅРЅРѕРіРѕ СЃР°Р№С‚Р°"
        },
        {
            "name": "РњР°СЂРёСЏ",
            "role": "UI/UX РґРёР·Р°Р№РЅРµСЂ",
            "specialization": "UI/UX",
            "skills": "Figma, Photoshop",
            "experience": "РЎСЂРµРґРЅРёР№",
            "mode": "РћРЅР»Р°Р№РЅ",
            "languages": [],
            "project_type": "Р”РёР·Р°Р№РЅ",
            "project": "Р”РёР·Р°Р№РЅ РјРѕР±РёР»СЊРЅРѕРіРѕ РїСЂРёР»РѕР¶РµРЅРёСЏ"
        },
        {
            "name": "РРІР°РЅ",
            "role": "Backend-СЂР°Р·СЂР°Р±РѕС‚С‡РёРє",
            "specialization": "Backend",
            "skills": "Python, Flask, Django",
            "experience": "РћРїС‹С‚РЅС‹Р№",
            "mode": "РћС„Р»Р°Р№РЅ",
            "languages": ["Python"],
            "project_type": "Telegram-Р±РѕС‚",
            "project": "Р Р°Р·СЂР°Р±РѕС‚РєР° Telegram-Р±РѕС‚Р°"
        },
        {
            "name": "Р”РµРЅРёСЃ",
            "role": "Mobile-СЂР°Р·СЂР°Р±РѕС‚С‡РёРє",
            "specialization": "Mobile",
            "skills": "Flutter, Android, Dart",
            "experience": "РЎСЂРµРґРЅРёР№",
            "mode": "РћРЅР»Р°Р№РЅ",
            "languages": ["Dart", "Java"],
            "project_type": "РњРѕР±РёР»СЊРЅРѕРµ РїСЂРёР»РѕР¶РµРЅРёРµ",
            "project": "Р Р°Р·СЂР°Р±РѕС‚РєР° РјРѕР±РёР»СЊРЅРѕРіРѕ РїСЂРёР»РѕР¶РµРЅРёСЏ"
        },
        {
            "name": "РЎРѕС„РёСЏ",
            "role": "QA-РёРЅР¶РµРЅРµСЂ",
            "specialization": "QA",
            "skills": "РўРµСЃС‚РёСЂРѕРІР°РЅРёРµ, Selenium",
            "experience": "РќР°С‡РёРЅР°СЋС‰РёР№",
            "mode": "РћРЅР»Р°Р№РЅ",
            "languages": ["Python", "Java"],
            "project_type": "Р’РµР±-СЃР°Р№С‚",
            "project": "РўРµСЃС‚РёСЂРѕРІР°РЅРёРµ РІРµР±-РїСЂРёР»РѕР¶РµРЅРёСЏ"
        },
        {
            "name": "РњР°РєСЃРёРј",
            "role": "DevOps-РёРЅР¶РµРЅРµСЂ",
            "specialization": "DevOps",
            "skills": "Docker, Linux, CI/CD",
            "experience": "РћРїС‹С‚РЅС‹Р№",
            "mode": "РћС„Р»Р°Р№РЅ",
            "languages": ["Python"],
            "project_type": "Р’РµР±-СЃР°Р№С‚",
            "project": "РђРІС‚РѕРјР°С‚РёР·Р°С†РёСЏ СЂР°Р·РІС‘СЂС‚С‹РІР°РЅРёСЏ"
        },
        {
            "name": "РђРЅРЅР°",
            "role": "Fullstack-СЂР°Р·СЂР°Р±РѕС‚С‡РёРє",
            "specialization": "Fullstack",
            "skills": "Python, JavaScript, React",
            "experience": "РЎСЂРµРґРЅРёР№",
            "mode": "РћРЅР»Р°Р№РЅ",
            "languages": ["Python", "JavaScript"],
            "project_type": "Р’РµР±-СЃР°Р№С‚",
            "project": "РЎРѕР·РґР°РЅРёРµ РІРµР±-СЃРµСЂРІРёСЃР°"
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



@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('РЎРЅР°С‡Р°Р»Р° РІРѕР№РґРё РІ Р°РєРєР°СѓРЅС‚.', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        profession = request.form.get('profession', '').strip()
        skills = request.form.get('skills', '').strip()
        experience = request.form.get('experience', '').strip()
        about = request.form.get('about', '').strip()
        portfolio_url = request.form.get('portfolio_url', '').strip()

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO profiles
                    (user_id, full_name, profession, skills,
                     experience, about, portfolio_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    full_name = excluded.full_name,
                    profession = excluded.profession,
                    skills = excluded.skills,
                    experience = excluded.experience,
                    about = excluded.about,
                    portfolio_url = excluded.portfolio_url
                """,
                (user_id, full_name, profession, skills,
                 experience, about, portfolio_url)
            )

        flash('РџСЂРѕС„РёР»СЊ СѓСЃРїРµС€РЅРѕ СЃРѕС…СЂР°РЅС‘РЅ!', 'success')
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



@app.route('/user/<string:name>/<int:id>')
def user(name, id):
    return "User page: " + name + " - " + str(id)

init_auth_db();

if __name__ == "__main__":
    app.run(debug=True)

