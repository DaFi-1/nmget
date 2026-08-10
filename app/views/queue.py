from flask import Blueprint, jsonify

from app.db import Queue, cache_bust, cache_get, db, json_data

queue_bp = Blueprint("queue", __name__)


@queue_bp.route("/queue")
def queue_stats():
    items = cache_get("queue_stats", 2, lambda: Queue.stats(db))
    return jsonify({"items": items})


@queue_bp.route("/queue/send", methods=["POST"])
def queue_send():
    tag = json_data().get("tag")
    if tag:
        Queue.move_tag(db, tag)
    else:
        Queue.move_to_numbers(db)
    cache_bust("queue_stats", "dashboard_stats", "pending_counts")
    return jsonify({"ok": True})


@queue_bp.route("/queue/clear", methods=["POST"])
def queue_clear():
    tag = json_data().get("tag")
    if tag:
        Queue.clear_tag(db, tag)
    else:
        Queue.clear_all(db)
    cache_bust("queue_stats", "dashboard_stats", "pending_counts")
    return jsonify({"ok": True})
