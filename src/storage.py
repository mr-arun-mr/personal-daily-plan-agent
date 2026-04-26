import sqlite3
import os
from typing import Optional

DB_PATH = os.environ.get("DB_PATH", "planner.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                number INTEGER NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_logs (
                date TEXT PRIMARY KEY,
                summary TEXT,
                completed INTEGER DEFAULT 0,
                skipped INTEGER DEFAULT 0,
                pending INTEGER DEFAULT 0,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.commit()


def get_tasks(date_str: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE date = ? ORDER BY number",
            (date_str,)
        ).fetchall()
        return [dict(row) for row in rows]


def add_task(date_str: str, description: str) -> int:
    with get_connection() as conn:
        max_num = conn.execute(
            "SELECT MAX(number) FROM tasks WHERE date = ?", (date_str,)
        ).fetchone()[0] or 0
        number = max_num + 1
        conn.execute(
            "INSERT INTO tasks (date, number, description) VALUES (?, ?, ?)",
            (date_str, number, description)
        )
        conn.commit()
        return number


def bulk_add_tasks(date_str: str, descriptions: list[str]):
    with get_connection() as conn:
        conn.execute("DELETE FROM tasks WHERE date = ?", (date_str,))
        for i, desc in enumerate(descriptions, 1):
            conn.execute(
                "INSERT INTO tasks (date, number, description) VALUES (?, ?, ?)",
                (date_str, i, desc)
            )
        conn.commit()


def update_task_status(date_str: str, number: int, status: str) -> bool:
    with get_connection() as conn:
        result = conn.execute(
            "UPDATE tasks SET status = ? WHERE date = ? AND number = ?",
            (status, date_str, number)
        )
        conn.commit()
        return result.rowcount > 0


def get_task(date_str: str, number: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE date = ? AND number = ?",
            (date_str, number)
        ).fetchone()
        return dict(row) if row else None


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else default


def set_setting(key: str, value: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        conn.commit()


def save_daily_log(date_str: str, summary: str, completed: int, skipped: int, pending: int):
    with get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO daily_logs (date, summary, completed, skipped, pending)
            VALUES (?, ?, ?, ?, ?)
        """, (date_str, summary, completed, skipped, pending))
        conn.commit()


def get_daily_log(date_str: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM daily_logs WHERE date = ?", (date_str,)
        ).fetchone()
        return dict(row) if row else None
