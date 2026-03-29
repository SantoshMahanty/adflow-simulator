from flask import Blueprint, render_template

from ..services import get_report_data, login_required


reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
@login_required
def index():
    return render_template("reports/index.html", page_title="Reports", reports=get_report_data())
