from flask import Flask, render_template,request, redirect, url_for, session, abort, request, flash
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from db import get_conn, init_db, insert_test_user, show_table
from dotenv import load_dotenv
import os
from auth_utils import(
    create_user,
    ensure_master,
    is_logged_in,
    current_user,
    is_admin,
    get_registration_open,
    is_manager,
    is_master,
    is_teacher
)

from views_auth import(
    login_form_view,
    login_view,
    logout_view,
    register_form_view,
    register_view,
    dashboard_view,
    progress_view,
    stats_view
)

from views_admin import(
    admin_settings_view,
    admin_settings_save_view,
    admin_users_view,
    admin_user_create_view,
    admin_user_archive_view,
    admin_user_restore_view,
    admin_user_delete_view
   )
    
from views_classes import (
    class_list_view,
    class_new_view,
    class_create_view
)    

from views_classes import (
    class_list_view,
    class_new_view,
    class_create_view,
    class_show_view,
    class_add_student_view,
    class_remove_student_view,
)

from views_lessons import (
    lesson_list_view,
    lesson_new_view,
    lesson_create_view,
    lesson_show_view,
    lesson_attendance_save_view,
)

from views_homework import (
    homework_new_view,
    homework_create_view,
    homework_show_view,
    homework_submit_view,
    homework_grades_save_view,
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")

def init_db():
    conn = sqlite3.connect('lms.db')
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('registration_open', '0')")
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('student', 'teacher', 'manager', 'admin')),
            archived_at TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS class_students (
            class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            PRIMARY KEY (class_id, student_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            teacher_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            scheduled_date TEXT NOT NULL,
            duration INTEGER NOT NULL,
            classroom TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)   
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
            status TEXT NOT NULL CHECK (status IN ('present', 'absent')),
            mark TEXT,
            PRIMARY KEY (student_id, lesson_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS homework (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT,
            url TEXT,
            due_date TEXT NOT NULL,
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            homework_id INTEGER NOT NULL REFERENCES homework(id) ON DELETE CASCADE,
            text TEXT,
            url TEXT,
            grade INTEGER,
            feedback TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            PRIMARY KEY (student_id, homework_id)
        )
    """)
    conn.commit()
    conn.close()
    
init_db()  
    
@app.get("/login")
def login_form():
    return login_form_view()

@app.post("/login")
def login():
    return login_view()

@app.get("/logout")
def logout():
    return logout_view()

@app.route("/dashboard")
def dashboard():
    return dashboard_view()

@app.get("/progress")
def progress():
    return progress_view()

@app.get("/stats")
def stats():
    return stats_view()

@app.get("/admin/settings")
def admin_settings():
    return admin_settings_view()

@app.post("/admin/settings")
def admin_settings_save():
    return admin_settings_save_view()

@app.get("/admin/users")
def admin_users():
    return admin_users_view()

@app.post("/admin/users/create")
def admin_user_create():
    return admin_user_create_view()

@app.post("/admin/users/<int:user_id>/archive")
def admin_user_archive(user_id):
    return admin_user_archive_view(user_id)
    
@app.post("/admin/users/<int:user_id>/restore")
def admin_user_restore(user_id):
    return admin_user_restore_view(user_id)

@app.post("/admin/users/<int:user_id>/delete")
def admin_user_delete(user_id):
    return admin_user_delete_view(user_id)

@app.get("/classes")
def class_list():
    return class_list_view()

@app.get("/classes/new")
def class_new():
    return class_new_view()

@app.post("/classes/new")
def class_create():
    return class_create_view()

@app.get("/classes/<int:class_id>")
def class_show(class_id):
    return class_show_view(class_id)


@app.post("/classes/<int:class_id>/students/add")
def class_add_student(class_id):
    return class_add_student_view(class_id)


@app.post("/classes/<int:class_id>/students/remove")
def class_remove_student(class_id):
    return class_remove_student_view(class_id)

@app.get("/lessons")
def lesson_list():
    return lesson_list_view()


@app.get("/lessons/new")
def lesson_new():
    return lesson_new_view()


@app.post("/lessons/new")
def lesson_create():
    return lesson_create_view()


@app.get("/lessons/<int:lesson_id>")
def lesson_show(lesson_id):
    return lesson_show_view(lesson_id)


@app.post("/lessons/<int:lesson_id>/attendance")
def lesson_attendance_save(lesson_id):
    return lesson_attendance_save_view(lesson_id)

@app.get("/register")
def register_form():
    return register_form_view()

@app.post("/register")
def register():
    return register_view()

@app.context_processor
def inject():
    return {
        "current_user": current_user,
        "is_admin": is_admin,
        "is_manager": is_manager,
        "is_master": is_master,
        "is_teacher": is_teacher,
        "registration_open": get_registration_open(),
    }


@app.route("/")
def home():
    conn = get_conn()
    row = conn.execute("SELECT 1 AS ok").fetchone()
    conn.close()
    
    u = current_user()

    db_ok = row is not None and row["ok"] == 1
    return render_template("home.html", db_ok=db_ok, u=u)

if __name__ == "__main__":
    #init_db() 
    ensure_master()
    print(show_table())

    app.run(debug=True)