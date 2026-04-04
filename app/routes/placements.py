from collections import Counter

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.orm import selectinload

from ..models import AdUnit, Placement, db
from ..services import log_activity, login_required
from ..services.helpers import parse_int


placements_bp = Blueprint("placements", __name__, url_prefix="/placements")


@placements_bp.route("/")
@login_required
def index():
    placements = Placement.query.options(selectinload(Placement.ad_units)).order_by(Placement.created_at.desc()).all()

    device_counts = Counter((placement.device_type or "Unspecified").title() for placement in placements)
    format_counts = Counter((placement.placement_format or "Unspecified").title() for placement in placements)
    linked_ad_unit_ids = {ad_unit.id for placement in placements for ad_unit in placement.ad_units}

    placement_stats = {
        "total_placements": len(placements),
        "ad_unit_links": sum(len(placement.ad_units) for placement in placements),
        "unique_ad_units": len(linked_ad_unit_ids),
        "device_count": len(device_counts),
        "format_count": len(format_counts),
    }

    busiest_placements = sorted(placements, key=lambda placement: len(placement.ad_units), reverse=True)[:3]

    return render_template(
        "placements/index.html",
        page_title="Placements",
        placements=placements,
        placement_stats=placement_stats,
        device_breakdown=device_counts.most_common(4),
        format_breakdown=format_counts.most_common(4),
        busiest_placements=busiest_placements,
    )


@placements_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    placement = Placement(device_type="desktop", placement_format="display")
    ad_units = AdUnit.query.order_by(AdUnit.path.asc()).all()
    if request.method == "POST":
        populate_placement(placement, request.form)
        if validate_placement(placement):
            selected_ids = [parse_int(item, None) for item in request.form.getlist("ad_unit_ids") if item]
            selected_ids = [item for item in selected_ids if item is not None]
            placement.ad_units = AdUnit.query.filter(AdUnit.id.in_(selected_ids)).all() if selected_ids else []
            db.session.add(placement)
            db.session.commit()
            log_activity("placement", placement.id, "created", f"Placement {placement.name} created.")
            flash("Placement created successfully.", "success")
            return redirect(url_for("placements.index"))
    return render_template("placements/form.html", page_title="Create Placement", placement=placement, ad_units=ad_units, mode="create")


@placements_bp.route("/<int:placement_id>/edit", methods=["GET", "POST"])
@login_required
def edit(placement_id):
    placement = Placement.query.get_or_404(placement_id)
    ad_units = AdUnit.query.order_by(AdUnit.path.asc()).all()
    if request.method == "POST":
        populate_placement(placement, request.form)
        if validate_placement(placement):
            selected_ids = [parse_int(item, None) for item in request.form.getlist("ad_unit_ids") if item]
            selected_ids = [item for item in selected_ids if item is not None]
            placement.ad_units = AdUnit.query.filter(AdUnit.id.in_(selected_ids)).all() if selected_ids else []
            db.session.commit()
            log_activity("placement", placement.id, "updated", f"Placement {placement.name} updated.")
            flash("Placement updated successfully.", "success")
            return redirect(url_for("placements.index"))
    return render_template("placements/form.html", page_title="Edit Placement", placement=placement, ad_units=ad_units, mode="edit")


@placements_bp.route("/<int:placement_id>/delete", methods=["POST"])
@login_required
def delete(placement_id):
    placement = Placement.query.get_or_404(placement_id)
    name = placement.name
    db.session.delete(placement)
    db.session.commit()
    log_activity("placement", placement_id, "deleted", f"Placement {name} deleted.")
    flash("Placement deleted.", "success")
    return redirect(url_for("placements.index"))


def populate_placement(placement, form):
    placement.name = form.get("name", "").strip()
    placement.device_type = form.get("device_type", "").strip()
    placement.placement_format = form.get("placement_format", "").strip()
    placement.notes = form.get("notes", "").strip()


def validate_placement(placement):
    if not placement.name or not placement.device_type or not placement.placement_format:
        flash("Placement name, device type, and format are required.", "error")
        return False
    return True
