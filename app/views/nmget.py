import sqlite3

from flask import Blueprint, jsonify, render_template, request

from app.db import (
    BUST_ALL,
    BUST_STATS,
    MAX_TAG_LENGTH,
    Queue,
    Tag,
    TagName,
    cache_bust,
    cache_get,
    db,
    json_data,
)

nmget_bp = Blueprint("nmget", __name__)


@nmget_bp.route("/nmget", methods=["GET", "POST"])
def nmget():
    if request.method == "POST":
        tag_name = (json_data().get("tag") or "").strip()[:MAX_TAG_LENGTH]
        if tag_name:
            try:
                Tag.create(db, name=tag_name)
            except sqlite3.IntegrityError:
                pass
            cache_bust(*BUST_ALL)
        return jsonify({"ok": True})
    return render_template("pages/nmget.html")


@nmget_bp.route("/tag/current")
def current_tag():
    tag = Tag.current(db)
    return jsonify({"tag": tag.name})


@nmget_bp.route("/tag/current", methods=["DELETE"])
def delete_current_tag():
    tag = Tag.current(db)
    if tag.name != "EMPTY":
        Tag.delete(db, tag.name)
        cache_bust(*BUST_ALL)
    return jsonify({"tag": "EMPTY"})


@nmget_bp.route("/tags", methods=["GET"])
def list_tags():
    tags = cache_get("tags", 5, lambda: [t.name for t in TagName.all(db)])
    return jsonify({"tags": tags})


@nmget_bp.route("/tags", methods=["POST"])
def create_tag():
    name = (json_data().get("name") or "").strip()[:MAX_TAG_LENGTH]
    if not name:
        return jsonify({"ok": False, "error": "empty name"}), 400
    try:
        TagName.create(db, name=name)
    except sqlite3.IntegrityError:
        return jsonify({"ok": False, "error": "duplicate"}), 409
    cache_bust(*BUST_ALL)
    return jsonify({"ok": True, "name": name})
