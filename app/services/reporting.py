from sqlalchemy import func

from ..models import Advertiser, AuctionSimulation, LineItem, Order, TroubleshootingIssue


def get_report_data():
    line_item_status = (
        LineItem.query.with_entities(LineItem.status, func.count(LineItem.id))
        .group_by(LineItem.status)
        .all()
    )
    issue_categories = (
        TroubleshootingIssue.query.with_entities(TroubleshootingIssue.category, func.count(TroubleshootingIssue.id))
        .group_by(TroubleshootingIssue.category)
        .all()
    )
    advertiser_activity = [
        {"label": advertiser.name, "value": sum(item.delivered_impressions for item in advertiser.line_items)}
        for advertiser in Advertiser.query.order_by(Advertiser.name.asc()).all()
    ]

    simulation_summary = {}
    failure_reasons = {}
    simulations = AuctionSimulation.query.all()
    for simulation in simulations:
        simulation_summary[simulation.mode] = simulation_summary.get(simulation.mode, 0) + 1
        for candidate in simulation.evaluation_data.get("candidates", []):
            if candidate.get("eligible"):
                continue
            reason = candidate.get("rejection_reason", "Other").split(";")[0]
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

    return {
        "totals": {
            "advertisers": Advertiser.query.count(),
            "orders": Order.query.count(),
            "line_items": LineItem.query.count(),
            "simulations": len(simulations),
        },
        "line_item_status": [{"label": label.title(), "value": value} for label, value in line_item_status],
        "issue_categories": [{"label": label, "value": value} for label, value in issue_categories],
        "advertiser_activity": advertiser_activity,
        "simulation_summary": [{"label": label, "value": value} for label, value in simulation_summary.items()],
        "failure_reasons": [{"label": label, "value": value} for label, value in failure_reasons.items()],
    }
