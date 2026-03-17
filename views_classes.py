from flask import render_template, redirect, url_for, request, abort

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