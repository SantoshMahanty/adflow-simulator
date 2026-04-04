from flask import Blueprint, jsonify, request

from ..models import Advertiser, Creative, LineItem, Order, db
from ..routes.creatives import populate_creative, validate_creative
from ..routes.line_items import populate_line_item, sync_targeting, validate_line_item
from ..services import launch_line_item
from ..services.helpers import parse_date, parse_decimal, parse_int
from ..services.reporting import get_report_data


api_bp = Blueprint("api", __name__)


@api_bp.route("/advertisers", methods=["POST"])
def create_advertiser_api():
    payload = request.get_json(silent=True) or {}
    advertiser = Advertiser(
        name=(payload.get("name") or "").strip(),
        vertical=(payload.get("vertical") or "").strip(),
        status=(payload.get("status") or "active").strip() or "active",
    )
    if not advertiser.name or not advertiser.vertical:
        return jsonify({"ok": False, "error": "name and vertical are required"}), 400
    db.session.add(advertiser)
    db.session.commit()
    return jsonify({"ok": True, "id": advertiser.id, "name": advertiser.name}), 201


@api_bp.route("/orders", methods=["POST"])
def create_order_api():
    payload = request.get_json(silent=True) or {}
    order = Order(
        advertiser_id=parse_int(payload.get("advertiser_id"), None),
        name=(payload.get("name") or "").strip(),
        start_date=parse_date(payload.get("start_date")),
        end_date=parse_date(payload.get("end_date")),
        status=(payload.get("status") or "active").strip() or "active",
        workflow_state=(payload.get("workflow_state") or "Draft").strip() or "Draft",
        budget_amount=parse_decimal(payload.get("budget_amount"), "0.00"),
        notes=(payload.get("notes") or "").strip(),
    )
    if not order.name or not order.advertiser_id or not order.start_date or not order.end_date:
        return jsonify({"ok": False, "error": "name, advertiser_id, start_date, and end_date are required"}), 400
    db.session.add(order)
    db.session.commit()
    return jsonify({"ok": True, "id": order.id, "name": order.name}), 201


@api_bp.route("/line-items", methods=["POST"])
def create_line_item_api():
    payload = request.get_json(silent=True) or {}
    line_item = LineItem()
    populate_line_item(line_item, payload)
    if not validate_line_item(line_item):
        return jsonify({"ok": False, "error": "invalid line item payload"}), 400
    db.session.add(line_item)
    db.session.flush()
    sync_targeting(line_item, _api_form_like(payload))
    db.session.commit()
    return jsonify({"ok": True, "id": line_item.id, "name": line_item.name}), 201


@api_bp.route("/creatives", methods=["POST"])
def create_creative_api():
    payload = request.get_json(silent=True) or {}
    creative = Creative()
    populate_creative(creative, payload)
    if not validate_creative(creative):
        return jsonify({"ok": False, "error": "invalid creative payload"}), 400
    db.session.add(creative)
    db.session.commit()
    return jsonify({"ok": True, "id": creative.id, "name": creative.name}), 201


@api_bp.route("/launch-line-item", methods=["POST"])
def launch_line_item_api():
    payload = request.get_json(silent=True) or request.form
    line_item = LineItem.query.get_or_404(parse_int(payload.get("line_item_id"), None))
    result = launch_line_item(line_item)
    status_code = 200 if result["ready"] else 422
    return jsonify({"ok": result["ready"], "workflow_state": line_item.workflow_state, "issues": result["issues"]}), status_code


@api_bp.route("/delivery/report")
def delivery_report_api():
    date_from = parse_date(request.args.get("date_from"))
    date_to = parse_date(request.args.get("date_to"))
    return jsonify(get_report_data(date_from=date_from, date_to=date_to))


class _ApiFormLike(dict):
    def getlist(self, key):
        value = self.get(key, [])
        if isinstance(value, list):
            return value
        if value in (None, ""):
            return []
        return [value]


def _api_form_like(payload):
    return _ApiFormLike(payload)
