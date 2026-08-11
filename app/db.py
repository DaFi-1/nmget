import os
import re
import sqlite3
import time
from datetime import datetime

from flask import request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "instance", "nmget.db")

EMPTY_TAG = "EMPTY"
STATUS_PENDING = "ON"
STATUS_SENT = "OFF"
TAG_FILTER = "tag = ?"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MIN_DIGITS = 10
MAX_DIGITS = 13
MAX_TAG_LENGTH = 50

BUST_STATS = ("queue_stats", "dashboard_stats", "pending_counts")
BUST_ALL = BUST_STATS + ("tags",)

_CACHE = {}


def now():
    return datetime.now().strftime(DATE_FORMAT)


def digits(value):
    return re.sub(r"\D", "", str(value))


def json_data():
    return request.get_json(silent=True) or {}


def cache_get(key, ttl, fn):
    now_time = time.monotonic()
    entry = _CACHE.get(key)
    if entry and now_time - entry[0] < ttl:
        return entry[1]
    value = fn()
    _CACHE[key] = (now_time, value)
    return value


def cache_bust(*keys):
    for key in keys:
        _CACHE.pop(key, None)


class Database:
    def __init__(self, path=DB_PATH):
        self.path = path
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA cache_size=-8000")
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

                CREATE TABLE IF NOT EXISTS tegname (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                );

                CREATE INDEX IF NOT EXISTS idx_numbers_tag
                    ON numbers(tag);
                CREATE INDEX IF NOT EXISTS idx_numbers_status
                    ON numbers(status);
                CREATE INDEX IF NOT EXISTS idx_numbers_status_tag
                    ON numbers(status, tag);
                CREATE INDEX IF NOT EXISTS idx_numbers_date
                    ON numbers(date_get_number);
                CREATE INDEX IF NOT EXISTS idx_numbers_tag_status_date
                    ON numbers(tag, status, date_get_number);
                CREATE INDEX IF NOT EXISTS idx_queue_tag
                    ON queue(tag);
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO tag (name) VALUES (?)", (EMPTY_TAG,)
            )
            connection.execute(
                "INSERT OR IGNORE INTO tegname (name) VALUES (?)", (EMPTY_TAG,)
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

    @classmethod
    def create(cls, db, **values):
        obj = cls(db, **values)
        obj.save()
        return obj

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

    @classmethod
    def exists(cls, db, name):
        with db._connect() as connection:
            row = connection.execute(
                f"SELECT 1 FROM {cls.table} WHERE name = ? LIMIT 1", (name,)
            ).fetchone()
        return row is not None


class TagName(Model):
    table = "tegname"
    columns = ("id", "name")

    @classmethod
    def all(cls, db):
        with db._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM {cls.table} ORDER BY name"
            ).fetchall()
        return [cls(db, **dict(row)) for row in rows]


class Number(Model):
    table = "numbers"
    columns = ("id", "tag", "number", "status", "send_date", "date_get_number")

    @classmethod
    def stats(cls, db):
        today_str = datetime.now().strftime("%Y-%m-%d")
        with db._connect() as connection:
            by_status = connection.execute(
                "SELECT status, COUNT(id) AS quantity FROM numbers "
                "GROUP BY status ORDER BY quantity DESC"
            ).fetchall()
            status_by_tag = connection.execute(
                "SELECT tag, status, COUNT(id) AS quantity FROM numbers "
                "GROUP BY tag, status ORDER BY tag"
            ).fetchall()
            by_date = connection.execute(
                "SELECT substr(date_get_number, 1, 10) AS date, "
                "COUNT(id) AS quantity FROM numbers "
                "GROUP BY date ORDER BY date"
            ).fetchall()
            last = connection.execute(
                "SELECT MAX(date_get_number) FROM numbers"
            ).fetchone()[0]
        tag_totals = {}
        for row in status_by_tag:
            tag_totals[row["tag"]] = tag_totals.get(row["tag"], 0) + row["quantity"]
        by_tag = [
            {"tag": tag, "quantity": quantity}
            for tag, quantity in sorted(
                tag_totals.items(), key=lambda item: item[1], reverse=True
            )
        ]
        today = sum(
            row["quantity"] for row in by_date if row["date"] == today_str
        )
        return {
            "total": sum(row["quantity"] for row in by_status),
            "today": today,
            "last_capture": last,
            "by_tag": by_tag,
            "by_date": [dict(row) for row in by_date],
            "by_status": [dict(row) for row in by_status],
            "status_by_tag": [dict(row) for row in status_by_tag],
        }

    @classmethod
    def pending_for_tag(cls, db, tag, limit):
        with db._connect() as connection:
            rows = connection.execute(
                "SELECT number FROM numbers WHERE tag = ? AND status = ? "
                "ORDER BY date_get_number ASC LIMIT ?",
                (tag, STATUS_PENDING, limit),
            ).fetchall()
        return [row["number"] for row in rows]

    @classmethod
    def pending_counts(cls, db):
        with db._connect() as connection:
            rows = connection.execute(
                "SELECT tag, COUNT(id) AS quantity FROM numbers "
                "WHERE status = ? GROUP BY tag ORDER BY tag",
                (STATUS_PENDING,),
            ).fetchall()
        return [dict(row) for row in rows]

    @classmethod
    def mark_sent(cls, db, numbers):
        if not numbers:
            return
        moment = now()
        placeholders = ",".join("?" for _ in numbers)
        with db._connect() as connection:
            connection.execute(
                f"UPDATE numbers SET status = ?, send_date = ? "
                f"WHERE number IN ({placeholders})",
                [STATUS_SENT, moment] + numbers,
            )


class Queue(Model):
    table = "queue"
    columns = ("id", "number", "tag")

    @classmethod
    def stats(cls, db):
        with db._connect() as connection:
            rows = connection.execute(
                "SELECT tag AS tag, COUNT(id) AS quantity "
                "FROM queue GROUP BY tag ORDER BY quantity DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    @classmethod
    def add_numbers(cls, db, tag, numbers):
        with db._connect() as connection:
            connection.executemany(
                "INSERT OR IGNORE INTO queue (number, tag) "
                "SELECT ?, ? WHERE NOT EXISTS "
                "(SELECT 1 FROM numbers WHERE number = ?)",
                [(number, tag, number) for number in numbers],
            )

    @classmethod
    def _move(cls, db, filter_="", values=()):
        where = f" WHERE {filter_}" if filter_ else ""
        moment = now()
        with db._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO numbers "
                "(tag, number, status, send_date, date_get_number) "
                f"SELECT tag, number, ?, NULL, ? FROM queue{where}",
                [STATUS_PENDING, moment] + list(values),
            )
            connection.execute(f"DELETE FROM queue{where}", values)

    @classmethod
    def move_to_numbers(cls, db):
        cls._move(db)

    @classmethod
    def move_tag(cls, db, tag):
        cls._move(db, filter_=TAG_FILTER, values=(tag,))

    @classmethod
    def _clear(cls, db, filter_="", values=()):
        where = f" WHERE {filter_}" if filter_ else ""
        with db._connect() as connection:
            connection.execute(f"DELETE FROM queue{where}", values)

    @classmethod
    def clear_all(cls, db):
        cls._clear(db)

    @classmethod
    def clear_tag(cls, db, tag):
        cls._clear(db, filter_=TAG_FILTER, values=(tag,))


db = Database()
