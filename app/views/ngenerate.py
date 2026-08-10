import json
import re

from flask import Blueprint, jsonify, make_response, render_template, request

from app.db import Number, cache_bust, cache_get, db, json_data

ngenerate_bp = Blueprint("ngenerate", __name__)


@ngenerate_bp.route("/ngenerate")
def ngenerate():
    return render_template("pages/ngenerate.html")


@ngenerate_bp.route("/ngenerate/tags")
def ngenerate_tags():
    items = cache_get("pending_counts", 3, lambda: Number.pending_counts(db))
    return jsonify({"items": items})


@ngenerate_bp.route("/ngenerate/generate", methods=["POST"])
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


@ngenerate_bp.route("/ngenerate/download", methods=["POST"])
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
    cache_bust("dashboard_stats", "pending_counts")
    dark = bool(data.get("dark"))
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", tag).strip("-") or "lista"
    response = make_response(build_whatsapp_html(tag, numbers, dark=dark))
    response.mimetype = "text/html"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="lista-{safe}.html"'
    )
    return response


def wa_number(number):
    digits_number = re.sub(r"\D", "", str(number))
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
