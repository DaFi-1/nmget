import hashlib
import json
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
    make_response,
    send_file,
)
from werkzeug.exceptions import HTTPException

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


def digits(value):
    return re.sub(r"\D", "", str(value))


def json_data():
    return request.get_json(silent=True) or {}


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

                CREATE TABLE IF NOT EXISTS tegname (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                );
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

_STATIC_HASHES = {}


@app.context_processor
def inject_static_version():
    def version(filename):
        path = os.path.join(BASE_DIR, "static", filename)
        try:
            mtime = os.stat(path).st_mtime_ns
        except OSError:
            return "0"
        entry = _STATIC_HASHES.get(filename)
        if entry and entry[0] == mtime:
            return entry[1]
        try:
            with open(path, "rb") as f:
                digest = hashlib.md5(f.read()).hexdigest()[:8]
        except OSError:
            return "0"
        _STATIC_HASHES[filename] = (mtime, digest)
        return digest

    return {"version": version}


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
        tag_name = (json_data().get("tag") or "").strip()[:MAX_TAG_LENGTH]
        if tag_name:
            try:
                Tag.create(db, name=tag_name)
            except sqlite3.IntegrityError:
                pass
        return jsonify({"ok": True})
    return render_template('nmget.html')


@app.route('/config')
def config():
    return render_template('config.html')


@app.route('/config/export')
def config_export():
    if not os.path.exists(DB_PATH):
        return jsonify({"ok": False, "error": "database not found"}), 404
    return send_file(
        DB_PATH,
        as_attachment=True,
        download_name="nmget.db",
        mimetype="application/octet-stream",
    )


@app.route('/config/import', methods=['POST'])
def config_import():
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"ok": False, "error": "no file"}), 400

    tmp = os.path.join(BASE_DIR, "instance", "nmget-import.tmp")
    file.save(tmp)

    try:
        with sqlite3.connect(tmp) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        if not {"tag", "numbers", "queue"}.issubset(tables):
            return jsonify({"ok": False, "error": "invalid database"}), 400
    except sqlite3.Error:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return jsonify({"ok": False, "error": "invalid file"}), 400

    backup = os.path.join(BASE_DIR, "instance", "nmget.db.bak")
    if os.path.exists(DB_PATH):
        os.replace(DB_PATH, backup)
    os.replace(tmp, DB_PATH)
    db._initialize()
    return jsonify({"ok": True})


@app.route('/tags', methods=['GET'])
def list_tags():
    return jsonify({"tags": [tag.name for tag in TagName.all(db)]})


@app.route('/tags', methods=['POST'])
def create_tag():
    name = (json_data().get("name") or "").strip()[:MAX_TAG_LENGTH]
    if not name:
        return jsonify({"ok": False, "error": "empty name"}), 400
    try:
        TagName.create(db, name=name)
    except sqlite3.IntegrityError:
        return jsonify({"ok": False, "error": "duplicate"}), 409
    return jsonify({"ok": True, "name": name})


@app.after_request
def add_cors(response):
    if request.path == "/phones":
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    if request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    else:
        response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(Exception)
def handle_error(error):
    if isinstance(error, HTTPException):
        return error
    app.logger.exception("Unhandled error: %s", error)
    return jsonify({"ok": False, "error": "internal error"}), 500


@app.route('/queue')
def queue_stats():
    return jsonify({"items": Queue.stats(db)})


@app.route('/queue/send', methods=['POST'])
def queue_send():
    tag = json_data().get("tag")
    if tag:
        Queue.move_tag(db, tag)
    else:
        Queue.move_to_numbers(db)
    return jsonify({"ok": True})


@app.route('/queue/clear', methods=['POST'])
def queue_clear():
    tag = json_data().get("tag")
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
        number = digits(number)
        if MIN_DIGITS <= len(number) <= MAX_DIGITS:
            numbers.add(number)

    Queue.add_numbers(db, tag_name, numbers)
    return jsonify({"ok": True})


def wa_number(number):
    digits_number = digits(number)
    if digits_number.startswith("55"):
        return digits_number
    return "55" + digits_number


def esc_html(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_whatsapp_html(tag, numbers, dark=False):
    items = "\n".join(
        f'        <li>\n'
        f'            <a href="https://wa.me/{wa_number(number)}" target="_blank">\n'
        f'                +55 {number}\n'
        f'            </a>\n'
        f'        </li>'
        for number in numbers
    )
    if dark:
        bg, text, link, visited = "#000000", "#e5e5e5", "#66b3ff", "#ff5252"
    else:
        bg, text, link, visited = "#ffffff", "#222222", "#0645ad", "#cc0000"
    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Lista de WhatsApp - {esc_html(tag)}</title>
    <style>
        body {{
            font-family: system-ui, sans-serif;
            line-height: 1.8;
            padding: 20px;
            background: {bg};
            color: {text};
        }}
        h2 {{
            font-size: 20px;
        }}
        ol {{
            padding-left: 24px;
        }}
        li {{
            padding: 4px 0;
        }}
        a {{
            color: {link};
            text-decoration: none;
            cursor: pointer;
        }}
        a:visited,
        a.clicked {{
            color: {visited};
            text-decoration: line-through;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>

    <h2>Lista de números - {esc_html(tag)}</h2>

    <ol>
{items}
    </ol>

    <script>
        (() => {{
            const KEY = "nmget-clicked";
            let clicked = new Set();
            try {{
                clicked = new Set(JSON.parse(localStorage.getItem(KEY) || "[]"));
            }} catch (e) {{}}

            const paint = (a) => {{
                if (clicked.has(a.href)) a.classList.add("clicked");
            }};

            const track = (a) => {{
                clicked.add(a.href);
                a.classList.add("clicked");
                try {{
                    localStorage.setItem(KEY, JSON.stringify([...clicked]));
                }} catch (e) {{}}
            }};

            document.querySelectorAll("a").forEach((a) => {{
                paint(a);
                a.addEventListener("click", () => track(a));
            }});
        }})();
    </script>
</body>
</html>
'''


@app.route('/ngenerate')
def ngenerate():
    return render_template('ngenerate.html')


@app.route('/ngenerate/tags')
def ngenerate_tags():
    return jsonify({"items": Number.pending_counts(db)})


@app.route('/ngenerate/generate', methods=['POST'])
def ngenerate_generate():
    data = json_data()
    tag = (data.get("tag") or "").strip()
    try:
        limit = max(1, min(int(data.get("quantity", 10)), 5000))
    except (TypeError, ValueError):
        limit = 10
    numbers = Number.pending_for_tag(db, tag, limit)
    dark = bool(data.get("dark"))
    html = build_whatsapp_html(tag, numbers, dark=dark)
    return jsonify({
        "ok": True,
        "tag": tag,
        "count": len(numbers),
        "numbers": numbers,
        "html": html,
    })


@app.route('/ngenerate/download', methods=['POST'])
def ngenerate_download():
    data = request.get_json(silent=True)
    if data is None:
        try:
            data = json.loads(request.form.get("payload", "{}"))
        except ValueError:
            data = {}
    data = data or {}
    tag = (data.get("tag") or "").strip()
    numbers = [
        n for n in (data.get("numbers") or [])
        if re.fullmatch(r"\d+", str(n))
    ]
    Number.mark_sent(db, numbers)
    dark = bool(data.get("dark"))
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", tag).strip("-") or "lista"
    response = make_response(build_whatsapp_html(tag, numbers, dark=dark))
    response.mimetype = "text/html"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="lista-{safe}.html"'
    )
    return response


if __name__ == "__main__":
    db._initialize()
    app.run(debug=True)
