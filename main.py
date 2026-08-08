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

