import sqlite3

from flask import Blueprint, jsonify, request

from app.db import (
    MAX_DIGITS,
    MIN_DIGITS,
    Queue,
    Tag,
    cache_bust,
    db,
    digits,
    json_data,
)

phones_bp = Blueprint("phones", __name__)


@phones_bp.after_request
def allow_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response


@phones_bp.route("/phones", methods=["POST", "OPTIONS"])
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
    cache_bust("queue_stats", "dashboard_stats", "pending_counts")
    return jsonify({"ok": True})
