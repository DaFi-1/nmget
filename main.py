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
            for number in numbers:
                connection.execute(
                    "INSERT OR IGNORE INTO queue (number, tag) "
                    "SELECT ?, ? WHERE NOT EXISTS "
                    "(SELECT 1 FROM numbers WHERE number = ?)",
                    (number, tag, number),
                )

    @classmethod
    def _move(cls, db, filter_="", values=()):
        where = f" WHERE {filter_}" if filter_ else ""
        moment = now()
        with db._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM queue{where}", values
            ).fetchall()
            for row in rows:
                data = dict(row)
                connection.execute(
                    "INSERT OR IGNORE INTO numbers (tag, number, status, send_date, date_get_number) "
                    "VALUES (?, ?, ?, NULL, ?)",
                    (data["tag"], data["number"], STATUS_PENDING, moment),
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


@app.before_request
def ensure_db():
    if request.path.startswith("/static/"):
        return
    db._initialize()


@app.route('/')
def home():
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route("/dashboard/data")
def dashboard_data():
    return jsonify(Number.stats(db))


@app.route('/tag/current')
def current_tag():
    tag = Tag.current(db)
    return jsonify({"tag": tag.name})


@app.route('/tag/current', methods=['DELETE'])
def delete_current_tag():
    tag = Tag.current(db)
    if tag.name != EMPTY_TAG:
        Tag.delete(db, tag.name)
    return jsonify({"tag": EMPTY_TAG})


@app.route('/nmget', methods=['GET', 'POST'])
def nmget():
    if request.method == "POST":
        data = request.get_json(silent=True)
        tag_name = ((data or {}).get("tag") or "").strip()[:MAX_TAG_LENGTH]
        if tag_name:
            try:
                Tag.create(db, name=tag_name)
            except sqlite3.IntegrityError:
                pass
        return jsonify({"ok": True})
    return render_template('nmget.html')


@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response


@app.errorhandler(Exception)
def handle_error(error):
    app.logger.exception("Unhandled error: %s", error)
    return jsonify({"ok": False, "error": "internal error"}), 500


@app.route('/queue')
def queue_stats():
    return jsonify({"items": Queue.stats(db)})


@app.route('/queue/send', methods=['POST'])
def queue_send():
    data = request.get_json(silent=True)
    tag = (data or {}).get("tag")
    if tag:
        Queue.move_tag(db, tag)
    else:
        Queue.move_to_numbers(db)
    return jsonify({"ok": True})


@app.route('/queue/clear', methods=['POST'])
def queue_clear():
    data = request.get_json(silent=True)
    tag = (data or {}).get("tag")
    if tag:
        Queue.clear_tag(db, tag)
    else:
        Queue.clear_all(db)
    return jsonify({"ok": True})


@app.route("/phones", methods=["POST", "OPTIONS"])
def receive_phones():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": True})

    tag_name = data.get("tag")
    if not Tag.find(db, name=tag_name):
        return jsonify({"ok": True, "tag": "not found"})

    numbers = set()
    for number in data.get("phones", []):
        number = re.sub(r"\D", "", str(number))
        if MIN_DIGITS <= len(number) <= MAX_DIGITS:
            numbers.add(number)

    Queue.add_numbers(db, tag_name, numbers)
    return jsonify({"ok": True})


@app.route('/config')
def config():
    return render_template('config.html')

