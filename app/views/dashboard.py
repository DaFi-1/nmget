from flask import Blueprint, jsonify, redirect, render_template, url_for

from app.db import Number, cache_get, db

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def home():
    return redirect(url_for("dashboard.dashboard"))


@dashboard_bp.route("/dashboard")
def dashboard():
    return render_template("pages/dashboard.html")


@dashboard_bp.route("/dashboard/data")
def dashboard_data():
    data = cache_get("dashboard_stats", 3, lambda: Number.stats(db))
    return jsonify(data)
