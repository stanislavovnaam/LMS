from flask import Flask, render_template, session, request, url_for, redirect

from werkzeug.security import check_password_hash, generate_password_hash

import sqlite3

from functools import wraps

DB_PATH = "database.db"
app = Flask(__name__)
app.secret_key = "super-secret-key-change-me"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@app.route("/", methods=["GET", "POST"])
def home():
    conn = get_conn()
    row = conn.execute("SELECT 1 AS ok").fetchone()
    rows = conn.execute("SELECT * FROM users")
    for r in rows:
        print(dict(r))
    conn.close()
    return render_template(
            "index.html",
            db_ok=row is not None and row["ok"] == 1,
            current_user=current_user,
        )
def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('student', 'teacher', 'manager', 'admin')),
            archived_at TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    conn.commit()
    conn.close()
    
def ensure_master():
    """Создать пользователя master (admin), если ещё нет ни одного admin."""
    conn = get_conn()
    row = conn.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1").fetchone()
    if row is not None:
        conn.close()
        return
     #password_hash = generate_password_hash(plain_password)
    #if not check_password_hash(user["password_hash"], entered_password):
        #print("Неверный пароль!")
    conn.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
        ("master", generate_password_hash("master")),
    )
    conn.commit()
    conn.close()
    
def get_conn():  # Если нет — добавьте
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn    
    
@app.route("/login", methods=["GET", "POST"])  # ← Вот оно!
def login():
    if request.method == "GET":
        if "user_id" in session:
            return redirect("/")
        return render_template("login.html", next=request.args.get("next"))
    
    # POST
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if not username or not password:
        return render_template("login.html", error="Введите логин и пароль"), 400
    
    conn = get_conn()
    user = conn.execute(
        "SELECT id, password_hash, role FROM users WHERE username = ? AND archived_at IS NULL",
        (username,)
    ).fetchone()
    conn.close()
    
    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Неверный логин или пароль"), 401
    
    session.clear()
    session["user_id"] = user["id"]
    session["role"] = user["role"]
    
    next_url = request.form.get("next") or ("/")
    return redirect(next_url)

@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")

def current_user():
    uid = session.get("user_id")
    if uid is None:
        return None
    conn = get_conn()
    user = conn.execute(
        "SELECT id, username, role FROM users WHERE id = ? AND archived_at IS NULL",
        (uid,),
    ).fetchone()
    conn.close()
    return user

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login_form", next=request.url))
        return f(*args, **kwargs)
    return wrapped

@app.get("/dashboard")
@login_required
def dashboard():
    user = current_user()
    return render_template("dashboard.html", user=user)

if __name__ == "__main__":
    init_db()
    ensure_master()
    app.run(debug=True)