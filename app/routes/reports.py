import csv
from io import StringIO

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for

from ..services import build_report_export, get_available_report_types, get_report_data, login_required
from ..services.helpers import parse_date


reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def parse_report_filters():
    filters = {
        "report_type": request.args.get("report_type", "summary").strip() or "summary",
        "date_from": request.args.get("date_from", "").strip(),
        "date_to": request.args.get("date_to", "").strip(),
    }
    date_from = parse_date(filters["date_from"])
    date_to = parse_date(filters["date_to"])
    if filters["date_from"] and not date_from:
        flash("Invalid start date. Please use YYYY-MM-DD.", "error")
        filters["date_from"] = ""
    if filters["date_to"] and not date_to:
        flash("Invalid end date. Please use YYYY-MM-DD.", "error")
        filters["date_to"] = ""
    date_from = parse_date(filters["date_from"])
    date_to = parse_date(filters["date_to"])
    if date_from and date_to and date_from > date_to:
        flash("Start date cannot be after end date.", "error")
        filters["date_from"] = ""
        filters["date_to"] = ""
        date_from = None
        date_to = None
    return filters, date_from, date_to


@reports_bp.route("/")
@login_required
def index():
    filters, date_from, date_to = parse_report_filters()
    report_types = get_available_report_types()
    return render_template(
        "reports/index.html",
        page_title="Reports",
        reports=get_report_data(date_from=date_from, date_to=date_to),
        report_types=report_types,
        filters=filters,
    )


@reports_bp.route("/export")
@login_required
def export():
    filters, date_from, date_to = parse_report_filters()
    export_data = build_report_export(filters["report_type"], date_from=date_from, date_to=date_to)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(export_data["headers"])
    writer.writerows(export_data["rows"])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={export_data['filename']}"},
    )
