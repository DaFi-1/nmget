from app.views.config import config_bp
from app.views.dashboard import dashboard_bp
from app.views.ngenerate import ngenerate_bp
from app.views.nmget import nmget_bp
from app.views.phones import phones_bp
from app.views.queue import queue_bp

all_blueprints = [
    dashboard_bp,
    nmget_bp,
    queue_bp,
    phones_bp,
    ngenerate_bp,
    config_bp,
]
