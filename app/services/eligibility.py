from datetime import date

from .helpers import split_csv_values


def value_matches(rule_value, request_value):
    if not rule_value:
        return True
    request_value = (request_value or "").strip().lower()
    if not request_value:
        return False
    allowed = split_csv_values(rule_value)
    return request_value in allowed


def build_troubleshooting_hints(reasons):
    mapping = {
        "Line item is paused or not active.": "Activate the line item or move it from draft or paused to active.",
        "Current date is outside the flight window.": "Check start and end dates on the order and line item.",
        "Line item has exhausted its impression goal.": "Raise the impression goal or reset delivered volume for testing.",
        "Geo targeting does not match the request.": "Compare request geo with configured geo targeting.",
        "Device targeting does not match the request.": "Validate device targeting and environment mapping.",
        "Audience targeting does not match the request.": "Review audience segment mapping and request segment availability.",
        "Creative size does not match the request.": "Align the request size with the line item and creative sizes.",
        "No approved and active creative is available.": "Approve or replace creatives and confirm active serving state.",
        "Line item budget is exhausted.": "Increase the line item budget or lower delivery for testing.",
        "Ad unit targeting does not include the request ad unit.": "Assign the correct ad unit or placement to the line item.",
        "Content category targeting does not match.": "Verify content_category targeting against request metadata.",
        "Page type targeting does not match the request.": "Check whether the line item is targeted to home, article, or category pages.",
        "Slot position targeting does not match the request.": "Confirm the line item targets the requested top, sidebar, in-article, footer, or anchor slot.",
        "Required key-value targeting does not match.": "Check page key-values and the line item's required values.",
    }
    return [mapping[reason] for reason in reasons if reason in mapping]


def evaluate_line_item(line_item, request_context, current_day=None):
    current_day = current_day or date.today()
    reasons = []
    checks = []

    def add_check(label, passed, message):
        checks.append({"label": label, "passed": passed, "message": message})
        if not passed:
            reasons.append(message)

    add_check(
        "Status",
        (line_item.workflow_state or "").lower() in {"live", "scheduled"} and line_item.status.lower() in {"active", "live"},
        "Line item is paused or not active.",
    )
    add_check(
        "Flight Dates",
        line_item.start_date <= current_day <= line_item.end_date,
        "Current date is outside the flight window.",
    )
    add_check("Geo", value_matches(line_item.geo_targeting, request_context.get("geo")), "Geo targeting does not match the request.")
    add_check(
        "Device",
        value_matches(line_item.device_targeting, request_context.get("device")),
        "Device targeting does not match the request.",
    )
    add_check(
        "Audience",
        value_matches(line_item.audience_targeting, request_context.get("audience")),
        "Audience targeting does not match the request.",
    )
    add_check(
        "Goal Remaining",
        not line_item.goal_impressions or line_item.delivered_impressions < line_item.goal_impressions,
        "Line item has exhausted its impression goal.",
    )
    add_check(
        "Budget Remaining",
        not getattr(line_item, "budget_amount", 0) or float(line_item.budget_amount) > float(getattr(line_item, "spent_amount", 0) or 0),
        "Line item budget is exhausted.",
    )

    requested_size = (request_context.get("creative_size") or "").strip().lower()
    add_check(
        "Creative Size",
        not line_item.creative_size or line_item.creative_size.lower() == requested_size,
        "Creative size does not match the request.",
    )

    approved_creatives = [
        creative
        for creative in line_item.creatives
        if creative.is_active
        and creative.approval_status.lower() == "approved"
        and (not requested_size or creative.size.lower() == requested_size)
    ]
    add_check("Creative Approval", bool(approved_creatives), "No approved and active creative is available.")

    request_key_values = request_context.get("key_values") or {}
    key_value_rules = [rule for rule in line_item.targeting_rules if rule.target_type == "key_value"]
    key_value_ok = True
    for rule in key_value_rules:
        if not rule.key_value_value:
            continue
        expected = rule.key_value_value.value.strip().lower()
        actual = (request_key_values.get(rule.key_value_value.key.name) or "").strip().lower()
        if actual != expected:
            key_value_ok = False
            break
    add_check("Key Values", key_value_ok, "Required key-value targeting does not match.")

    ad_unit_request = (request_context.get("ad_unit_path") or "").strip().lower()
    ad_unit_rules = [rule for rule in line_item.targeting_rules if rule.target_type == "ad_unit"]
    ad_unit_ok = True if not ad_unit_rules else any((rule.target_value or "").strip().lower() == ad_unit_request for rule in ad_unit_rules)
    add_check("Ad Unit", ad_unit_ok, "Ad unit targeting does not include the request ad unit.")

    category_request = (request_context.get("content_category") or "").strip().lower()
    category_rules = [rule for rule in line_item.targeting_rules if rule.target_type == "content_category"]
    category_ok = True if not category_rules else any((rule.target_value or "").strip().lower() == category_request for rule in category_rules)
    add_check("Content Category", category_ok, "Content category targeting does not match.")

    page_type_request = (request_context.get("page_type") or "").strip().lower()
    page_type_rules = [rule for rule in line_item.targeting_rules if rule.target_type == "page_type"]
    page_type_ok = True if not page_type_rules else any((rule.target_value or "").strip().lower() == page_type_request for rule in page_type_rules)
    add_check("Page Type", page_type_ok, "Page type targeting does not match the request.")

    slot_position_request = (request_context.get("slot_position") or "").strip().lower()
    slot_position_rules = [rule for rule in line_item.targeting_rules if rule.target_type == "slot_position"]
    slot_position_ok = True if not slot_position_rules else any((rule.target_value or "").strip().lower() == slot_position_request for rule in slot_position_rules)
    add_check("Slot Position", slot_position_ok, "Slot position targeting does not match the request.")

    return {
        "eligible": not reasons,
        "reasons": reasons,
        "checks": checks,
        "approved_creatives": approved_creatives,
        "hints": build_troubleshooting_hints(reasons),
    }
