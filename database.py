"""SQLite persistence for sessions and chat messages."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from datetime import datetime


class ChatDatabase:
    def __init__(self, db_path=None):
        if db_path is None:
            data_dir = Path.home() / ".neuradesk"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "neuradesk.sqlite3"
        self.connection = sqlite3.connect(str(db_path))
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self._initialize()

    def _initialize(self):
        with self.connection:
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    def create_session(self, title="گفت‌وگوی جدید"):
        created = datetime.now().isoformat(timespec="seconds")
        with self.connection:
            cursor = self.connection.execute("INSERT INTO sessions(title, created_at) VALUES (?, ?)", (title, created))
        return cursor.lastrowid

    def add_message(self, session_id, role, content):
        if role not in ("user", "assistant"):
            raise ValueError("نقش پیام نامعتبر است.")
        if not isinstance(content, str):
            raise TypeError("محتوای پیام باید متن باشد.")
        created = datetime.now().isoformat(timespec="seconds")
        with self.connection:
            self.connection.execute(
                "INSERT INTO messages(session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, role, content, created),
            )
            row = self.connection.execute("SELECT COUNT(*) FROM messages WHERE session_id=?", (session_id,)).fetchone()
            if row and row[0] == 1 and role == "user":
                title = content.replace("\n", " ").strip()[:35] or "گفت‌وگوی جدید"
                self.connection.execute("UPDATE sessions SET title=? WHERE id=?", (title, session_id))

    def list_sessions(self):
        return self.connection.execute(
            "SELECT id, title, created_at FROM sessions ORDER BY id DESC"
        ).fetchall()

    def get_messages(self, session_id):
        return self.connection.execute(
            "SELECT role, content, created_at FROM messages WHERE session_id=? ORDER BY id",
            (session_id,),
        ).fetchall()

    def close(self):
        self.connection.close()
