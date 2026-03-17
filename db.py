import sqlite3

DB_PATH = "database.db"
def get_conn():
    """Вернуть соединение с SQLite. Вызывающий обязан закрыть соединение."""
    conn = sqlite3.connect(DB_PATH)
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
    conn.commit()
    conn.close()
    
def insert_test_user():
    """Добавить одного тестового пользователя (для проверки таблицы)."""
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, 'user')",
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
