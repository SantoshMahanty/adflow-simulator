import csv
from io import StringIO

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for

from ..models import LineItem, TroubleshootingIssue, TroubleshootingSheetRow, db
from ..services import log_activity, login_required
from ..services.helpers import parse_date


troubleshooting_bp = Blueprint("troubleshooting", __name__, url_prefix="/troubleshooting")


@troubleshooting_bp.route("/issues")
@login_required
def issues():
    query = TroubleshootingIssue.query
    search = request.args.get("q", "").strip()
    severity = request.args.get("severity", "").strip()
    category = request.args.get("category", "").strip()
    if search:
        query = query.filter(TroubleshootingIssue.title.ilike(f"%{search}%"))
    if severity:
        query = query.filter(TroubleshootingIssue.severity == severity)
    if category:
        query = query.filter(TroubleshootingIssue.category == category)
    issues_list = query.order_by(TroubleshootingIssue.created_at.desc()).all()
    return render_template(
        "troubleshooting/issues.html",
        page_title="Issues Library",
        issues=issues_list,
        filters={"q": search, "severity": severity, "category": category},
    )


@troubleshooting_bp.route("/issues/new", methods=["GET", "POST"])
@login_required
def create_issue():
    issue = TroubleshootingIssue(severity="medium", category="Delivery", related_module="Line Items")
    if request.method == "POST":
        populate_issue(issue, request.form)
        if validate_issue(issue):
            db.session.add(issue)
            db.session.commit()
            log_activity("troubleshooting_issue", issue.id, "created", f"Issue library entry {issue.title} created.")
            flash("Issue library entry created.", "success")
            return redirect(url_for("troubleshooting.issues"))
    return render_template("troubleshooting/issue_form.html", page_title="Create Issue", issue=issue, mode="create")


@troubleshooting_bp.route("/issues/<int:issue_id>/edit", methods=["GET", "POST"])
@login_required
def edit_issue(issue_id):
    issue = TroubleshootingIssue.query.get_or_404(issue_id)
    if request.method == "POST":
        populate_issue(issue, request.form)
        if validate_issue(issue):
            db.session.commit()
            log_activity("troubleshooting_issue", issue.id, "updated", f"Issue library entry {issue.title} updated.")
            flash("Issue library entry updated.", "success")
            return redirect(url_for("troubleshooting.issues"))
    return render_template("troubleshooting/issue_form.html", page_title="Edit Issue", issue=issue, mode="edit")


@troubleshooting_bp.route("/issues/<int:issue_id>/delete", methods=["POST"])
@login_required
def delete_issue(issue_id):
    issue = TroubleshootingIssue.query.get_or_404(issue_id)
    title = issue.title
    db.session.delete(issue)
    db.session.commit()
    log_activity("troubleshooting_issue", issue_id, "deleted", f"Issue library entry {title} deleted.")
    flash("Issue library entry deleted.", "success")
    return redirect(url_for("troubleshooting.issues"))


@troubleshooting_bp.route("/sheet")
@login_required
def sheet():
    query = TroubleshootingSheetRow.query
    filters = {
        "q": request.args.get("q", "").strip(),
        "severity": request.args.get("severity", "").strip(),
        "status": request.args.get("status", "").strip(),
        "owner": request.args.get("owner", "").strip(),
    }
    if filters["q"]:
        query = query.filter(TroubleshootingSheetRow.issue_title.ilike(f"%{filters['q']}%"))
    if filters["severity"]:
        query = query.filter(TroubleshootingSheetRow.severity == filters["severity"])
    if filters["status"]:
        query = query.filter(TroubleshootingSheetRow.status == filters["status"])
    if filters["owner"]:
        query = query.filter(TroubleshootingSheetRow.owner.ilike(f"%{filters['owner']}%"))

    rows = query.order_by(TroubleshootingSheetRow.created_at.desc()).all()
    return render_template("troubleshooting/sheet.html", page_title="Troubleshooting Sheet", rows=rows, filters=filters)


@troubleshooting_bp.route("/sheet/new", methods=["GET", "POST"])
@login_required
def create_sheet_row():
    row = TroubleshootingSheetRow(status="open", severity="medium")
    line_items = LineItem.query.order_by(LineItem.name.asc()).all()
    if request.method == "POST":
        populate_sheet_row(row, request.form)
        if validate_sheet_row(row):
            db.session.add(row)
            db.session.commit()
            log_activity("troubleshooting_row", row.id, "created", f"Troubleshooting row {row.issue_title} created.")
            flash("Troubleshooting row created.", "success")
            return redirect(url_for("troubleshooting.sheet"))
    return render_template("troubleshooting/sheet_form.html", page_title="Create Sheet Row", row=row, line_items=line_items, mode="create")


@troubleshooting_bp.route("/sheet/<int:row_id>/edit", methods=["GET", "POST"])
@login_required
def edit_sheet_row(row_id):
    row = TroubleshootingSheetRow.query.get_or_404(row_id)
    line_items = LineItem.query.order_by(LineItem.name.asc()).all()
    if request.method == "POST":
        populate_sheet_row(row, request.form)
        if validate_sheet_row(row):
            db.session.commit()
            log_activity("troubleshooting_row", row.id, "updated", f"Troubleshooting row {row.issue_title} updated.")
            flash("Troubleshooting row updated.", "success")
            return redirect(url_for("troubleshooting.sheet"))
    return render_template("troubleshooting/sheet_form.html", page_title="Edit Sheet Row", row=row, line_items=line_items, mode="edit")


@troubleshooting_bp.route("/sheet/<int:row_id>/delete", methods=["POST"])
@login_required
def delete_sheet_row(row_id):
    row = TroubleshootingSheetRow.query.get_or_404(row_id)
    title = row.issue_title
    db.session.delete(row)
    db.session.commit()
    log_activity("troubleshooting_row", row_id, "deleted", f"Troubleshooting row {title} deleted.")
    flash("Troubleshooting row deleted.", "success")
    return redirect(url_for("troubleshooting.sheet"))


@troubleshooting_bp.route("/sheet/export")
@login_required
def export_sheet():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Issue Title", "Campaign", "Problem", "Possible Reason", "Where To Check", "Suggested Fix", "Severity", "Owner", "Due Date", "Status", "Notes"])
    for row in TroubleshootingSheetRow.query.order_by(TroubleshootingSheetRow.created_at.desc()).all():
        writer.writerow(
            [
                row.issue_title,
                row.campaign_name,
                row.problem,
                row.possible_reason,
                row.where_to_check,
                row.suggested_fix,
                row.severity,
                row.owner,
                row.due_date.isoformat() if row.due_date else "",
                row.status,
                row.notes or "",
            ]
        )
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=troubleshooting_sheet.csv"},
    )


def populate_issue(issue, form):
    issue.title = form.get("title", "").strip()
    issue.symptoms = form.get("symptoms", "").strip()
    issue.likely_causes = form.get("likely_causes", "").strip()
    issue.where_to_check = form.get("where_to_check", "").strip()
    issue.recommended_fix = form.get("recommended_fix", "").strip()
    issue.severity = form.get("severity", "").strip()
    issue.category = form.get("category", "").strip()
    issue.related_module = form.get("related_module", "").strip()


def validate_issue(issue):
    if not all([issue.title, issue.symptoms, issue.likely_causes, issue.where_to_check, issue.recommended_fix, issue.severity, issue.category, issue.related_module]):
        flash("All issue fields are required.", "error")
        return False
    return True


def populate_sheet_row(row, form):
    row.issue_title = form.get("issue_title", "").strip()
    row.line_item_id = parse_int(form.get("line_item_id"), None)
    row.campaign_name = form.get("campaign_name", "").strip()
    row.problem = form.get("problem", "").strip()
    row.possible_reason = form.get("possible_reason", "").strip()
    row.where_to_check = form.get("where_to_check", "").strip()
    row.suggested_fix = form.get("suggested_fix", "").strip()
    row.severity = form.get("severity", "").strip()
    row.owner = form.get("owner", "").strip()
    row.due_date = parse_date(form.get("due_date"))
    row.status = form.get("status", "").strip()
    row.notes = form.get("notes", "").strip()


def validate_sheet_row(row):
    if not all([row.issue_title, row.campaign_name, row.problem, row.possible_reason, row.where_to_check, row.suggested_fix, row.severity, row.owner, row.status]):
        flash("Please complete all required troubleshooting sheet fields.", "error")
        return False
    return True
