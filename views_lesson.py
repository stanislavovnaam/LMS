from flask import render_template, redirect, url_for, request, abort, session
from db import get_conn
from auth_utils import is_logged_in, current_user, is_teacher, is_manager, is_master


def can_manage_lesson(lesson):
    """Может ли текущий пользователь управлять занятием (посещаемость и т.д.)."""
    if not is_logged_in():
        return False
    u = current_user()
    if u is None:
        return False
    if is_manager() or is_master():
        return True
    if is_teacher() and lesson["teacher_id"] == u["id"]:
        return True
    return False
def lesson_list_view():
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))

    u = current_user()
    if u is None:
        session.clear()
        return redirect(url_for("login_form"))

    conn = get_conn()
    if u["role"] == "student":
        lessons = conn.execute(
            """
            SELECT l.id, l.title, l.scheduled_date, l.class_id, l.teacher_id,
                   c.name AS class_name
            FROM lessons l
            JOIN classes c ON c.id = l.class_id
            WHERE l.class_id IN (SELECT class_id FROM class_students WHERE student_id = ?)
            ORDER BY l.scheduled_date DESC
            """,
            (u["id"],),
        ).fetchall()
    elif u["role"] == "teacher":
        lessons = conn.execute(
            """
            SELECT l.id, l.title, l.scheduled_date, l.class_id, l.teacher_id,
                   c.name AS class_name
            FROM lessons l
            JOIN classes c ON c.id = l.class_id
            WHERE l.teacher_id = ?
            ORDER BY l.scheduled_date DESC
            """,
            (u["id"],),
        ).fetchall()
    elif is_manager() or is_master():
        lessons = conn.execute(
            """
            SELECT l.id, l.title, l.scheduled_date, l.class_id, l.teacher_id,
                   c.name AS class_name
            FROM lessons l
            JOIN classes c ON c.id = l.class_id
            ORDER BY l.scheduled_date DESC
            """
        ).fetchall()
    else:
        lessons = []
    conn.close()

    return render_template("lesson_list.html", lessons=lessons)
def lesson_new_view():
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))
    if not is_manager() and not is_master():
        abort(403)

    conn = get_conn()
    classes = conn.execute("SELECT id, name FROM classes ORDER BY name").fetchall()
    teachers = conn.execute(
        "SELECT id, username FROM users WHERE role = 'teacher' AND archived_at IS NULL ORDER BY username"
    ).fetchall()
    conn.close()
    return render_template("lesson_new.html", classes=classes, teachers=teachers, error=None)


def lesson_create_view():
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))
    if not is_manager() and not is_master():
        abort(403)

    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    class_id = request.form.get("class_id", type=int)
    teacher_id = request.form.get("teacher_id", type=int)
    scheduled_date = (request.form.get("scheduled_date") or "").strip()
    duration = request.form.get("duration", type=int)
    classroom = (request.form.get("classroom") or "").strip()

    if not title or class_id is None:
        conn = get_conn()
        classes = conn.execute("SELECT id, name FROM classes ORDER BY name").fetchall()
        teachers = conn.execute(
            "SELECT id, username FROM users WHERE role = 'teacher' AND archived_at IS NULL ORDER BY username"
        ).fetchall()
        conn.close()
        return render_template(
            "lesson_new.html",
            classes=classes,
            teachers=teachers,
            error="Укажите название и класс.",
        )

    if duration is None or duration < 1:
        duration = 45

    conn = get_conn()
    conn.execute(
        """INSERT INTO lessons (title, description, teacher_id, class_id, scheduled_date, duration, classroom)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (title, description, teacher_id if teacher_id else None, class_id, scheduled_date, duration, classroom or None),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("lesson_list"))
def lesson_show_view(lesson_id):
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))

    u = current_user()
    if u is None:
        session.clear()
        return redirect(url_for("login_form"))

    conn = get_conn()
    lesson = conn.execute(
        """SELECT l.id, l.title, l.description, l.teacher_id, l.class_id, l.scheduled_date, l.duration, l.classroom,
                  c.name AS class_name
           FROM lessons l
           JOIN classes c ON c.id = l.class_id
           WHERE l.id = ?""",
        (lesson_id,),
    ).fetchone()
    if lesson is None:
        conn.close()
        abort(404)

    if u["role"] == "student":
        in_class = conn.execute(
            "SELECT 1 FROM class_students WHERE class_id = ? AND student_id = ?",
            (lesson["class_id"], u["id"]),
        ).fetchone()
        if not in_class:
            conn.close()
            abort(403)
    elif u["role"] == "teacher":
        if lesson["teacher_id"] != u["id"]:
            conn.close()
            abort(403)
    elif not is_manager() and not is_master():
        conn.close()
        abort(403)

    teacher_name = None
    if lesson["teacher_id"]:
        row = conn.execute("SELECT username FROM users WHERE id = ?", (lesson["teacher_id"],)).fetchone()
        teacher_name = row["username"] if row else None

    homework_list = []

    can_manage = can_manage_lesson(lesson)
    students_attendance = []
    if can_manage:
        class_students = conn.execute(
            """SELECT u.id, u.username
               FROM users u
               INNER JOIN class_students cs ON cs.student_id = u.id
               WHERE cs.class_id = ? AND u.archived_at IS NULL
               ORDER BY u.username""",
            (lesson["class_id"],),
        ).fetchall()
        for s in class_students:
            att = conn.execute(
                "SELECT status, mark FROM attendance WHERE lesson_id = ? AND student_id = ?",
                (lesson_id, s["id"]),
            ).fetchone()
            students_attendance.append({
                "id": s["id"],
                "username": s["username"],
                "status": att["status"] if att else "present",
                "mark": att["mark"] if att else "",
            })
    conn.close()

    return render_template(
        "lesson_show.html",
        lesson=lesson,
        teacher_name=teacher_name,
        homework_list=homework_list,
        can_manage=can_manage,
        students_attendance=students_attendance,
    )
def lesson_attendance_save_view(lesson_id):
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))

    conn = get_conn()
    lesson = conn.execute("SELECT id, class_id, teacher_id FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    if lesson is None:
        conn.close()
        abort(404)
    if not can_manage_lesson(lesson):
        conn.close()
        abort(403)

    class_students = conn.execute(
        "SELECT student_id FROM class_students WHERE class_id = ?",
        (lesson["class_id"],),
    ).fetchall()
    for row in class_students:
        sid = row["student_id"]
        status = request.form.get(f"status_{sid}") or "present"
        if status not in ("present", "absent"):
            status = "present"
        mark = (request.form.get(f"mark_{sid}") or "").strip() or None
        conn.execute(
            "INSERT OR REPLACE INTO attendance (student_id, lesson_id, status, mark) VALUES (?, ?, ?, ?)",
            (sid, lesson_id, status, mark),
        )
    conn.commit()
    conn.close()
    return redirect(url_for("lesson_show", lesson_id=lesson_id))