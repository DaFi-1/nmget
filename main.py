import os
import re
import sqlite3
from datetime import datetime

from flask import (
    Flask,
    render_template,
    url_for,
    redirect,
    jsonify,
    request,
)

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "nmget.db")

EMPTY_TAG = "EMPTY"
STATUS_PENDING = "ON"
STATUS_SENT = "OFF"
TAG_FILTER = "tag = ?"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MIN_DIGITS = 10
MAX_DIGITS = 13
MAX_TAG_LENGTH = 50


def now():
    return datetime.now().strftime(DATE_FORMAT)


class Database:
    def __init__(self, path=DB_PATH):
        self.path = path
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with self._connect() as connection:
            fila_rows = connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'fila'"
            ).fetchall()
            if fila_rows:
                connection.execute("ALTER TABLE fila RENAME TO queue")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS tag (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS numbers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tag TEXT NOT NULL,
                    number TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL DEFAULT 'ON',
                    send_date TEXT,
                    date_get_number TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    number TEXT NOT NULL UNIQUE,
                    tag TEXT NOT NULL
                );
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO tag (name) VALUES (?)", (EMPTY_TAG,)
            )
            columns = [
                row["name"]
                for row in connection.execute("PRAGMA table_info(numbers)").fetchall()
            ]
            if "send" in columns and "status" not in columns:
                connection.execute("ALTER TABLE numbers RENAME COLUMN send TO status")


class Model:
    table = None
    columns = ()

    def __init__(self, db, **values):
        self.db = db
        for column in self.columns:
            setattr(self, column, values.get(column))

    @classmethod
    def find(cls, db, **filters):
        clauses = " AND ".join(f"{key} = ?" for key in filters)
        values = list(filters.values())
        with db._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM {cls.table} WHERE {clauses}", values
            ).fetchall()
        return [cls(db, **dict(row)) for row in rows]

    def save(self):
        columns = [
            column
            for column in self.columns
            if column != "id" and getattr(self, column) is not None
        ]
        placeholders = ",".join("?" for _ in columns)
        values = [getattr(self, column) for column in columns]
        with self.db._connect() as connection:
            connection.execute(
                f"INSERT INTO {self.table} ({','.join(columns)}) "
                f"VALUES ({placeholders})",
                values,
            )


class Tag(Model):
    table = "tag"
    columns = ("id", "name")

    @classmethod
    def create(cls, db, name):
        tag = cls(db, name=name)
        tag.save()
        return tag

    @classmethod
    def current(cls, db):
        with db._connect() as connection:
            row = connection.execute(
                f"SELECT * FROM {cls.table} ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row:
            return cls(db, **dict(row))
        return cls(db, name=EMPTY_TAG)

    @classmethod
    def delete(cls, db, name):
        with db._connect() as connection:
            connection.execute(f"DELETE FROM {cls.table} WHERE name = ?", (name,))


class Number(Model):
    table = "numbers"
    columns = ("id", "tag", "number", "status", "send_date", "date_get_number")

    @classmethod
    def stats(cls, db):
        today_start = datetime.now().strftime("%Y-%m-%d") + " 00:00:00"
        with db._connect() as connection:
            total = connection.execute("SELECT COUNT(id) FROM numbers").fetchone()[0]
            by_tag = connection.execute(
                "SELECT tag, COUNT(id) AS quantity FROM numbers "
                "GROUP BY tag ORDER BY quantity DESC"
            ).fetchall()
            by_date = connection.execute(
                "SELECT substr(date_get_number, 1, 10) AS date, "
                "COUNT(id) AS quantity FROM numbers "
                "GROUP BY date ORDER BY date"
            ).fetchall()
            by_status = connection.execute(
                "SELECT status, COUNT(id) AS quantity FROM numbers "
                "GROUP BY status ORDER BY quantity DESC"
            ).fetchall()
            status_by_tag = connection.execute(
                "SELECT tag, status, COUNT(id) AS quantity FROM numbers "
                "GROUP BY tag, status ORDER BY tag"
            ).fetchall()
            today = connection.execute(
                "SELECT COUNT(id) FROM numbers WHERE date_get_number >= ?",
                (today_start,),
            ).fetchone()[0]
            last = connection.execute(
                "SELECT MAX(date_get_number) FROM numbers"
            ).fetchone()[0]
        return {
            "total": total,
            "today": today,
            "last_capture": last,
            "by_tag": [dict(row) for row in by_tag],
            "by_date": [dict(row) for row in by_date],
            "by_status": [dict(row) for row in by_status],
            "status_by_tag": [dict(row) for row in status_by_tag],
        }

