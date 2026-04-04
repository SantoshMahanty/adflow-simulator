from sqlalchemy.orm import defer

from sqlalchemy import func

from ..models import (
    ActivityLog,
    AdRequest,
    Advertiser,
    AuctionCandidate,
    AuctionResult,
    AuctionSimulation,
    ClickLog,
    Creative,
    ImpressionLog,
    LineItem,
    Order,
    TroubleshootingIssue,
    db,
)


def get_dashboard_data():
    paused_campaigns = LineItem.query.filter_by(status="paused").count()
    total_requests = AdRequest.query.count()
    filled_requests = AdRequest.query.join(AdRequest.result).filter(AuctionResult.status == "filled").count()
    impressions = ImpressionLog.query.count()
    clicks = ClickLog.query.count()
    line_item_spend = float(db.session.query(func.coalesce(func.sum(LineItem.spent_amount), 0)).scalar() or 0)
    issue_breakdown = (
        TroubleshootingIssue.query.with_entities(TroubleshootingIssue.severity, func.count(TroubleshootingIssue.id))
        .group_by(TroubleshootingIssue.severity)
        .all()
    )
    recent_activity = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
    recent_simulations = (
        AuctionSimulation.query.options(
            defer(AuctionSimulation.request_context),
            defer(AuctionSimulation.evaluation_data),
        )
        .order_by(AuctionSimulation.created_at.desc())
        .limit(6)
        .all()
    )
    recent_requests = AdRequest.query.order_by(AdRequest.created_at.desc()).limit(8).all()
    slot_performance = (
        AdRequest.query.with_entities(AdRequest.slot_id, func.count(AdRequest.id))
        .group_by(AdRequest.slot_id)
        .order_by(func.count(AdRequest.id).desc())
        .limit(6)
        .all()
    )
    loss_reason_breakdown = (
        AuctionCandidate.query.with_entities(AuctionCandidate.loss_reason, func.count(AuctionCandidate.id))
        .filter(AuctionCandidate.loss_reason.isnot(None))
        .group_by(AuctionCandidate.loss_reason)
        .order_by(func.count(AuctionCandidate.id).desc())
        .limit(6)
        .all()
    )
    active_by_ad_unit = (
        AdRequest.query.with_entities(AdRequest.ad_unit_code, func.count(func.distinct(AdRequest.winning_line_item_id)))
        .filter(AdRequest.winning_line_item_id.isnot(None))
        .group_by(AdRequest.ad_unit_code)
        .order_by(func.count(AdRequest.id).desc())
        .limit(8)
        .all()
    )

    return {
        "kpis": [
            {"label": "Total Advertisers", "value": Advertiser.query.count()},
            {"label": "Total Orders", "value": Order.query.count()},
            {"label": "Total Line Items", "value": LineItem.query.count()},
            {"label": "Active Line Items", "value": LineItem.query.filter(LineItem.workflow_state.in_(["Live", "Scheduled"])).count()},
            {"label": "Paused Campaigns", "value": paused_campaigns},
            {"label": "Fill Rate", "value": f"{round((filled_requests / total_requests) * 100, 2) if total_requests else 0}%"},
            {"label": "Win Rate", "value": f"{round((filled_requests / max(total_requests, 1)) * 100, 2)}%"},
            {"label": "CTR", "value": f"{round((clicks / impressions) * 100, 2) if impressions else 0}%"},
            {"label": "Spend", "value": f"{line_item_spend:,.2f}"},
        ],
        "delivery_summary": {
            "healthy": LineItem.query.filter(LineItem.workflow_state == "Live", LineItem.delivered_impressions >= (LineItem.goal_impressions * 0.7)).count(),
            "at_risk": LineItem.query.filter(LineItem.workflow_state == "Live", LineItem.delivered_impressions < (LineItem.goal_impressions * 0.7)).count(),
            "paused": paused_campaigns,
        },
        "issue_breakdown": [{"label": severity.title(), "value": count} for severity, count in issue_breakdown],
        "auction_chart": [
            {
                "label": f"{simulation.mode[:3]} #{simulation.id}",
                "value": 1,
                "winner": simulation.winner_line_item.name if simulation.winner_line_item else "No winner",
            }
            for simulation in recent_simulations
        ],
        "recent_activity": recent_activity,
        "recent_simulations": recent_simulations,
        "recent_requests": recent_requests,
        "slot_performance": [{"label": label, "value": value} for label, value in slot_performance],
        "loss_reason_breakdown": [{"label": label or "unknown", "value": value} for label, value in loss_reason_breakdown],
        "active_by_ad_unit": [{"label": label or "unknown", "value": value} for label, value in active_by_ad_unit],
    }
