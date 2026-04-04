from datetime import date

from sqlalchemy.orm import joinedload, selectinload

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..models import AdUnit, Advertiser, KeyValueValue, LineItem, LineItemTargeting, Order, db
from ..services import (
    WORKFLOW_STATES,
    apply_workflow_state,
    evaluate_line_item,
    launch_line_item,
    log_activity,
    login_required,
    validate_launch,
)
from ..services.helpers import parse_date, parse_decimal, parse_int


LINE_ITEM_TYPES = [
    "Sponsorship",
    "Standard",
    "Preferred Deal",
    "Programmatic Guaranteed",
    "AdX/Price Priority",
    "Network",
    "House",
]

LINE_ITEM_STATUSES = ["draft", "active", "live", "paused", "completed", "archived"]
PAGE_TYPE_TARGETS = ["home", "article", "category"]
SLOT_POSITION_TARGETS = ["top", "sidebar", "in_article", "footer", "video"]


line_items_bp = Blueprint("line_items", __name__, url_prefix="/line-items")


def default_request_context(line_item):
    ad_unit_rule = next((rule for rule in line_item.targeting_rules if rule.target_type == "ad_unit"), None)
    page_type_rule = next((rule for rule in line_item.targeting_rules if rule.target_type == "page_type"), None)
    slot_position_rule = next((rule for rule in line_item.targeting_rules if rule.target_type == "slot_position"), None)
    key_values = {
        rule.key_value_value.key.name: rule.key_value_value.value
        for rule in line_item.targeting_rules
        if rule.target_type == "key_value" and rule.key_value_value
    }
    content_category_rule = next(
        (rule.target_value for rule in line_item.targeting_rules if rule.target_type == "content_category"),
        "",
    )
    return {
        "ad_unit_path": ad_unit_rule.target_value if ad_unit_rule else "",
        "device": (line_item.device_targeting or "").split(",")[0].strip(),
        "geo": (line_item.geo_targeting or "").split(",")[0].strip(),
        "audience": (line_item.audience_targeting or "").split(",")[0].strip(),
        "creative_size": line_item.creative_size,
        "content_category": content_category_rule,
        "page_type": page_type_rule.target_value if page_type_rule else "",
        "slot_position": slot_position_rule.target_value if slot_position_rule else "",
        "key_values": key_values,
    }


def sync_targeting(line_item, form):
    line_item.targeting_rules.clear()
    db.session.flush()

    for ad_unit_path in form.getlist("ad_unit_paths"):
        if ad_unit_path:
            line_item.targeting_rules.append(LineItemTargeting(target_type="ad_unit", target_value=ad_unit_path))

    for page_type in form.getlist("page_types"):
        if page_type:
            line_item.targeting_rules.append(LineItemTargeting(target_type="page_type", target_value=page_type))

    for slot_position in form.getlist("slot_positions"):
        if slot_position:
            line_item.targeting_rules.append(LineItemTargeting(target_type="slot_position", target_value=slot_position))

    content_category = form.get("content_category", "").strip()
    if content_category:
        line_item.targeting_rules.append(
            LineItemTargeting(target_type="content_category", target_value=content_category)
        )

    for value_id in form.getlist("key_value_value_ids"):
        if value_id:
            parsed_value_id = parse_int(value_id, None)
            if parsed_value_id is not None:
                line_item.targeting_rules.append(
                    LineItemTargeting(target_type="key_value", key_value_value_id=parsed_value_id)
                )


def load_form_collections():
    advertisers = Advertiser.query.order_by(Advertiser.name.asc()).all()
    orders = Order.query.order_by(Order.name.asc()).all()
    ad_units = AdUnit.query.order_by(AdUnit.path.asc()).all()
    key_value_values = KeyValueValue.query.order_by(KeyValueValue.value.asc()).all()
    return advertisers, orders, ad_units, key_value_values


@line_items_bp.route("/")
@login_required
def index():
    query = LineItem.query.join(LineItem.order).join(LineItem.advertiser)
    filters = {
        "q": request.args.get("q", "").strip(),
        "advertiser_id": request.args.get("advertiser_id", "").strip(),
        "line_item_type": request.args.get("line_item_type", "").strip(),
        "status": request.args.get("status", "").strip(),
        "workflow_state": request.args.get("workflow_state", "").strip(),
        "geo": request.args.get("geo", "").strip(),
        "device": request.args.get("device", "").strip(),
        "date_from": request.args.get("date_from", "").strip(),
        "date_to": request.args.get("date_to", "").strip(),
    }
    advertiser_id_value = parse_int(filters["advertiser_id"], None)

    if filters["q"]:
        query = query.filter(LineItem.name.ilike(f"%{filters['q']}%"))
    if advertiser_id_value is not None:
        query = query.filter(LineItem.advertiser_id == advertiser_id_value)
    if filters["line_item_type"]:
        query = query.filter(LineItem.line_item_type == filters["line_item_type"])
    if filters["status"]:
        query = query.filter(LineItem.status == filters["status"])
    if filters["workflow_state"]:
        query = query.filter(LineItem.workflow_state == filters["workflow_state"])
    if filters["geo"]:
        query = query.filter(LineItem.geo_targeting.ilike(f"%{filters['geo']}%"))
    if filters["device"]:
        query = query.filter(LineItem.device_targeting.ilike(f"%{filters['device']}%"))
    date_from = parse_date(filters["date_from"])
    date_to = parse_date(filters["date_to"])
    if date_from:
        query = query.filter(LineItem.end_date >= date_from)
    if date_to:
        query = query.filter(LineItem.start_date <= date_to)

    line_items = query.options(
        joinedload(LineItem.order),
        joinedload(LineItem.advertiser),
        selectinload(LineItem.creatives),
        selectinload(LineItem.targeting_rules)
        .joinedload(LineItemTargeting.key_value_value)
        .joinedload(KeyValueValue.key)
    ).order_by(LineItem.created_at.desc()).all()
    advertisers = Advertiser.query.order_by(Advertiser.name.asc()).all()
    eligibility_map = {}
    for line_item in line_items:
        evaluation = evaluate_line_item(line_item, default_request_context(line_item), current_day=date.today())
        eligibility_map[line_item.id] = evaluation["eligible"]

    return render_template(
        "line_items/index.html",
        page_title="Line Items",
        line_items=line_items,
        advertisers=advertisers,
        line_item_types=LINE_ITEM_TYPES,
        statuses=LINE_ITEM_STATUSES,
        workflow_states=WORKFLOW_STATES,
        page_type_targets=PAGE_TYPE_TARGETS,
        slot_position_targets=SLOT_POSITION_TARGETS,
        eligibility_map=eligibility_map,
        filters=filters,
    )


@line_items_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    line_item = LineItem(status="draft", workflow_state="Draft", line_item_type="Standard", priority=2, delivery_weight=100)
    advertisers, orders, ad_units, key_value_values = load_form_collections()
    if request.method == "POST":
        populate_line_item(line_item, request.form)
        if validate_line_item(line_item):
            db.session.add(line_item)
            db.session.flush()
            sync_targeting(line_item, request.form)
            db.session.commit()
            log_activity("line_item", line_item.id, "created", f"Line item {line_item.name} created.")
            flash("Line item created successfully.", "success")
            return redirect(url_for("line_items.detail", line_item_id=line_item.id))

    return render_template(
        "line_items/form.html",
        page_title="Create Line Item",
        line_item=line_item,
        advertisers=advertisers,
        orders=orders,
        ad_units=ad_units,
        key_value_values=key_value_values,
        line_item_types=LINE_ITEM_TYPES,
        statuses=LINE_ITEM_STATUSES,
        workflow_states=WORKFLOW_STATES,
        page_type_targets=PAGE_TYPE_TARGETS,
        slot_position_targets=SLOT_POSITION_TARGETS,
        mode="create",
    )


@line_items_bp.route("/<int:line_item_id>")
@login_required
def detail(line_item_id):
    line_item = LineItem.query.get_or_404(line_item_id)
    request_context = default_request_context(line_item)
    evaluation = evaluate_line_item(line_item, request_context)
    launch_validation = validate_launch(line_item)
    return render_template(
        "line_items/detail.html",
        page_title=line_item.name,
        line_item=line_item,
        evaluation=evaluation,
        request_context=request_context,
        launch_validation=launch_validation,
    )


@line_items_bp.route("/<int:line_item_id>/edit", methods=["GET", "POST"])
@login_required
def edit(line_item_id):
    line_item = LineItem.query.get_or_404(line_item_id)
    advertisers, orders, ad_units, key_value_values = load_form_collections()
    if request.method == "POST":
        populate_line_item(line_item, request.form)
        if validate_line_item(line_item):
            sync_targeting(line_item, request.form)
            db.session.commit()
            log_activity("line_item", line_item.id, "updated", f"Line item {line_item.name} updated.")
            flash("Line item updated successfully.", "success")
            return redirect(url_for("line_items.detail", line_item_id=line_item.id))

    return render_template(
        "line_items/form.html",
        page_title="Edit Line Item",
        line_item=line_item,
        advertisers=advertisers,
        orders=orders,
        ad_units=ad_units,
        key_value_values=key_value_values,
        line_item_types=LINE_ITEM_TYPES,
        statuses=LINE_ITEM_STATUSES,
        workflow_states=WORKFLOW_STATES,
        page_type_targets=PAGE_TYPE_TARGETS,
        slot_position_targets=SLOT_POSITION_TARGETS,
        mode="edit",
    )


@line_items_bp.route("/<int:line_item_id>/delete", methods=["POST"])
@login_required
def delete(line_item_id):
    line_item = LineItem.query.get_or_404(line_item_id)
    name = line_item.name
    db.session.delete(line_item)
    db.session.commit()
    log_activity("line_item", line_item_id, "deleted", f"Line item {name} deleted.")
    flash("Line item deleted.", "success")
    return redirect(url_for("line_items.index"))


@line_items_bp.route("/<int:line_item_id>/launch", methods=["POST"])
@login_required
def launch(line_item_id):
    line_item = LineItem.query.get_or_404(line_item_id)
    validation = launch_line_item(line_item)
    if validation["ready"]:
        log_activity("line_item", line_item.id, "launched", f"Line item {line_item.name} moved to {line_item.workflow_state}.")
        flash(f"Line item launched successfully as {line_item.workflow_state}.", "success")
    else:
        flash("Launch validation failed: " + " ".join(validation["issues"]), "error")
    return redirect(url_for("line_items.detail", line_item_id=line_item.id))


def populate_line_item(line_item, form):
    line_item.name = form.get("name", "").strip()
    line_item.advertiser_id = parse_int(form.get("advertiser_id"), None)
    line_item.order_id = parse_int(form.get("order_id"), None)
    line_item.line_item_type = form.get("line_item_type", "Standard")
    line_item.priority = parse_int(form.get("priority"), 2)
    line_item.delivery_weight = max(parse_int(form.get("delivery_weight"), 100), 1)
    line_item.start_date = parse_date(form.get("start_date"))
    line_item.end_date = parse_date(form.get("end_date"))
    line_item.goal_impressions = parse_int(form.get("goal_impressions"), 0)
    line_item.delivered_impressions = parse_int(form.get("delivered_impressions"), 0)
    line_item.cpm = parse_decimal(form.get("cpm"), "0.00")
    line_item.frequency_cap = parse_int(form.get("frequency_cap"), 0)
    line_item.creative_size = form.get("creative_size", "").strip()
    line_item.geo_targeting = form.get("geo_targeting", "").strip()
    line_item.device_targeting = form.get("device_targeting", "").strip()
    line_item.audience_targeting = form.get("audience_targeting", "").strip()
    line_item.budget_amount = parse_decimal(form.get("budget_amount"), "0.00")
    line_item.spent_amount = parse_decimal(form.get("spent_amount"), "0.00")
    line_item.daily_impression_cap = parse_int(form.get("daily_impression_cap"), 0)
    line_item.daily_spend_cap = parse_decimal(form.get("daily_spend_cap"), "0.00")
    apply_workflow_state(line_item, form.get("workflow_state", "Draft"))
    line_item.notes = form.get("notes", "").strip()


def validate_line_item(line_item):
    if not all([line_item.name, line_item.advertiser_id, line_item.order_id, line_item.start_date, line_item.end_date, line_item.creative_size]):
        flash("Please complete all required fields.", "error")
        return False
    if line_item.start_date > line_item.end_date:
        flash("Start date must be before end date.", "error")
        return False
    return True
