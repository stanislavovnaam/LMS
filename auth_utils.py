from flask import session
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from db import get_conn

def create_user(username, password, role):
    password_hash = generate_password_hash(password)

    conn = get_conn()
    row = conn.execute(
        "INSERT INTO users  (username, password, role) VALUES (?, ?, ?)",
        (username, password_hash, role),
    ).fetchone()
    conn.commit()
    conn.close()
    
def ensure_master():
    """
    Убедиться, что в системе есть хотя бы один администратор.
    Если нет — создать пользователя master/master с ролью admin.
    """
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM users WHERE role = 'admin' AND archived_at IS NULL LIMIT 1"
    ).fetchone()

    if row is None:
        create_user("master", "master", "admin")
    conn.close()       
        
def is_logged_in():
    return session.get("user_id") is not None

def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None

    conn = get_conn()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ? AND archived_at IS NULL",
        (user_id,),
    ).fetchone()
    conn.close()

    return user

def is_admin():
    u = current_user()
    return u is not None and u["role"] == "admin"

def is_manager():
    u = current_user()
    return u is not None and u["role"] == "manager"

def is_master():
    u = current_user()
    return u is not None and u["role"] == "admin"

def is_teacher():
    u = current_user()
    return u is not None and u["role"] == "teacher"

def get_registration_open():
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = 'registration_open'").fetchone()
    conn.close()
    return row is not None and row["value"] == "1"