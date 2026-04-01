from flask import render_template, redirect, url_for, request, abort
from db import get_conn
from auth_utils import is_logged_in, current_user, is_manager, is_master
from views_lessons import can_manage_lesson

def can_view_homework(lesson_row):
    """Может ли текущий пользователь видеть задание (страница и сдача)."""
    if not is_logged_in():
        return False
    u = current_user()
    if u is None:
        return False
    if can_manage_lesson(lesson_row):
        return True
    if u["role"] == "student":
        conn = get_conn()
        in_class = conn.execute(
            "SELECT 1 FROM class_students WHERE class_id = ? AND student_id = ?",
            (lesson_row["class_id"], u["id"]),
        ).fetchone()
        conn.close()
        return in_class is not None
    return False

def homework_new_view(lesson_id):
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))

    conn = get_conn()
    lesson = conn.execute(
        "SELECT id, class_id, teacher_id, title FROM lessons WHERE id = ?",
        (lesson_id,),
    ).fetchone()
    if lesson is None:
        conn.close()
        abort(404)
    if not can_manage_lesson(lesson):
        conn.close()
        abort(403)
    conn.close()
    return render_template("homework_new.html", lesson_id=lesson_id, lesson=lesson, error=None)


def homework_create_view(lesson_id):
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))

    conn = get_conn()
    lesson = conn.execute(
        "SELECT id, class_id, teacher_id, title FROM lessons WHERE id = ?",
        (lesson_id,),
    ).fetchone()
    if lesson is None:
        conn.close()
        abort(404)
    if not can_manage_lesson(lesson):
        conn.close()
        abort(403)

    title = (request.form.get("title") or "").strip()
    due_date = (request.form.get("due_date") or "").strip()
    description = (request.form.get("description") or "").strip()
    url = (request.form.get("url") or "").strip() or None

    if not title or not due_date:
        conn.close()
        return render_template(
            "homework_new.html", 
             lesson_id=lesson_id, 
             lesson=lesson, 
             error="Название обязательно!")

    homework = Homework(
        lesson_id=lesson_id,
        title=title,
        description=description,
        deadline=deadline if deadline else None
    )
    db.session.add(homework)
    db.session.commit()
    
    return redirect(url_for('homework_show', lesson_id=lesson_id))

def homework_show_view(homework_id):
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))

    conn = get_conn()
    homework = conn.execute(
        """SELECT h.id, h.lesson_id, h.title, h.description, h.url, h.due_date, h.created_by
           FROM homework h WHERE h.id = ?""",
        (homework_id,),
    ).fetchone()
    if homework is None:
        conn.close()
        abort(404)

    lesson = conn.execute(
        "SELECT id, class_id, teacher_id FROM lessons WHERE id = ?",
        (homework["lesson_id"],),
    ).fetchone()
    if lesson is None:
        conn.close()
        abort(404)

    if not can_view_homework(lesson):
        conn.close()
        abort(403)

    lesson_title_row = conn.execute(
        "SELECT title FROM lessons WHERE id = ?",
        (homework["lesson_id"],),
    ).fetchone()
    lesson_title = lesson_title_row["title"] if lesson_title_row else ""

    u = current_user()
    can_manage = can_manage_lesson(lesson)
    my_submission = None
    submissions_list = []
    can_still_submit = False

    if u["role"] == "student":
        my_submission = conn.execute(
            "SELECT text, url, grade, feedback, created_at FROM submissions WHERE homework_id = ? AND student_id = ?",
            (homework_id, u["id"]),
        ).fetchone()
        can_still_submit = my_submission is None
        if can_still_submit and homework["due_date"]:
            from datetime import datetime, timezone
            try:
                due_dt = datetime.fromisoformat(homework["due_date"].replace("Z", "+00:00"))
                if due_dt.tzinfo is None:
                    due_dt = due_dt.replace(tzinfo=timezone.utc)
                can_still_submit = datetime.now(timezone.utc) <= due_dt
            except Exception:
                pass
    elif can_manage:
        submissions_list = conn.execute(
            """SELECT s.student_id, s.text, s.url, s.grade, s.feedback, s.created_at, u.username
               FROM submissions s
               JOIN users u ON u.id = s.student_id
               WHERE s.homework_id = ?
               ORDER BY u.username""",
            (homework_id,),
        ).fetchall()

    conn.close()

    return render_template(
        "homework_show.html",
        homework=homework,
        lesson_title=lesson_title,
        can_manage=can_manage,
        my_submission=my_submission,
        can_still_submit=can_still_submit,
        submissions_list=submissions_list,
    )

def homework_submit_view(homework_id):
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))

    u = current_user()
    if u is None or u["role"] != "student":
        abort(403)

    conn = get_conn()
    homework = conn.execute("SELECT id, lesson_id, due_date FROM homework WHERE id = ?", (homework_id,)).fetchone()
    if homework is None:
        conn.close()
        abort(404)
    lesson = conn.execute("SELECT id, class_id, teacher_id FROM lessons WHERE id = ?", (homework["lesson_id"],)).fetchone()
    if lesson is None or not can_view_homework(lesson):
        conn.close()
        abort(403)
    existing = conn.execute(
        "SELECT 1 FROM submissions WHERE homework_id = ? AND student_id = ?",
        (homework_id, u["id"]),
    ).fetchone()
    if existing:
        conn.close()
        return redirect(url_for("homework_show", homework_id=homework_id))
    from datetime import datetime, timezone
    if homework["due_date"]:
        try:
            due_dt = datetime.fromisoformat(homework["due_date"].replace("Z", "+00:00"))
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > due_dt:
                conn.close()
                return redirect(url_for("homework_show", homework_id=homework_id))
        except Exception:
            pass
    text = (request.form.get("text") or "").strip()
    url = (request.form.get("url") or "").strip() or None
    conn.execute(
        "INSERT INTO submissions (student_id, homework_id, text, url) VALUES (?, ?, ?, ?)",
        (u["id"], homework_id, text or None, url),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("homework_show", homework_id=homework_id))

def homework_grades_save_view(homework_id):
    if not is_logged_in():
        return redirect(url_for("login_form", next=request.url))

    conn = get_conn()
    homework = conn.execute("SELECT id, lesson_id FROM homework WHERE id = ?", (homework_id,)).fetchone()
    if homework is None:
        conn.close()
        abort(404)
    lesson = conn.execute("SELECT id, class_id, teacher_id FROM lessons WHERE id = ?", (homework["lesson_id"],)).fetchone()
    if lesson is None or not can_manage_lesson(lesson):
        conn.close()
        abort(403)
    rows = conn.execute(
        "SELECT student_id FROM submissions WHERE homework_id = ?",
        (homework_id,),
    ).fetchall()
    for row in rows:
        sid = row["student_id"]
        grade_val = request.form.get(f"grade_{sid}", type=int)
        feedback_val = (request.form.get(f"feedback_{sid}") or "").strip() or None
        if grade_val is not None and 0 <= grade_val <= 100:
            conn.execute(
                "UPDATE submissions SET grade = ?, feedback = ? WHERE homework_id = ? AND student_id = ?",
                (grade_val, feedback_val, homework_id, sid),
            )
    conn.commit()
    conn.close()
    return redirect(url_for("homework_show", homework_id=homework_id))