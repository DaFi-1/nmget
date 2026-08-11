import gzip
import hashlib
import os

from flask import Flask, jsonify, request

from app.db import BASE_DIR, db
from app.views import all_blueprints
from werkzeug.exceptions import HTTPException

_STATIC_HASHES = {}

_COMPRESSIBLE = ("text/", "application/json")
_MIN_GZIP_SIZE = 500


class GzipMiddleware:
    def __init__(self, app):
        self.app = app

    @staticmethod
    def _should_skip(headers):
        headers = {k.lower(): v for k, v in headers}
        if headers.get("content-encoding"):
            return True
        if headers.get("content-disposition", "").lower().startswith("attachment"):
            return True
        length = headers.get("content-length")
        if length and int(length) < _MIN_GZIP_SIZE:
            return True
        content_type = headers.get("content-type", "").split(";")[0]
        return not content_type.startswith(_COMPRESSIBLE)

    def __call__(self, environ, start_response):
        if "gzip" not in environ.get("HTTP_ACCEPT_ENCODING", ""):
            return self.app(environ, start_response)

        state = {}

        def capture(status, headers, exc_info=None):
            state.update(status=status, headers=headers, exc_info=exc_info)

        body = b"".join(self.app(environ, capture))

        if state.get("skip") is None:
            state["skip"] = self._should_skip(state.get("headers") or [])
        if state["skip"]:
            start_response(state["status"], state["headers"], state.get("exc_info"))
            return [body]

        compressed = gzip.compress(body, 6)
        headers = [
            (name, value)
            for name, value in state["headers"]
            if name.lower() not in ("content-length", "content-encoding")
        ]
        headers.append(("Content-Encoding", "gzip"))
        headers.append(("Content-Length", str(len(compressed))))
        headers.append(("Vary", "Accept-Encoding"))
        start_response(state["status"], headers, state.get("exc_info"))
        return [compressed]


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
    )
    app.wsgi_app = GzipMiddleware(app.wsgi_app)

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
