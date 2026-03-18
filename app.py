from flask import Flask, render_template,request, redirect, url_for, session, abort, request, flash
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from db import get_conn, init_db, insert_test_user, show_table
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
    dashboard_view
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
app = Flask(__name__)
app.secret_key = "dev-secret"

    
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
    
    user = current_user()

    db_ok = row is not None and row["ok"] == 1
    return render_template("home.html", db_ok=db_ok, user=user)

if __name__ == "__main__":
    init_db() 
    ensure_master()
    #insert_test_user() 
    #print(show_table())
    
    print(show_table())

    app.run(debug=True)