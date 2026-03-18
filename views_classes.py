from flask import render_template, redirect, url_for, request, abort, flash
import sqlite3
from db import get_conn
from auth_utils import is_logged_in, is_manager, is_master

def can_manage_classes():
    """Может ли текущий пользователь просматривать и создавать классы."""
    return is_logged_in() and (is_manager() or is_master())

def class_list_view():
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))
    if not can_manage_classes():
        abort(403)

    conn = get_conn()
    classes = conn.execute(
        "SELECT id, name, created_at FROM classes ORDER BY name"
    ).fetchall()
    conn.close()

    return render_template("class_list.html", classes=classes)


def class_new_view():
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))
    if not can_manage_classes():
        abort(403)

    return render_template("class_new.html", error=None)


def class_create_view():
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))
    if not can_manage_classes():
        abort(403)

    name = (request.form.get("name") or "").strip()
    if not name:
        return render_template("class_new.html", error="Введите название класса.")

    conn = get_conn()
    conn.execute("INSERT INTO classes (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

    return redirect(url_for("class_list"))

def class_show_view(class_id):
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))
    if not can_manage_classes():
        abort(403)

    conn = get_conn()
    cls = conn.execute(
        "SELECT id, name, created_at FROM classes WHERE id = ?",
        (class_id,),
    ).fetchone()
    if cls is None:
        conn.close()
        abort(404)

    students_in_class = conn.execute(
        """
        SELECT u.id, u.username
        FROM users u
        INNER JOIN class_students cs ON cs.student_id = u.id
        WHERE cs.class_id = ? AND u.archived_at IS NULL
        ORDER BY u.username
        """,
        (class_id,),
    ).fetchall()

    students_not_in_class = conn.execute(
        """
        SELECT id, username
        FROM users
        WHERE role = 'student' AND archived_at IS NULL
        AND id NOT IN (SELECT student_id FROM class_students WHERE class_id = ?)
        ORDER BY username
        """,
        (class_id,),
    ).fetchall()
    conn.close()

    return render_template(
        "class_show.html",
        cls=cls,
        students_in_class=students_in_class,
        students_not_in_class=students_not_in_class,
    )
def class_add_student_view(class_id):
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))
    if not can_manage_classes():
        abort(403)

    student_id = request.form.get("student_id", type=int)
    if student_id is None:
        return redirect(url_for("class_show", class_id=class_id))

    conn = get_conn()
    cls = conn.execute("SELECT id FROM classes WHERE id = ?", (class_id,)).fetchone()
    student = conn.execute(
        "SELECT id FROM users WHERE id = ? AND role = 'student' AND archived_at IS NULL",
        (student_id,),
    ).fetchone()
    if cls is None or student is None:
        conn.close()
        abort(404)

    try:
        conn.execute(
            "INSERT INTO class_students (class_id, student_id) VALUES (?, ?)",
            (class_id, student_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()
    return redirect(url_for("class_show", class_id=class_id))
def class_remove_student_view(class_id):
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))
    if not can_manage_classes():
        abort(403)

    student_id = request.form.get("student_id", type=int)
    if student_id is None:
        return redirect(url_for("class_show", class_id=class_id))

    conn = get_conn()
    conn.execute(
        "DELETE FROM class_students WHERE class_id = ? AND student_id = ?",
        (class_id, student_id),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("class_show", class_id=class_id))