from __future__ import annotations

from datetime import date, datetime

from ..models import LineItem, db


WORKFLOW_STATES = [
    "Draft",
    "Ready for Review",
    "Approved",
    "Scheduled",
    "Live",
    "Paused",
    "Completed",
    "Archived",
]


def _has_targeting(line_item):
    return any(rule.target_type == "ad_unit" for rule in line_item.targeting_rules)


def _approved_creatives(line_item):
    return [
        creative
        for creative in line_item.creatives
        if creative.is_active and (creative.approval_status or "").lower() == "approved"
    ]


def validate_launch(line_item, current_day=None):
    current_day = current_day or date.today()
    issues = []

    if not line_item.advertiser or (line_item.advertiser.status or "").lower() != "active":
        issues.append("Advertiser must exist and be active.")
    if not line_item.order:
        issues.append("Order must exist before launch.")
    if not line_item.name:
        issues.append("Line item name is required.")
    if not line_item.start_date or not line_item.end_date or line_item.start_date > line_item.end_date:
        issues.append("Start and end dates must be valid.")
    if line_item.end_date and line_item.end_date < current_day:
        issues.append("Campaign flight has already expired.")
    if not line_item.budget_amount or float(line_item.budget_amount) <= 0:
        issues.append("Budget is required before launch.")
    if not _has_targeting(line_item):
        issues.append("At least one publisher ad unit must be mapped.")
    if not line_item.targeting_rules:
        issues.append("Targeting rules must exist before launch.")
    if not _approved_creatives(line_item):
        issues.append("At least one approved active creative is required.")
    if not line_item.creative_size:
        issues.append("Creative size is required.")

    # Order-level checks keep the line item aligned with its parent campaign.
    if line_item.order:
        if line_item.order.start_date and line_item.start_date and line_item.start_date < line_item.order.start_date:
            issues.append("Line item cannot start before its order.")
        if line_item.order.end_date and line_item.end_date and line_item.end_date > line_item.order.end_date:
            issues.append("Line item cannot end after its order.")

    return {
        "ready": not issues,
        "issues": issues,
        "approved_creatives": _approved_creatives(line_item),
    }


def apply_workflow_state(line_item, workflow_state):
    workflow_state = workflow_state or "Draft"
    line_item.workflow_state = workflow_state
    normalized = workflow_state.lower()
    if normalized == "live":
        line_item.status = "live"
    elif normalized == "paused":
        line_item.status = "paused"
    elif normalized == "completed":
        line_item.status = "completed"
    elif normalized == "archived":
        line_item.status = "archived"
    else:
        line_item.status = "draft"


def launch_line_item(line_item, current_day=None):
    current_day = current_day or date.today()
    validation = validate_launch(line_item, current_day=current_day)
    line_item.launch_ready = validation["ready"]
    if not validation["ready"]:
        return validation

    if line_item.start_date > current_day:
        line_item.workflow_state = "Scheduled"
        line_item.status = "active"
    else:
        line_item.workflow_state = "Live"
        line_item.status = "live"
    line_item.launch_ready = True
    line_item.last_launched_at = datetime.utcnow()
    if line_item.order and not line_item.order.workflow_state:
        line_item.order.workflow_state = "Approved"
    db.session.commit()
    return validation
