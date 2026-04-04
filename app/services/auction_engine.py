from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from random import Random
from uuid import uuid4

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import joinedload, selectinload

from ..models import (
    AdRequest,
    AdUnit,
    AuctionCandidate,
    AuctionResult,
    ClickLog,
    Creative,
    DeliveryLog,
    ImpressionLog,
    KeyValueValue,
    LineItem,
    LineItemTargeting,
    PublisherSite,
    db,
)
from .helpers import split_csv_values


LOSS_LABELS = {
    "not_live": "lost_not_live",
    "not_started": "lost_not_started",
    "expired": "lost_expired",
    "geo_mismatch": "lost_geo_mismatch",
    "device_mismatch": "lost_device_mismatch",
    "size_mismatch": "lost_size_mismatch",
    "budget_exhausted": "lost_budget_exhausted",
    "daily_cap": "lost_daily_cap",
    "frequency_cap": "lost_frequency_cap",
    "creative_missing": "lost_creative_missing",
    "creative_not_approved": "lost_creative_not_approved",
    "ad_unit_mismatch": "lost_ad_unit_mismatch",
    "page_type_mismatch": "lost_page_type_mismatch",
    "slot_position_mismatch": "lost_slot_position_mismatch",
    "category_mismatch": "lost_category_mismatch",
    "key_value_mismatch": "lost_key_value_mismatch",
    "lower_bid": "lost_lower_bid",
    "priority": "lost_priority",
    "weighted_tiebreak": "lost_weighted_tiebreak",
}
WIN_LABELS = {
    "highest_bid": "won_highest_bid",
    "weighted_tiebreak": "won_weighted_tiebreak",
}

PRIORITY_BUCKETS = {
    "sponsorship": 1,
    "programmatic guaranteed": 2,
    "preferred deal": 2,
    "standard": 2,
    "adx/price priority": 3,
    "network": 3,
    "house": 4,
    "bulk": 4,
}


def _priority_bucket(line_item):
    type_name = (line_item.line_item_type or "").strip().lower()
    if type_name in PRIORITY_BUCKETS:
        return type_name.title()
    return "Standard"


def _priority_value(line_item):
    return PRIORITY_BUCKETS.get((line_item.line_item_type or "").strip().lower(), 2)


def _value_matches(rule_value, request_value):
    if not rule_value:
        return True
    request_value = (request_value or "").strip().lower()
    if not request_value:
        return False
    return request_value in split_csv_values(rule_value)


def _count_session_impressions(line_item_id, session_id):
    if not session_id:
        return 0
    return ImpressionLog.query.filter_by(line_item_id=line_item_id, session_id=session_id).count()


def _count_daily_impressions(line_item_id, current_day):
    return ImpressionLog.query.filter(
        ImpressionLog.line_item_id == line_item_id,
        ImpressionLog.created_at >= datetime.combine(current_day, time.min),
        ImpressionLog.created_at <= datetime.combine(current_day, time.max),
    ).count()


def _sum_daily_spend(line_item_id, current_day):
    return float(
        db.session.query(func.coalesce(func.sum(ImpressionLog.revenue), 0))
        .filter(
            ImpressionLog.line_item_id == line_item_id,
            ImpressionLog.created_at >= datetime.combine(current_day, time.min),
            ImpressionLog.created_at <= datetime.combine(current_day, time.max),
        )
        .scalar()
        or 0
    )


def _creative_render_reason(creative, requested_size):
    requested_size = (requested_size or "").strip().lower()
    creative_format = (creative.creative_format or "").strip().lower()
    creative_size = (creative.size or "").strip().lower()

    if not creative.is_active:
        return LOSS_LABELS["creative_missing"], "Creative is inactive."
    if (creative.approval_status or "").strip().lower() != "approved":
        return LOSS_LABELS["creative_not_approved"], "Creative is not approved."
    if requested_size and creative_size != requested_size:
        return LOSS_LABELS["size_mismatch"], "Creative size does not match the slot."
    if creative_format in {"html", "third_party_tag", "video"} and not (creative.tag_snippet or "").strip():
        return LOSS_LABELS["creative_missing"], "Creative has no tag or markup to render."
    if creative_format in {"image", "display", "native"} and not ((creative.preview_text or "").strip() or (creative.asset_url or "").strip()):
        return LOSS_LABELS["creative_missing"], "Creative has no preview asset."
    return None, None


def _select_creative(line_item, requested_size):
    approved = []
    audit = []
    for creative in line_item.creatives:
        code, message = _creative_render_reason(creative, requested_size)
        audit.append(
            {
                "creative": creative.name,
                "eligible": code is None,
                "reason": message or "Creative ready to render.",
            }
        )
        if code is None:
            approved.append(creative)
    approved.sort(key=lambda creative: (creative.created_at, creative.id or 0), reverse=True)
    return (approved[0] if approved else None), audit


def _pacing_need_score(line_item, current_day):
    if not line_item.goal_impressions:
        return 0.5
    total_days = max((line_item.end_date - line_item.start_date).days + 1, 1)
    elapsed_days = min(max((current_day - line_item.start_date).days + 1, 0), total_days)
    flight_progress = elapsed_days / total_days
    delivery_progress = min(line_item.delivered_impressions / max(line_item.goal_impressions, 1), 1)
    return round(max(flight_progress - delivery_progress, 0), 4)


def _add_check(checks, reasons, label, passed, loss_code, message):
    checks.append({"label": label, "passed": passed, "loss_reason": loss_code, "message": message})
    if not passed:
        reasons.append({"code": loss_code, "message": message})


def _key_value_match(line_item, request_context):
    request_values = request_context.get("key_values") or {}
    for rule in line_item.targeting_rules:
        if rule.target_type != "key_value" or not rule.key_value_value:
            continue
        key_name = rule.key_value_value.key.name
        actual = (request_values.get(key_name) or "").strip().lower()
        expected = (rule.key_value_value.value or "").strip().lower()
        if actual != expected:
            return False
    return True


def _target_rule_values(line_item, target_type):
    return [
        (rule.target_value or "").strip().lower()
        for rule in line_item.targeting_rules
        if rule.target_type == target_type and (rule.target_value or "").strip()
    ]


def _event_log(request_row, line_item=None, creative=None, event_type="request", loss_reason=None, revenue=0, cpm=0, details=None):
    db.session.add(
        DeliveryLog(
            request_id=request_row.id,
            line_item_id=line_item.id if line_item else None,
            creative_id=creative.id if creative else None,
            event_type=event_type,
            loss_reason=loss_reason,
            revenue=Decimal(str(revenue or 0)),
            cpm=Decimal(str(cpm or 0)),
            details=details or {},
        )
    )


def _request_for_tracking(request_identifier):
    return AdRequest.query.options(
        joinedload(AdRequest.result),
        joinedload(AdRequest.winning_line_item).joinedload(LineItem.order),
        joinedload(AdRequest.winning_creative),
    ).filter_by(request_id=request_identifier).first_or_404()


def serialize_request_context(raw_request_context):
    timestamp_text = raw_request_context.get("timestamp") or datetime.utcnow().isoformat(timespec="seconds")
    return {
        "ad_unit_code": (raw_request_context.get("ad_unit_code") or raw_request_context.get("ad_unit_path") or raw_request_context.get("slot_id") or "").strip(),
        "slot_id": (raw_request_context.get("slot_id") or raw_request_context.get("ad_unit_code") or "").strip(),
        "page_url": (raw_request_context.get("page_url") or "").strip(),
        "page_type": (raw_request_context.get("page_type") or raw_request_context.get("page") or "").strip().lower(),
        "device_type": (raw_request_context.get("device_type") or raw_request_context.get("device") or "desktop").strip().lower(),
        "geo": (raw_request_context.get("geo") or "").strip().lower(),
        "session_id": (raw_request_context.get("session_id") or "").strip(),
        "content_category": (raw_request_context.get("category") or raw_request_context.get("content_category") or "").strip().lower(),
        "creative_size": (raw_request_context.get("size") or raw_request_context.get("creative_size") or "").strip().lower(),
        "slot_position": (raw_request_context.get("slot_position") or "").strip().lower(),
        "audience": (raw_request_context.get("audience") or "").strip().lower(),
        "timestamp": timestamp_text,
        "key_values": raw_request_context.get("key_values") or {},
        "debug": bool(raw_request_context.get("debug") or raw_request_context.get("debug_enabled")),
    }


def _candidate_queryset(ad_unit_path):
    if not ad_unit_path:
        return []
    return (
        LineItem.query.options(
            joinedload(LineItem.order),
            joinedload(LineItem.advertiser),
            selectinload(LineItem.creatives),
            selectinload(LineItem.targeting_rules)
            .joinedload(LineItemTargeting.key_value_value)
            .joinedload(KeyValueValue.key),
        )
        .filter(
            LineItem.targeting_rules.any(
                and_(
                    LineItemTargeting.target_type == "ad_unit",
                    LineItemTargeting.target_value == ad_unit_path,
                )
            )
        )
        .all()
    )


def evaluate_candidate(line_item, request_context, ad_unit, current_day=None):
    current_day = current_day or date.today()
    checks = []
    reasons = []
    selected_creative, creative_audit = _select_creative(line_item, request_context.get("creative_size"))

    _add_check(
        checks,
        reasons,
        "Workflow State",
        (line_item.workflow_state or "").lower() in {"live", "scheduled"} and (line_item.status or "").lower() in {"active", "live"},
        LOSS_LABELS["not_live"],
        "Line item is not launched for delivery.",
    )
    _add_check(checks, reasons, "Start Date", line_item.start_date <= current_day, LOSS_LABELS["not_started"], "Line item has not started yet.")
    _add_check(checks, reasons, "End Date", line_item.end_date >= current_day, LOSS_LABELS["expired"], "Line item has expired.")
    _add_check(checks, reasons, "Budget Remaining", float(line_item.budget_amount or 0) > float(line_item.spent_amount or 0), LOSS_LABELS["budget_exhausted"], "Line item budget is exhausted.")
    _add_check(checks, reasons, "Geo", _value_matches(line_item.geo_targeting, request_context.get("geo")), LOSS_LABELS["geo_mismatch"], "Geo targeting does not match.")
    _add_check(checks, reasons, "Device", _value_matches(line_item.device_targeting, request_context.get("device_type")), LOSS_LABELS["device_mismatch"], "Device targeting does not match.")
    _add_check(checks, reasons, "Audience", _value_matches(line_item.audience_targeting, request_context.get("audience")), LOSS_LABELS["key_value_mismatch"], "Audience targeting does not match.")
    _add_check(checks, reasons, "Slot Size", (line_item.creative_size or "").strip().lower() == (request_context.get("creative_size") or "").strip().lower(), LOSS_LABELS["size_mismatch"], "Line item creative size does not match the requested slot.")

    ad_unit_rules = _target_rule_values(line_item, "ad_unit")
    _add_check(checks, reasons, "Ad Unit", bool(ad_unit_rules) and (ad_unit.path if ad_unit else "").lower() in ad_unit_rules, LOSS_LABELS["ad_unit_mismatch"], "Ad unit targeting does not include the requested slot.")

    page_type_rules = _target_rule_values(line_item, "page_type")
    _add_check(checks, reasons, "Page Type", True if not page_type_rules else request_context.get("page_type") in page_type_rules, LOSS_LABELS["page_type_mismatch"], "Page type targeting does not match.")

    slot_position_rules = _target_rule_values(line_item, "slot_position")
    _add_check(checks, reasons, "Slot Position", True if not slot_position_rules else request_context.get("slot_position") in slot_position_rules, LOSS_LABELS["slot_position_mismatch"], "Slot position targeting does not match.")

    category_rules = _target_rule_values(line_item, "content_category")
    _add_check(checks, reasons, "Content Category", True if not category_rules else request_context.get("content_category") in category_rules, LOSS_LABELS["category_mismatch"], "Content category targeting does not match.")

    _add_check(checks, reasons, "Key Values", _key_value_match(line_item, request_context), LOSS_LABELS["key_value_mismatch"], "Required key values do not match.")

    frequency_ok = True
    if line_item.frequency_cap:
        frequency_ok = _count_session_impressions(line_item.id, request_context.get("session_id")) < line_item.frequency_cap
    _add_check(checks, reasons, "Frequency Cap", frequency_ok, LOSS_LABELS["frequency_cap"], "Session frequency cap reached.")

    daily_ok = True
    if line_item.daily_impression_cap:
        daily_ok = _count_daily_impressions(line_item.id, current_day) < line_item.daily_impression_cap
    _add_check(checks, reasons, "Daily Cap", daily_ok, LOSS_LABELS["daily_cap"], "Daily impression cap reached.")

    daily_spend_ok = True
    if float(line_item.daily_spend_cap or 0) > 0:
        daily_spend_ok = _sum_daily_spend(line_item.id, current_day) < float(line_item.daily_spend_cap)
    _add_check(checks, reasons, "Daily Spend Cap", daily_spend_ok, LOSS_LABELS["budget_exhausted"], "Daily spend cap reached.")

    creative_ok = selected_creative is not None
    creative_failure = creative_audit[0]["reason"] if creative_audit else "No creative attached."
    creative_loss_reason = LOSS_LABELS["creative_missing"]
    if creative_audit:
        first_rejection = next((entry for entry in creative_audit if not entry["eligible"]), None)
        if first_rejection and "approved" in first_rejection["reason"].lower():
            creative_loss_reason = LOSS_LABELS["creative_not_approved"]
    _add_check(checks, reasons, "Creative Render", creative_ok, creative_loss_reason, creative_failure)

    eligible = not reasons and selected_creative is not None
    return {
        "eligible": eligible,
        "checks": checks,
        "reasons": reasons,
        "selected_creative": selected_creative,
        "creative_audit": creative_audit,
        "priority_bucket": _priority_bucket(line_item),
        "priority_value": _priority_value(line_item),
        "pacing_score": _pacing_need_score(line_item, current_day),
        "effective_cpm": round(float(line_item.cpm or 0), 2),
    }


def _rank_eligible(eligible_candidates, request_context):
    if not eligible_candidates:
        return None, []

    ranked = sorted(
        eligible_candidates,
        key=lambda item: (
            item["evaluation"]["priority_value"],
            -float(item["line_item"].cpm or 0),
            -item["evaluation"]["pacing_score"],
        ),
    )
    top = ranked[0]
    finalists = [
        candidate
        for candidate in ranked
        if candidate["evaluation"]["priority_value"] == top["evaluation"]["priority_value"]
        and float(candidate["line_item"].cpm or 0) == float(top["line_item"].cpm or 0)
        and candidate["evaluation"]["pacing_score"] == top["evaluation"]["pacing_score"]
    ]
    if len(finalists) == 1:
        return finalists[0], finalists

    stable_seed = "|".join(
        [
            request_context.get("slot_id", ""),
            request_context.get("page_url", ""),
            request_context.get("session_id", ""),
            request_context.get("creative_size", ""),
        ]
    )
    rng = Random(stable_seed)
    total_weight = sum(max(candidate["line_item"].delivery_weight or 1, 1) for candidate in finalists)
    threshold = rng.uniform(0, total_weight)
    cursor = 0
    for candidate in finalists:
        cursor += max(candidate["line_item"].delivery_weight or 1, 1)
        if threshold <= cursor:
            return candidate, finalists
    return finalists[-1], finalists


def _render_mode(creative):
    creative_format = (creative.creative_format or "").strip().lower()
    snippet = (creative.tag_snippet or "").strip().lower()
    if creative_format == "third_party_tag" or "<script" in snippet:
        return "third_party_tag"
    if creative_format in {"html", "native", "video"}:
        return "html"
    return "image"


def execute_auction(raw_request_context):
    request_context = serialize_request_context(raw_request_context)
    current_day = date.today()
    ad_unit = AdUnit.query.filter(
        or_(AdUnit.path == request_context["ad_unit_code"], AdUnit.ad_unit_code == request_context["ad_unit_code"])
    ).first()
    publisher_site = ad_unit.publisher_site if ad_unit and ad_unit.publisher_site else PublisherSite.query.order_by(PublisherSite.id.asc()).first()

    request_row = AdRequest(
        request_id=uuid4().hex,
        publisher_site_id=publisher_site.id if publisher_site else None,
        ad_unit_id=ad_unit.id if ad_unit else None,
        ad_unit_code=request_context["ad_unit_code"],
        slot_id=request_context["slot_id"] or request_context["ad_unit_code"],
        page_url=request_context["page_url"],
        page_type=request_context["page_type"],
        device_type=request_context["device_type"],
        geo=request_context["geo"],
        session_id=request_context["session_id"],
        content_category=request_context["content_category"],
        creative_size=request_context["creative_size"],
        request_params=request_context,
        request_status="received",
        render_status="pending",
    )
    db.session.add(request_row)
    db.session.flush()
    _event_log(request_row, event_type="request", details=request_context)

    line_items = _candidate_queryset(ad_unit.path if ad_unit else request_context["ad_unit_code"])
    evaluated_candidates = []
    for line_item in line_items:
        evaluation = evaluate_candidate(line_item, request_context, ad_unit, current_day=current_day)
        evaluated_candidates.append({"line_item": line_item, "evaluation": evaluation})

    eligible_candidates = [candidate for candidate in evaluated_candidates if candidate["evaluation"]["eligible"]]
    winner_candidate, finalists = _rank_eligible(eligible_candidates, request_context)
    finalist_ids = {candidate["line_item"].id for candidate in finalists}

    ranked_candidates = sorted(
        evaluated_candidates,
        key=lambda item: (
            0 if item["evaluation"]["eligible"] else 1,
            item["evaluation"]["priority_value"],
            -float(item["line_item"].cpm or 0),
            -item["evaluation"]["pacing_score"],
            -(item["line_item"].delivery_weight or 1),
        ),
    )

    for index, candidate in enumerate(ranked_candidates, start=1):
        line_item = candidate["line_item"]
        evaluation = candidate["evaluation"]
        loss_reason = None
        win_reason = None

        if not evaluation["eligible"]:
            loss_reason = evaluation["reasons"][0]["code"] if evaluation["reasons"] else None
        elif winner_candidate and winner_candidate["line_item"].id == line_item.id:
            win_reason = "won_highest_bid"
        else:
            if winner_candidate:
                if evaluation["priority_value"] > winner_candidate["evaluation"]["priority_value"]:
                    loss_reason = LOSS_LABELS["priority"]
                elif float(line_item.cpm or 0) < float(winner_candidate["line_item"].cpm or 0):
                    loss_reason = LOSS_LABELS["lower_bid"]
                elif line_item.id in finalist_ids:
                    loss_reason = LOSS_LABELS["weighted_tiebreak"]
                else:
                    loss_reason = LOSS_LABELS["lower_bid"]

        db.session.add(
            AuctionCandidate(
                request_id=request_row.id,
                line_item_id=line_item.id,
                creative_id=evaluation["selected_creative"].id if evaluation["selected_creative"] else None,
                candidate_rank=index,
                eligible=evaluation["eligible"],
                win_reason=win_reason,
                loss_reason=loss_reason,
                priority_bucket=evaluation["priority_bucket"],
                cpm=Decimal(str(line_item.cpm or 0)),
                effective_cpm=Decimal(str(evaluation["effective_cpm"])),
                pacing_score=Decimal(str(evaluation["pacing_score"])),
                evaluation={
                    "checks": evaluation["checks"],
                    "reasons": evaluation["reasons"],
                    "creative_audit": evaluation["creative_audit"],
                },
            )
        )
        _event_log(
            request_row,
            line_item=line_item,
            creative=evaluation["selected_creative"],
            event_type="eligible" if evaluation["eligible"] else "ineligible",
            loss_reason=loss_reason,
            cpm=float(line_item.cpm or 0),
            details={
                "checks": evaluation["checks"],
                "priority_bucket": evaluation["priority_bucket"],
                "pacing_score": evaluation["pacing_score"],
            },
        )

    if winner_candidate:
        winning_line_item = winner_candidate["line_item"]
        winning_creative = winner_candidate["evaluation"]["selected_creative"]
        request_row.winning_line_item_id = winning_line_item.id
        request_row.winning_creative_id = winning_creative.id if winning_creative else None
        request_row.request_status = "evaluated"
        request_row.render_status = "response_ready"
        request_row.winner_reason = WIN_LABELS["highest_bid"]
        result = AuctionResult(
            request_id=request_row.id,
            winner_line_item_id=winning_line_item.id,
            winner_creative_id=winning_creative.id if winning_creative else None,
            status="filled",
            response_type=_render_mode(winning_creative),
            rendered=False,
            reason="Eligible winner selected after priority, bid, pacing, and weighted tie-break checks.",
            fallback_type=None,
            revenue=Decimal("0.0000"),
            cpm=Decimal(str(winning_line_item.cpm or 0)),
        )
        db.session.add(result)
        _event_log(
            request_row,
            line_item=winning_line_item,
            creative=winning_creative,
            event_type="win",
            cpm=float(winning_line_item.cpm or 0),
            details={"reason": request_row.winner_reason},
        )
    else:
        request_row.request_status = "evaluated"
        request_row.render_status = "fallback_ready"
        request_row.fallback_reason = "No eligible line item matched the request."
        db.session.add(
            AuctionResult(
                request_id=request_row.id,
                status="no_fill",
                response_type="house",
                rendered=False,
                reason="No eligible line item matched the request.",
                fallback_type="house",
                revenue=Decimal("0.0000"),
                cpm=Decimal("0.00"),
            )
        )

    db.session.commit()
    request_row = AdRequest.query.options(
        joinedload(AdRequest.result),
        selectinload(AdRequest.candidates).joinedload(AuctionCandidate.line_item),
        selectinload(AdRequest.candidates).joinedload(AuctionCandidate.creative),
    ).filter_by(id=request_row.id).first()
    return request_row


def _request_revenue(cpm_value):
    return round(float(cpm_value or 0) / 1000, 4)


def record_impression_for_request(request_identifier, payload=None):
    payload = payload or {}
    request_row = _request_for_tracking(request_identifier)
    if request_row.impression_logged:
        return {"ok": True, "impression_id": None, "request_id": request_row.request_id}
    if not request_row.result or request_row.result.status != "filled" or not request_row.winning_creative_id:
        return {"ok": False, "error": "No winning creative is available for impression tracking.", "request_id": request_row.request_id}

    payload_creative_id = payload.get("creative_id")
    if payload_creative_id and int(payload_creative_id) != request_row.winning_creative_id:
        return {"ok": False, "error": "Impression payload does not match the rendered creative.", "request_id": request_row.request_id}

    revenue = _request_revenue(request_row.result.cpm if request_row.result else 0)
    impression = ImpressionLog(
        request_id=request_row.id,
        creative_id=request_row.winning_creative_id,
        line_item_id=request_row.winning_line_item_id,
        order_id=request_row.winning_line_item.order_id if request_row.winning_line_item else None,
        ad_unit_id=request_row.ad_unit_id,
        slot_id=request_row.slot_id,
        page_url=payload.get("page_url") or request_row.page_url,
        page_type=payload.get("page_type") or request_row.page_type,
        device=payload.get("device_type") or request_row.device_type,
        session_id=payload.get("session_id") or request_row.session_id,
        request_key_values=payload.get("key_values") or request_row.request_params.get("key_values") or {},
        revenue=Decimal(str(revenue)),
        cpm=request_row.result.cpm if request_row.result else Decimal("0.00"),
    )
    db.session.add(impression)

    if request_row.winning_line_item:
        request_row.winning_line_item.delivered_impressions += 1
        request_row.winning_line_item.spent_amount = Decimal(str(float(request_row.winning_line_item.spent_amount or 0) + revenue))
        if request_row.winning_line_item.order:
            request_row.winning_line_item.order.spent_amount = Decimal(str(float(request_row.winning_line_item.order.spent_amount or 0) + revenue))

    request_row.impression_logged = True
    request_row.render_status = "rendered"
    if request_row.result:
        request_row.result.rendered = True
        request_row.result.revenue = Decimal(str(revenue))
    _event_log(
        request_row,
        line_item=request_row.winning_line_item,
        creative=request_row.winning_creative,
        event_type="impression",
        revenue=revenue,
        cpm=float(request_row.result.cpm if request_row.result else 0),
        details={"request_id": request_row.request_id},
    )
    db.session.commit()
    return {"ok": True, "impression_id": impression.id, "request_id": request_row.request_id}


def record_click_for_request(request_identifier, creative_id=None):
    request_row = _request_for_tracking(request_identifier)
    if not request_row.result or request_row.result.status != "filled" or not request_row.winning_creative_id:
        return None
    if creative_id is not None and int(creative_id) != request_row.winning_creative_id:
        return None

    revenue = _request_revenue(request_row.result.cpm if request_row.result else 0)
    click = ClickLog(
        request_id=request_row.id,
        creative_id=request_row.winning_creative_id,
        line_item_id=request_row.winning_line_item_id,
        order_id=request_row.winning_line_item.order_id if request_row.winning_line_item else None,
        ad_unit_id=request_row.ad_unit_id,
        slot_id=request_row.slot_id,
        page_url=request_row.page_url,
        device=request_row.device_type,
        session_id=request_row.session_id,
        landing_url=request_row.winning_creative.destination_url if request_row.winning_creative else "",
        revenue=Decimal(str(revenue)),
        cpm=request_row.result.cpm if request_row.result else Decimal("0.00"),
    )
    db.session.add(click)
    request_row.click_logged = True
    if request_row.render_status == "response_ready":
        request_row.render_status = "clicked_before_impression"
    _event_log(
        request_row,
        line_item=request_row.winning_line_item,
        creative=request_row.winning_creative,
        event_type="click",
        revenue=revenue,
        cpm=float(request_row.result.cpm if request_row.result else 0),
        details={"request_id": request_row.request_id},
    )
    db.session.commit()
    return click


def build_request_diagnostics(request_row):
    eligible_candidates = [candidate for candidate in request_row.candidates if candidate.eligible]
    ineligible_candidates = [candidate for candidate in request_row.candidates if not candidate.eligible]
    return {
        "request_id": request_row.request_id,
        "request": request_row.request_params,
        "winner": request_row.winning_line_item.name if request_row.winning_line_item else None,
        "creative": request_row.winning_creative.name if request_row.winning_creative else None,
        "winner_reason": request_row.winner_reason,
        "fallback_reason": request_row.fallback_reason,
        "render_status": request_row.render_status,
        "impression_status": request_row.impression_logged,
        "click_status": request_row.click_logged,
        "considered_count": len(request_row.candidates),
        "eligible_count": len(eligible_candidates),
        "ineligible_count": len(ineligible_candidates),
        "candidates": [
            {
                "line_item": candidate.line_item.name if candidate.line_item else "Unknown",
                "creative": candidate.creative.name if candidate.creative else None,
                "eligible": candidate.eligible,
                "win_reason": candidate.win_reason,
                "loss_reason": candidate.loss_reason,
                "priority_bucket": candidate.priority_bucket,
                "cpm": float(candidate.cpm or 0),
                "effective_cpm": float(candidate.effective_cpm or 0),
                "pacing_score": float(candidate.pacing_score or 0),
                "checks": candidate.evaluation.get("checks", []),
            }
            for candidate in request_row.candidates
        ],
    }
