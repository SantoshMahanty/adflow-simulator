from datetime import datetime

from sqlalchemy.orm import joinedload, selectinload

from ..models import AuctionSimulation, KeyValueValue, LineItem, LineItemTargeting, db
from .eligibility import evaluate_line_item


WATERFALL_ORDER = {
    "Sponsorship": 1,
    "Standard": 2,
    "Preferred Deal": 3,
    "Programmatic Guaranteed": 4,
    "AdX/Price Priority": 5,
    "Network": 6,
    "House": 7,
}

UNIFIED_BONUS = {
    "Sponsorship": 5.0,
    "Preferred Deal": 3.5,
    "Programmatic Guaranteed": 3.0,
    "Standard": 2.0,
    "AdX/Price Priority": 1.5,
    "Network": 1.0,
    "House": 0.2,
}


def serialize_candidate(line_item, evaluation):
    targeting_failed = any(
        phrase in " ".join(evaluation["reasons"]).lower()
        for phrase in ["targeting", "category", "ad unit", "key-value"]
    )
    return {
        "id": line_item.id,
        "name": line_item.name,
        "advertiser": line_item.advertiser.name,
        "order": line_item.order.name,
        "type": line_item.line_item_type,
        "priority": line_item.priority,
        "cpm": float(line_item.cpm),
        "status": line_item.status,
        "targeting_match": "Fail" if targeting_failed else "Pass",
        "date_match": "Fail" if "Current date is outside the flight window." in evaluation["reasons"] else "Pass",
        "status_match": "Fail" if "Line item is paused or not active." in evaluation["reasons"] else "Pass",
        "eligible": evaluation["eligible"],
        "rejection_reason": "; ".join(evaluation["reasons"]) if evaluation["reasons"] else "",
        "approved_creatives": [creative.name for creative in evaluation["approved_creatives"]],
    }


def run_waterfall(request_context):
    line_items = (
        LineItem.query.options(
            joinedload(LineItem.order),
            joinedload(LineItem.advertiser),
            selectinload(LineItem.creatives),
            selectinload(LineItem.targeting_rules)
            .joinedload(LineItemTargeting.key_value_value)
            .joinedload(KeyValueValue.key),
        )
        .all()
    )
    sorted_line_items = sorted(
        line_items,
        key=lambda item: (WATERFALL_ORDER.get(item.line_item_type, 99), item.priority, -float(item.cpm)),
    )

    winner = None
    steps = []
    candidates = []

    for index, line_item in enumerate(sorted_line_items, start=1):
        evaluation = evaluate_line_item(line_item, request_context)
        candidate = serialize_candidate(line_item, evaluation)
        if not winner and evaluation["eligible"]:
            winner = candidate
            decision = "Winner selected"
            reason = "Highest priority eligible demand won the waterfall."
        elif evaluation["eligible"] and winner:
            decision = "Skipped after winner"
            reason = "Lower in waterfall after an earlier eligible winner."
            candidate["rejection_reason"] = reason
        else:
            decision = "Rejected"
            reason = candidate["rejection_reason"]

        steps.append(
            {
                "step": index,
                "line_item": line_item.name,
                "type": line_item.line_item_type,
                "priority": line_item.priority,
                "decision": decision,
                "reason": reason,
            }
        )
        candidates.append(candidate)

    return {
        "mode": "Waterfall",
        "request_context": request_context,
        "winner": winner,
        "candidates": candidates,
        "steps": steps,
        "generated_at": datetime.utcnow().isoformat(),
    }


def run_unified_auction(request_context):
    candidates = []
    eligible_candidates = []

    line_items = (
        LineItem.query.options(
            joinedload(LineItem.order),
            joinedload(LineItem.advertiser),
            selectinload(LineItem.creatives),
            selectinload(LineItem.targeting_rules)
            .joinedload(LineItemTargeting.key_value_value)
            .joinedload(KeyValueValue.key),
        )
        .all()
    )
    for line_item in line_items:
        evaluation = evaluate_line_item(line_item, request_context)
        candidate = serialize_candidate(line_item, evaluation)
        candidate["effective_cpm"] = round(float(line_item.cpm) + UNIFIED_BONUS.get(line_item.line_item_type, 0), 2)
        candidates.append(candidate)
        if candidate["eligible"]:
            eligible_candidates.append(candidate)

    eligible_candidates.sort(key=lambda item: (item["effective_cpm"], -item["priority"], item["cpm"]), reverse=True)
    winner = eligible_candidates[0] if eligible_candidates else None

    for candidate in candidates:
        if not candidate["eligible"] or not winner or candidate["id"] == winner["id"]:
            continue
        candidate["rejection_reason"] = f"Lost to {winner['name']} with higher effective CPM {winner['effective_cpm']:.2f}."

    return {
        "mode": "Unified Auction",
        "request_context": request_context,
        "winner": winner,
        "candidates": sorted(candidates, key=lambda item: item["effective_cpm"], reverse=True),
        "steps": [],
        "generated_at": datetime.utcnow().isoformat(),
        "why_winner_won": (
            f"{winner['name']} cleared eligibility and posted the strongest effective CPM."
            if winner
            else "No eligible line item matched the request."
        ),
    }


def persist_simulation(mode, request_context, result, ad_unit_id=None):
    simulation = AuctionSimulation(
        mode=mode,
        ad_unit_id=ad_unit_id,
        request_context=request_context,
        winner_line_item_id=result["winner"]["id"] if result.get("winner") else None,
        evaluation_data=result,
    )
    db.session.add(simulation)
    db.session.commit()
    return simulation
