from flask import render_template, request, redirect, url_for, session, abort
from auth_utils import is_logged_in, current_user, get_registration_open
from db import get_conn
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3

def login_form_view():
    if is_logged_in():
        return redirect(url_for("home"))

    return render_template("login.html", error=None)

def login_view():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        return render_template(
            "login.html",
            error="Введите логин и пароль.",
        )

    conn = get_conn()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND archived_at IS NULL LIMIT 1",
        (username,),
    ).fetchone()
    conn.close()

    if user is None:
        return render_template(
            "login.html",
            error="Пользователь не найден.",
        )

    if not check_password_hash(user["password"], password):
        return render_template(
            "login.html",
            error="Неверный пароль.",
        )

    session.clear()
    session["user_id"] = user["id"]
    session["role"] = user["role"]

    return redirect(url_for("dashboard"))

def logout_view():
    session.clear()
    return redirect(url_for("home"))

def dashboard_view():
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))

    user = current_user()
    if user is None:
        session.clear()
        return redirect(url_for("login_form"))

    conn = get_conn()
    
    total_students = []
    total_teachers = []
    total_managers = []
    recent_lessons = []
    recent_homework = []
    
    if user["role"] in ["student", "teacher", "manager", "admin"]:
        if user["role"] == "student":
            total_students = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE role = 'student' AND archived_at IS NULL"
            ).fetchone()["c"]
            recent_lessons = conn.execute(
            """SELECT l.id, l.title, l.scheduled_date, c.name AS class_name
               FROM lessons l JOIN classes c ON c.id = l.class_id
               WHERE l.class_id IN (SELECT class_id FROM class_students WHERE student_id = ?)
               ORDER BY l.scheduled_date DESC LIMIT 10""",
            (user["id"],),
            ).fetchall()
            recent_homework = conn.execute(
            """SELECT h.id, h.title, h.due_date
               FROM homework h
               WHERE h.lesson_id IN (
                 SELECT id FROM lessons
                 WHERE class_id IN (SELECT class_id FROM class_students WHERE student_id = ?)
               )
               ORDER BY h.due_date DESC LIMIT 10""",
            (user["id"],),
            ).fetchall()
        elif user["role"] in ["teacher"]:    
            total_teachers = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE role = 'teacher' AND archived_at IS NULL"
            ).fetchone()["c"]
            recent_lessons = conn.execute(
            """SELECT l.id, l.title, l.scheduled_date, c.name AS class_name
               FROM lessons l JOIN classes c ON c.id = l.class_id
               WHERE l.teacher_id = ? ORDER BY l.scheduled_date DESC LIMIT 10""",
            (user["id"],),
            ).fetchall()
            recent_homework = conn.execute(
            """SELECT id, title, due_date FROM homework WHERE created_by = ? ORDER BY created_at DESC LIMIT 10""",
            (user["id"],),
            ).fetchall()
        elif user["role"] in ["manager"]:    
            total_managers = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE role = 'manager' AND archived_at IS NULL"
            ).fetchone()["c"]
            recent_lessons = conn.execute(
            """SELECT l.id, l.title, l.scheduled_date, c.name AS class_name
               FROM lessons l JOIN classes c ON c.id = l.class_id
               ORDER BY l.scheduled_date DESC LIMIT 10"""
            ).fetchall()
            recent_homework = conn.execute(
            """SELECT id, title, due_date FROM homework ORDER BY created_at DESC LIMIT 10"""
            ).fetchall()
        conn.close()
    
    return render_template(
        "dashboard.html",
        user=user,
        total_students=total_students,
        total_teachers=total_teachers,
        total_managers=total_managers,
        recent_lessons=recent_lessons,
        recent_homework=recent_homework
    )

def register_form_view():
    if session.get("user_id") is not None:
        return redirect(url_for("dashboard"))
    if not get_registration_open():
        return render_template("register.html", registration_disabled=True), 403
    return render_template("register.html")

def register_view():
    if not get_registration_open():
        return render_template("register.html", registration_disabled=True), 403
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if not username or not password:
        return render_template("register.html", error="Username and password required."), 400
    if len(username) < 2:
        return render_template("register.html", error="Username too short."), 400
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, 'student')",
            (username, generate_password_hash(password)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return render_template("register.html", error="Username already taken."), 409
    conn.close()
    return redirect(url_for("login_form"))

def progress_view():
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))

    user = current_user()
    if user is None:
        session.clear()
        return redirect(url_for("login_form"))
    if user["role"] != "student":
        abort(403)

    conn = get_conn()
    total_lessons_row = conn.execute(
        """
        SELECT COUNT(DISTINCT l.id) AS c
        FROM lessons l
        WHERE l.class_id IN (SELECT class_id FROM class_students WHERE student_id = ?)
        """,
        (user["id"],),
    ).fetchone()
    total_lessons = total_lessons_row["c"] if total_lessons_row else 0

    present_row = conn.execute(
        """
        SELECT COUNT(*) AS c FROM attendance a
        INNER JOIN lessons l ON l.id = a.lesson_id
        WHERE a.student_id = ? AND a.status = 'present'
        AND l.class_id IN (SELECT class_id FROM class_students WHERE student_id = ?)
        """,
        (user["id"], user["id"]),
    ).fetchone()
    present_count = present_row["c"] if present_row else 0

    attendance_pct = (present_count / total_lessons * 100) if total_lessons else 0

    graded = conn.execute(
        """
        SELECT h.id AS homework_id, h.title AS homework_title, h.due_date, s.grade
        FROM submissions s
        JOIN homework h ON h.id = s.homework_id
        WHERE s.student_id = ? AND s.grade IS NOT NULL
        ORDER BY h.due_date DESC
        """,
        (user["id"],),
    ).fetchall()

    avg_row = conn.execute(
        "SELECT AVG(grade) AS avg_grade FROM submissions WHERE student_id = ? AND grade IS NOT NULL",
        (user["id"],),
    ).fetchone()
    average_grade = round(avg_row["avg_grade"], 1) if avg_row and avg_row["avg_grade"] is not None else None

    conn.close()

    return render_template(
        "progress.html",
        user=user,
        attendance_pct=attendance_pct,
        total_lessons=total_lessons,
        present_count=present_count,
        graded=graded,
        average_grade=average_grade,
    )
def stats_view():
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))

    user = current_user()
    if user is None:
        session.clear()
        return redirect(url_for("login_form"))
    if user["role"] != "manager" and user["role"] != "admin":
        abort(403)

    conn = get_conn()
    count_students = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE role = 'student' AND archived_at IS NULL"
    ).fetchone()["c"]
    count_teachers = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE role = 'teacher' AND archived_at IS NULL"
    ).fetchone()["c"]
    count_lessons = conn.execute("SELECT COUNT(*) AS c FROM lessons").fetchone()["c"]
    count_homework = conn.execute("SELECT COUNT(*) AS c FROM homework").fetchone()["c"]
    count_submissions = conn.execute("SELECT COUNT(*) AS c FROM submissions").fetchone()["c"]
    conn.close()

    return render_template(
        "stats.html",
        count_students=count_students,
        count_teachers=count_teachers,
        count_lessons=count_lessons,
        count_homework=count_homework,
        count_submissions=count_submissions,
    )