from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..models import Advertiser, Order, db
from ..services import log_activity, login_required
from ..services.helpers import parse_date, parse_int


orders_bp = Blueprint("orders", __name__, url_prefix="/orders")


@orders_bp.route("/")
@login_required
def index():
    query = Order.query.join(Order.advertiser)
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    advertiser_id = request.args.get("advertiser_id", "").strip()
    advertiser_id_value = parse_int(advertiser_id, None)

    if search:
        query = query.filter(Order.name.ilike(f"%{search}%"))
    if status:
        query = query.filter(Order.status == status)
    if advertiser_id_value is not None:
        query = query.filter(Order.advertiser_id == advertiser_id_value)

    orders = query.order_by(Order.created_at.desc()).all()
    advertisers = Advertiser.query.order_by(Advertiser.name.asc()).all()
    return render_template(
        "orders/index.html",
        page_title="Orders",
        orders=orders,
        advertisers=advertisers,
        filters={"q": search, "status": status, "advertiser_id": advertiser_id},
    )


@orders_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    order = Order(status="active")
    advertisers = Advertiser.query.order_by(Advertiser.name.asc()).all()
    if request.method == "POST":
        order.name = request.form.get("name", "").strip()
        order.advertiser_id = parse_int(request.form.get("advertiser_id"), None)
        order.start_date = parse_date(request.form.get("start_date"))
        order.end_date = parse_date(request.form.get("end_date"))
        order.status = request.form.get("status", "active")
        order.notes = request.form.get("notes", "").strip()

        if not order.name or not order.advertiser_id or not order.start_date or not order.end_date:
            flash("Order name, advertiser, and dates are required.", "error")
        elif order.start_date > order.end_date:
            flash("Start date must be before end date.", "error")
        else:
            db.session.add(order)
            db.session.commit()
            log_activity("order", order.id, "created", f"Order {order.name} created.")
            flash("Order created successfully.", "success")
            return redirect(url_for("orders.index"))

    return render_template("orders/form.html", page_title="Create Order", order=order, advertisers=advertisers, mode="create")


@orders_bp.route("/<int:order_id>")
@login_required
def detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("orders/detail.html", page_title=order.name, order=order)


@orders_bp.route("/<int:order_id>/edit", methods=["GET", "POST"])
@login_required
def edit(order_id):
    order = Order.query.get_or_404(order_id)
    advertisers = Advertiser.query.order_by(Advertiser.name.asc()).all()
    if request.method == "POST":
        order.name = request.form.get("name", "").strip()
        order.advertiser_id = parse_int(request.form.get("advertiser_id"), None)
        order.start_date = parse_date(request.form.get("start_date"))
        order.end_date = parse_date(request.form.get("end_date"))
        order.status = request.form.get("status", "active")
        order.notes = request.form.get("notes", "").strip()

        if not order.name or not order.advertiser_id or not order.start_date or not order.end_date:
            flash("Order name, advertiser, and dates are required.", "error")
        elif order.start_date > order.end_date:
            flash("Start date must be before end date.", "error")
        else:
            db.session.commit()
            log_activity("order", order.id, "updated", f"Order {order.name} updated.")
            flash("Order updated successfully.", "success")
            return redirect(url_for("orders.detail", order_id=order.id))

    return render_template("orders/form.html", page_title="Edit Order", order=order, advertisers=advertisers, mode="edit")


@orders_bp.route("/<int:order_id>/delete", methods=["POST"])
@login_required
def delete(order_id):
    order = Order.query.get_or_404(order_id)
    name = order.name
    db.session.delete(order)
    db.session.commit()
    log_activity("order", order_id, "deleted", f"Order {name} deleted.")
    flash("Order deleted.", "success")
    return redirect(url_for("orders.index"))
