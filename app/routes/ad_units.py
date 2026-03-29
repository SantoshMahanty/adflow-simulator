from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..models import AdUnit, db
from ..services import log_activity, login_required
from ..services.helpers import parse_int


ad_units_bp = Blueprint("ad_units", __name__, url_prefix="/ad-units")


@ad_units_bp.route("/")
@login_required
def index():
    ad_units = AdUnit.query.order_by(AdUnit.path.asc()).all()
    parents = AdUnit.query.filter_by(parent_id=None).order_by(AdUnit.path.asc()).all()
    return render_template("ad_units/index.html", page_title="Ad Units", ad_units=ad_units, parent_tree=parents)


@ad_units_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    ad_unit = AdUnit(is_active=True, environment="web")
    parents = AdUnit.query.order_by(AdUnit.path.asc()).all()
    if request.method == "POST":
        populate_ad_unit(ad_unit, request.form)
        existing = AdUnit.query.filter(AdUnit.path.ilike(ad_unit.path)).first() if ad_unit.path else None
        if validate_ad_unit(ad_unit) and not existing:
            db.session.add(ad_unit)
            db.session.commit()
            log_activity("ad_unit", ad_unit.id, "created", f"Ad unit {ad_unit.path} created.")
            flash("Ad unit created successfully.", "success")
            return redirect(url_for("ad_units.index"))
        elif existing:
            flash("An ad unit with this path already exists.", "error")
    return render_template("ad_units/form.html", page_title="Create Ad Unit", ad_unit=ad_unit, parents=parents, mode="create")


@ad_units_bp.route("/<int:ad_unit_id>/edit", methods=["GET", "POST"])
@login_required
def edit(ad_unit_id):
    ad_unit = AdUnit.query.get_or_404(ad_unit_id)
    parents = AdUnit.query.filter(AdUnit.id != ad_unit.id).order_by(AdUnit.path.asc()).all()
    if request.method == "POST":
        populate_ad_unit(ad_unit, request.form)
        existing = (
            AdUnit.query.filter(AdUnit.path.ilike(ad_unit.path), AdUnit.id != ad_unit.id).first()
            if ad_unit.path
            else None
        )
        if validate_ad_unit(ad_unit) and not existing:
            db.session.commit()
            log_activity("ad_unit", ad_unit.id, "updated", f"Ad unit {ad_unit.path} updated.")
            flash("Ad unit updated successfully.", "success")
            return redirect(url_for("ad_units.index"))
        elif existing:
            flash("An ad unit with this path already exists.", "error")
    return render_template("ad_units/form.html", page_title="Edit Ad Unit", ad_unit=ad_unit, parents=parents, mode="edit")


@ad_units_bp.route("/<int:ad_unit_id>/delete", methods=["POST"])
@login_required
def delete(ad_unit_id):
    ad_unit = AdUnit.query.get_or_404(ad_unit_id)
    label = ad_unit.path
    db.session.delete(ad_unit)
    db.session.commit()
    log_activity("ad_unit", ad_unit_id, "deleted", f"Ad unit {label} deleted.")
    flash("Ad unit deleted.", "success")
    return redirect(url_for("ad_units.index"))


def populate_ad_unit(ad_unit, form):
    ad_unit.name = form.get("name", "").strip()
    ad_unit.path = form.get("path", "").strip()
    ad_unit.size_support = form.get("size_support", "").strip()
    ad_unit.environment = form.get("environment", "").strip()
    ad_unit.parent_id = parse_int(form.get("parent_id"), None)
    ad_unit.is_active = form.get("is_active") == "on"


def validate_ad_unit(ad_unit):
    if not all([ad_unit.name, ad_unit.path, ad_unit.size_support, ad_unit.environment]):
        flash("Name, path, size support, and environment are required.", "error")
        return False
    return True
