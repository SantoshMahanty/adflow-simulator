from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..models import KeyValueKey, KeyValueValue, LineItemTargeting, db
from ..services import log_activity, login_required
from ..services.helpers import parse_int


key_values_bp = Blueprint("key_values", __name__, url_prefix="/key-values")


@key_values_bp.route("/")
@login_required
def index():
    search = request.args.get("q", "").strip()
    selected_id = request.args.get("key_id", "").strip()
    query = KeyValueKey.query
    if search:
        query = query.filter(KeyValueKey.name.ilike(f"%{search}%"))
    keys = query.order_by(KeyValueKey.name.asc()).all()
    selected_key_id = parse_int(selected_id, None)
    selected_key = KeyValueKey.query.get(selected_key_id) if selected_key_id else (keys[0] if keys else None)
    related_line_items = []
    if selected_key:
        related_line_items = (
            db.session.query(LineItemTargeting)
            .join(LineItemTargeting.key_value_value)
            .filter(KeyValueValue.key_id == selected_key.id)
            .all()
        )
    return render_template(
        "key_values/index.html",
        page_title="Key Values",
        keys=keys,
        selected_key=selected_key,
        related_line_items=related_line_items,
        filters={"q": search},
    )


@key_values_bp.route("/keys/new", methods=["POST"])
@login_required
def create_key():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    existing = KeyValueKey.query.filter(KeyValueKey.name.ilike(name)).first() if name else None
    if not name:
        flash("Key name is required.", "error")
    elif existing:
        flash("That key already exists.", "error")
    else:
        key = KeyValueKey(name=name, description=description)
        db.session.add(key)
        db.session.commit()
        log_activity("key_value_key", key.id, "created", f"Key {key.name} created.")
        flash("Key created successfully.", "success")
    return redirect(url_for("key_values.index"))


@key_values_bp.route("/values/new", methods=["POST"])
@login_required
def create_value():
    key_id = request.form.get("key_id")
    value = request.form.get("value", "").strip()
    description = request.form.get("description", "").strip()
    parsed_key_id = parse_int(key_id, None)
    existing = (
        KeyValueValue.query.filter_by(key_id=parsed_key_id, value=value).first()
        if parsed_key_id is not None and value
        else None
    )
    if parsed_key_id is None or not value:
        flash("Key and value are required.", "error")
    elif existing:
        flash("That value already exists for the selected key.", "error")
    else:
        row = KeyValueValue(key_id=parsed_key_id, value=value, description=description)
        db.session.add(row)
        db.session.commit()
        log_activity("key_value_value", row.id, "created", f"Value {row.value} created.")
        flash("Value created successfully.", "success")
    return redirect(url_for("key_values.index", key_id=key_id))
