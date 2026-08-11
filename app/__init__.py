import hashlib
import os

from flask import Flask, jsonify, request

from app.db import BASE_DIR, db
from app.views import all_blueprints
from werkzeug.exceptions import HTTPException

_STATIC_HASHES = {}


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
    )

    for blueprint in all_blueprints:
        app.register_blueprint(blueprint)

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

    @app.after_request
    def add_cache_headers(response):
        cache = "public, max-age=31536000, immutable" if request.path.startswith("/static/") else "no-store"
        response.headers["Cache-Control"] = cache
        return response

    @app.errorhandler(Exception)
    def handle_error(error):
        if isinstance(error, HTTPException):
            return error
        app.logger.exception("Unhandled error: %s", error)
        return jsonify({"ok": False, "error": "internal error"}), 500

    return app
