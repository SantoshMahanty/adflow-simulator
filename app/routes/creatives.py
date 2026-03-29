from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..models import Creative, LineItem, db
from ..services import log_activity, login_required
from ..services.helpers import parse_int


CREATIVE_FORMATS = ["display", "video", "native", "ctv"]
CREATIVE_STATUSES = ["approved", "pending", "rejected", "broken"]


creatives_bp = Blueprint("creatives", __name__, url_prefix="/creatives")


@creatives_bp.route("/")
@login_required
def index():
    query = Creative.query.join(Creative.line_item)
    search = request.args.get("q", "").strip()
    approval_status = request.args.get("approval_status", "").strip()

    if search:
        query = query.filter(Creative.name.ilike(f"%{search}%"))
    if approval_status:
        query = query.filter(Creative.approval_status == approval_status)

    creatives = query.order_by(Creative.created_at.desc()).all()
    return render_template(
        "creatives/index.html",
        page_title="Creatives",
        creatives=creatives,
        statuses=CREATIVE_STATUSES,
        filters={"q": search, "approval_status": approval_status},
    )


@creatives_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    creative = Creative(approval_status="pending", is_active=True, creative_format="display")
    line_items = LineItem.query.order_by(LineItem.name.asc()).all()
    if request.method == "POST":
        populate_creative(creative, request.form)
        if validate_creative(creative):
            db.session.add(creative)
            db.session.commit()
            log_activity("creative", creative.id, "created", f"Creative {creative.name} created.")
            flash("Creative created successfully.", "success")
            return redirect(url_for("creatives.index"))

    return render_template(
        "creatives/form.html",
        page_title="Create Creative",
        creative=creative,
        line_items=line_items,
        formats=CREATIVE_FORMATS,
        statuses=CREATIVE_STATUSES,
        mode="create",
    )


@creatives_bp.route("/<int:creative_id>/edit", methods=["GET", "POST"])
@login_required
def edit(creative_id):
    creative = Creative.query.get_or_404(creative_id)
    line_items = LineItem.query.order_by(LineItem.name.asc()).all()
    if request.method == "POST":
        populate_creative(creative, request.form)
        if validate_creative(creative):
            db.session.commit()
            log_activity("creative", creative.id, "updated", f"Creative {creative.name} updated.")
            flash("Creative updated successfully.", "success")
            return redirect(url_for("creatives.index"))

    return render_template(
        "creatives/form.html",
        page_title="Edit Creative",
        creative=creative,
        line_items=line_items,
        formats=CREATIVE_FORMATS,
        statuses=CREATIVE_STATUSES,
        mode="edit",
    )


@creatives_bp.route("/<int:creative_id>/delete", methods=["POST"])
@login_required
def delete(creative_id):
    creative = Creative.query.get_or_404(creative_id)
    name = creative.name
    db.session.delete(creative)
    db.session.commit()
    log_activity("creative", creative_id, "deleted", f"Creative {name} deleted.")
    flash("Creative deleted.", "success")
    return redirect(url_for("creatives.index"))


def populate_creative(creative, form):
    creative.name = form.get("name", "").strip()
    creative.line_item_id = parse_int(form.get("line_item_id"), None)
    creative.creative_format = form.get("creative_format", "display")
    creative.size = form.get("size", "").strip()
    creative.destination_url = form.get("destination_url", "").strip()
    creative.approval_status = form.get("approval_status", "pending")
    creative.tag_snippet = form.get("tag_snippet", "").strip()
    creative.preview_text = form.get("preview_text", "").strip()
    creative.is_active = form.get("is_active") == "on"


def validate_creative(creative):
    if not creative.name or not creative.line_item_id or not creative.size:
        flash("Creative name, linked line item, and size are required.", "error")
        return False
    return True
