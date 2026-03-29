from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..models import Advertiser, db
from ..services import log_activity, login_required


advertisers_bp = Blueprint("advertisers", __name__, url_prefix="/advertisers")


@advertisers_bp.route("/")
@login_required
def index():
    query = Advertiser.query
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()

    if search:
        query = query.filter(Advertiser.name.ilike(f"%{search}%"))
    if status:
        query = query.filter_by(status=status)

    advertisers = query.order_by(Advertiser.created_at.desc()).all()
    return render_template(
        "advertisers/index.html",
        page_title="Advertisers",
        advertisers=advertisers,
        filters={"q": search, "status": status},
    )


@advertisers_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    advertiser = Advertiser(status="active")
    if request.method == "POST":
        advertiser.name = request.form.get("name", "").strip()
        advertiser.vertical = request.form.get("vertical", "").strip()
        advertiser.status = request.form.get("status", "active")

        existing = Advertiser.query.filter(Advertiser.name.ilike(advertiser.name)).first() if advertiser.name else None
        if not advertiser.name or not advertiser.vertical:
            flash("Name and vertical are required.", "error")
        elif existing:
            flash("An advertiser with this name already exists.", "error")
        else:
            db.session.add(advertiser)
            db.session.commit()
            log_activity("advertiser", advertiser.id, "created", f"Advertiser {advertiser.name} created.")
            flash("Advertiser created successfully.", "success")
            return redirect(url_for("advertisers.index"))

    return render_template("advertisers/form.html", page_title="Create Advertiser", advertiser=advertiser, mode="create")


@advertisers_bp.route("/<int:advertiser_id>")
@login_required
def detail(advertiser_id):
    advertiser = Advertiser.query.get_or_404(advertiser_id)
    return render_template("advertisers/detail.html", page_title=advertiser.name, advertiser=advertiser)


@advertisers_bp.route("/<int:advertiser_id>/edit", methods=["GET", "POST"])
@login_required
def edit(advertiser_id):
    advertiser = Advertiser.query.get_or_404(advertiser_id)
    if request.method == "POST":
        advertiser.name = request.form.get("name", "").strip()
        advertiser.vertical = request.form.get("vertical", "").strip()
        advertiser.status = request.form.get("status", "active")

        existing = (
            Advertiser.query.filter(Advertiser.name.ilike(advertiser.name), Advertiser.id != advertiser.id).first()
            if advertiser.name
            else None
        )
        if not advertiser.name or not advertiser.vertical:
            flash("Name and vertical are required.", "error")
        elif existing:
            flash("An advertiser with this name already exists.", "error")
        else:
            db.session.commit()
            log_activity("advertiser", advertiser.id, "updated", f"Advertiser {advertiser.name} updated.")
            flash("Advertiser updated successfully.", "success")
            return redirect(url_for("advertisers.detail", advertiser_id=advertiser.id))

    return render_template("advertisers/form.html", page_title="Edit Advertiser", advertiser=advertiser, mode="edit")


@advertisers_bp.route("/<int:advertiser_id>/delete", methods=["POST"])
@login_required
def delete(advertiser_id):
    advertiser = Advertiser.query.get_or_404(advertiser_id)
    name = advertiser.name
    db.session.delete(advertiser)
    db.session.commit()
    log_activity("advertiser", advertiser_id, "deleted", f"Advertiser {name} deleted.")
    flash("Advertiser deleted.", "success")
    return redirect(url_for("advertisers.index"))
