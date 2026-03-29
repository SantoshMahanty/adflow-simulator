from flask import Blueprint, render_template

from ..models import KeyValueKey, Placement, User
from ..services import get_dashboard_data, login_required


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    data = get_dashboard_data()
    return render_template("dashboard/index.html", page_title="Dashboard", dashboard=data)


@dashboard_bp.route("/settings")
@login_required
def settings():
    settings_summary = {
        "users": User.query.count(),
        "placements": Placement.query.count(),
        "key_value_keys": KeyValueKey.query.count(),
    }
    return render_template("dashboard/settings.html", page_title="Settings", settings_summary=settings_summary)
