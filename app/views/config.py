import os
import sqlite3

from flask import Blueprint, jsonify, render_template, request, send_file

from app.db import BUST_ALL, DB_PATH, BASE_DIR, cache_bust, db

config_bp = Blueprint("config", __name__)


def _remove_quietly(path):
    try:
        os.remove(path)
    except OSError:
        pass


def _cleanup(db_path):
    for suffix in ("-wal", "-shm"):
        _remove_quietly(db_path + suffix)


@config_bp.route("/config")
def config():
    return render_template("pages/config.html")


@config_bp.route("/config/export")
def config_export():
    if not os.path.exists(DB_PATH):
        return jsonify({"ok": False, "error": "database not found"}), 404
    connection = db._connect()
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    connection.close()
    return send_file(
        DB_PATH,
        as_attachment=True,
        download_name="nmget.db",
        mimetype="application/octet-stream",
    )


@config_bp.route("/config/import", methods=["POST"])
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
            _cleanup(tmp)
            return jsonify({"ok": False, "error": "invalid database"}), 400
    except sqlite3.Error:
        _cleanup(tmp)
        return jsonify({"ok": False, "error": "invalid file"}), 400

    backup = os.path.join(BASE_DIR, "instance", "nmget.db.bak")
    if os.path.exists(DB_PATH):
        os.replace(DB_PATH, backup)
        _cleanup(backup)
    os.replace(tmp, DB_PATH)
    _cleanup(tmp)
    db._initialize()
    cache_bust(*BUST_ALL)
    return jsonify({"ok": True})
