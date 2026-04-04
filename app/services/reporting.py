from datetime import datetime, time

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from ..models import (
    AdRequest,
    Advertiser,
    AuctionCandidate,
    AuctionSimulation,
    ClickLog,
    ImpressionLog,
    LineItem,
    Order,
    TroubleshootingIssue,
    TroubleshootingSheetRow,
    db,
)


REPORT_TYPES = [
    {"value": "summary", "label": "Summary Report"},
    {"value": "line_items", "label": "Line Items Report"},
    {"value": "simulations", "label": "Simulation Report"},
    {"value": "troubleshooting", "label": "Troubleshooting Report"},
]
REPORT_TYPE_VALUES = {item["value"] for item in REPORT_TYPES}


def _normalize_report_type(report_type):
    return report_type if report_type in REPORT_TYPE_VALUES else "summary"


def _apply_created_at_range(query, model, date_from=None, date_to=None):
    if date_from:
        query = query.filter(model.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(model.created_at <= datetime.combine(date_to, time.max))
    return query


def get_report_data(date_from=None, date_to=None):
    advertiser_query = _apply_created_at_range(Advertiser.query, Advertiser, date_from, date_to)
    order_query = _apply_created_at_range(Order.query, Order, date_from, date_to)
    line_item_query = _apply_created_at_range(LineItem.query, LineItem, date_from, date_to)
    issue_query = _apply_created_at_range(TroubleshootingIssue.query, TroubleshootingIssue, date_from, date_to)
    simulation_query = _apply_created_at_range(AuctionSimulation.query, AuctionSimulation, date_from, date_to)
    request_query = _apply_created_at_range(AdRequest.query, AdRequest, date_from, date_to)
    impression_query = _apply_created_at_range(ImpressionLog.query, ImpressionLog, date_from, date_to)
    click_query = _apply_created_at_range(ClickLog.query, ClickLog, date_from, date_to)

    line_item_status = (
        line_item_query.with_entities(LineItem.status, func.count(LineItem.id))
        .group_by(LineItem.status)
        .all()
    )
    issue_categories = (
        issue_query.with_entities(TroubleshootingIssue.category, func.count(TroubleshootingIssue.id))
        .group_by(TroubleshootingIssue.category)
        .all()
    )
    advertiser_activity = (
        _apply_created_at_range(
            LineItem.query.join(LineItem.advertiser),
            LineItem,
            date_from,
            date_to,
        )
        .with_entities(
            Advertiser.name,
            func.coalesce(func.sum(LineItem.delivered_impressions), 0),
        )
        .group_by(Advertiser.name)
        .order_by(Advertiser.name.asc())
        .all()
    )

    simulations = simulation_query.all()
    ad_requests = request_query.all()
    impressions = impression_query.all()
    clicks = click_query.all()
    simulation_summary = {}
    failure_reasons = {}
    for simulation in simulations:
        simulation_summary[simulation.mode] = simulation_summary.get(simulation.mode, 0) + 1
        for candidate in simulation.evaluation_data.get("candidates", []):
            if candidate.get("eligible"):
                continue
            reason = candidate.get("rejection_reason", "Other").split(";")[0]
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

    live_loss_reasons = (
        _apply_created_at_range(AuctionCandidate.query, AuctionCandidate, date_from, date_to)
        .with_entities(AuctionCandidate.loss_reason, func.count(AuctionCandidate.id))
        .filter(AuctionCandidate.loss_reason.isnot(None))
        .group_by(AuctionCandidate.loss_reason)
        .all()
    )
    slot_activity = (
        _apply_created_at_range(AdRequest.query, AdRequest, date_from, date_to)
        .with_entities(AdRequest.slot_id, func.count(AdRequest.id))
        .group_by(AdRequest.slot_id)
        .all()
    )
    total_spend = float(
        _apply_created_at_range(ImpressionLog.query, ImpressionLog, date_from, date_to)
        .with_entities(func.coalesce(func.sum(ImpressionLog.revenue), 0))
        .scalar()
        or 0
    )

    return {
        "totals": {
            "advertisers": advertiser_query.count(),
            "orders": order_query.count(),
            "line_items": line_item_query.count(),
            "simulations": len(simulations),
            "requests": len(ad_requests),
            "impressions": len(impressions),
            "clicks": len(clicks),
            "spend": round(total_spend, 2),
        },
        "line_item_status": [{"label": label.title(), "value": value} for label, value in line_item_status],
        "issue_categories": [{"label": label, "value": value} for label, value in issue_categories],
        "advertiser_activity": [{"label": label, "value": int(value)} for label, value in advertiser_activity],
        "simulation_summary": [{"label": label, "value": value} for label, value in simulation_summary.items()],
        "failure_reasons": [{"label": label, "value": value} for label, value in failure_reasons.items()]
        + [{"label": label or "unknown", "value": value} for label, value in live_loss_reasons],
        "delivery_activity": [
            {"label": "Ad Requests", "value": len(ad_requests)},
            {"label": "Impressions", "value": len(impressions)},
            {"label": "Clicks", "value": len(clicks)},
            {"label": "CTR x100", "value": round((len(clicks) / len(impressions)) * 100, 2) if impressions else 0},
            {"label": "Fill Rate", "value": round((len(impressions) / len(ad_requests)) * 100, 2) if ad_requests else 0},
        ],
        "slot_activity": [{"label": label, "value": value} for label, value in slot_activity],
    }


def get_available_report_types():
    return REPORT_TYPES


def build_report_export(report_type, date_from=None, date_to=None):
    report_type = _normalize_report_type(report_type)

    if report_type == "line_items":
        rows = (
            _apply_created_at_range(
                LineItem.query.options(joinedload(LineItem.order), joinedload(LineItem.advertiser)),
                LineItem,
                date_from,
                date_to,
            )
            .order_by(LineItem.created_at.desc())
            .all()
        )
        return {
            "filename": "line_items_report.csv",
            "headers": [
                "Line Item ID",
                "Line Item Name",
                "Advertiser",
                "Order",
                "Type",
                "Status",
                "Priority",
                "Creative Size",
                "Goal Impressions",
                "Delivered Impressions",
                "CPM",
                "Start Date",
                "End Date",
                "Created At",
            ],
            "rows": [
                [
                    row.id,
                    row.name,
                    row.advertiser.name,
                    row.order.name,
                    row.line_item_type,
                    row.status,
                    row.priority,
                    row.creative_size,
                    row.goal_impressions,
                    row.delivered_impressions,
                    float(row.cpm),
                    row.start_date.isoformat(),
                    row.end_date.isoformat(),
                    row.created_at.isoformat(sep=" ", timespec="minutes"),
                ]
                for row in rows
            ],
        }

    if report_type == "simulations":
        rows = (
            _apply_created_at_range(
                AuctionSimulation.query.options(
                    joinedload(AuctionSimulation.ad_unit),
                    joinedload(AuctionSimulation.winner_line_item),
                ),
                AuctionSimulation,
                date_from,
                date_to,
            )
            .order_by(AuctionSimulation.created_at.desc())
            .all()
        )
        return {
            "filename": "simulation_report.csv",
            "headers": [
                "Simulation ID",
                "Mode",
                "Ad Unit",
                "Winner",
                "Request Geo",
                "Request Device",
                "Creative Size",
                "Created At",
            ],
            "rows": [
                [
                    row.id,
                    row.mode,
                    row.ad_unit.path if row.ad_unit else "",
                    row.winner_line_item.name if row.winner_line_item else "No winner",
                    row.request_context.get("geo", ""),
                    row.request_context.get("device", ""),
                    row.request_context.get("creative_size", ""),
                    row.created_at.isoformat(sep=" ", timespec="minutes"),
                ]
                for row in rows
            ],
        }

    if report_type == "troubleshooting":
        rows = (
            _apply_created_at_range(
                TroubleshootingSheetRow.query.options(joinedload(TroubleshootingSheetRow.line_item)),
                TroubleshootingSheetRow,
                date_from,
                date_to,
            )
            .order_by(TroubleshootingSheetRow.created_at.desc())
            .all()
        )
        return {
            "filename": "troubleshooting_report.csv",
            "headers": [
                "Issue Title",
                "Campaign",
                "Line Item",
                "Severity",
                "Status",
                "Owner",
                "Problem",
                "Possible Reason",
                "Suggested Fix",
                "Due Date",
                "Created At",
            ],
            "rows": [
                [
                    row.issue_title,
                    row.campaign_name,
                    row.line_item.name if row.line_item else "",
                    row.severity,
                    row.status,
                    row.owner,
                    row.problem,
                    row.possible_reason,
                    row.suggested_fix,
                    row.due_date.isoformat() if row.due_date else "",
                    row.created_at.isoformat(sep=" ", timespec="minutes"),
                ]
                for row in rows
            ],
        }

    summary = get_report_data(date_from=date_from, date_to=date_to)
    return {
        "filename": "summary_report.csv",
        "headers": [
            "Date From",
            "Date To",
            "Advertisers",
            "Orders",
            "Line Items",
            "Simulations",
            "Requests",
            "Top Failure Reason",
        ],
        "rows": [
            [
                date_from.isoformat() if date_from else "",
                date_to.isoformat() if date_to else "",
                summary["totals"]["advertisers"],
                summary["totals"]["orders"],
                summary["totals"]["line_items"],
                summary["totals"]["simulations"],
                summary["totals"]["requests"],
                summary["failure_reasons"][0]["label"] if summary["failure_reasons"] else "None",
            ]
        ],
    }
