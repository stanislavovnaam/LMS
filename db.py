import sqlite3
from contextlib import contextmanager

@contextmanager
def get_conn():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

DB_PATH = "database.db"
def get_conn():
    """Вернуть соединение с SQLite. Вызывающий обязан закрыть соединение."""
    conn = sqlite3.connect("database.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row  
    return conn 

def init_db():
    """Создать таблицу users, если её ещё нет."""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('registration_open', '0')")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('student', 'teacher', 'manager', 'admin')),
            archived_at TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS class_students (
            class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            PRIMARY KEY (class_id, student_id)
        )
    """)
    conn.execute("""
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
            status TEXT NOT NULL CHECK (status IN ('present', 'absent')),
            mark TEXT,
            PRIMARY KEY (student_id, lesson_id)
        )
    """)
    conn.execute("""
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
    conn.execute("""
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
    
def insert_test_user():
    """Добавить одного тестового пользователя (для проверки таблицы)."""
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, 'student')",
        ("testuser", "placeholder_hash"),
    )
    conn.commit()
    conn.close()


def show_table():
    """
    Вернуть содержимое таблицы users как список строк.
    Удобно вызывать из консоли: print(show_table()).
    """
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]    
