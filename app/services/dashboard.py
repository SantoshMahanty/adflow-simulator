from sqlalchemy.orm import defer

from sqlalchemy import func

from ..models import ActivityLog, Advertiser, AuctionSimulation, Creative, LineItem, Order, TroubleshootingIssue


def get_dashboard_data():
    paused_campaigns = LineItem.query.filter_by(status="paused").count()
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

    return {
        "kpis": [
            {"label": "Total Advertisers", "value": Advertiser.query.count()},
            {"label": "Total Orders", "value": Order.query.count()},
            {"label": "Total Line Items", "value": LineItem.query.count()},
            {"label": "Active Line Items", "value": LineItem.query.filter_by(status="active").count()},
            {"label": "Paused Campaigns", "value": paused_campaigns},
            {"label": "Total Creatives", "value": Creative.query.count()},
            {"label": "Open Troubleshooting Issues", "value": TroubleshootingIssue.query.count()},
            {"label": "Recent Simulations", "value": AuctionSimulation.query.count()},
        ],
        "delivery_summary": {
            "healthy": LineItem.query.filter(LineItem.status == "active", LineItem.delivered_impressions >= (LineItem.goal_impressions * 0.7)).count(),
            "at_risk": LineItem.query.filter(LineItem.status == "active", LineItem.delivered_impressions < (LineItem.goal_impressions * 0.7)).count(),
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
    }
