from __future__ import annotations

from datetime import date
from random import Random
from urllib.parse import urlencode

from flask import url_for
from sqlalchemy.orm import joinedload, selectinload

from ..models import (
    AdUnit,
    ClickLog,
    ImpressionLog,
    KeyValueValue,
    LineItem,
    LineItemTargeting,
    Placement,
    PublisherSite,
    db,
)
from .eligibility import evaluate_line_item


PUBLISHER_NAME = "AdFlow Times"

CREATIVE_FORMATS_WITH_PLACEHOLDER = {"third_party_tag", "video", "ctv"}
CREATIVE_FORMATS_WITH_HTML = {"html", "native"}
RESERVED_REQUEST_KEYS = {
    "slot_id",
    "page",
    "page_type",
    "page_url",
    "size",
    "device",
    "category",
    "slot_position",
    "debug",
}

PUBLISHER_ARTICLES = [
    {
        "id": 1,
        "slug": "privacy-sandbox-publisher-revenue-outlook",
        "title": "Privacy Sandbox tests reshape how publishers price premium inventory",
        "category": "technology",
        "author": "Neha Sethi",
        "summary": "Operators are rebuilding demand expectations around richer contextual packages and clearer sell-side diagnostics.",
        "body": [
            "Premium publishers are increasingly packaging homepage takeovers, in-article depth placements, and high-attention side rails as one coherent story for buyers.",
            "Mock ad ops teams can use this page to validate whether page type targeting, category rules, and slot-specific creative sizes line up before delivery begins.",
            "The embedded debug console shows exactly which line item cleared targeting and why a candidate was rejected, turning the publisher surface into a teaching tool.",
        ],
    },
    {
        "id": 2,
        "slug": "sports-streaming-operators-balance-video-and-display-demand",
        "title": "Sports publishers balance streaming sponsorships with evergreen display demand",
        "category": "sports",
        "author": "Rohit Menon",
        "summary": "Teams are using slot-by-slot testing to understand when direct sold demand should outrank exchange-style fallback.",
        "body": [
            "Article pages remain valuable because they combine intent-rich reading moments with multiple layouts including top banners, sticky sidebars, and in-content rectangles.",
            "This mock page mirrors that setup with realistic slots so the same order and line item objects created in admin can serve into a live-looking news page.",
            "Click tracking and impression logging run through the same backend, which makes delivery behavior visible end to end for classroom or self-study use.",
        ],
    },
    {
        "id": 3,
        "slug": "contextual-packages-return-to-the-front-of-media-plans",
        "title": "Contextual packages return to the center of media planning",
        "category": "business",
        "author": "Aisha Kapoor",
        "summary": "Page taxonomy, section targeting, and cleaner inventory labels are helping sellers explain value without hiding behind black-box automation.",
        "body": [
            "Advertisers still want clarity on where they run, especially when homepage mastheads, category rails, and footer units carry different expectations.",
            "Inventory mapping inside the same Flask project helps demonstrate that ad units are not abstract records. They directly drive which creative can render in which slot.",
            "That connection is what makes the project behave like a mini ad-serving platform instead of a static admin CRUD exercise.",
        ],
    },
]

CATEGORY_FEATURES = {
    "technology": {
        "title": "Technology Briefing",
        "description": "Coverage focused on platforms, privacy changes, measurement, and how publishers adapt monetization tactics.",
    },
    "sports": {
        "title": "Sports Desk",
        "description": "Fast-moving headlines, live coverage modules, and sponsor-friendly inventory around high-attention moments.",
    },
    "business": {
        "title": "Business Watch",
        "description": "Market trends, platform economics, and revenue strategy stories built for returning professional readers.",
    },
}

SLOT_LIBRARY = {
    "top_banner": {
        "path": "top_banner",
        "name": "Top Banner",
        "size": "728x90",
        "position": "top",
        "page_type": "home",
        "environment": "web",
    },
    "sidebar_rectangle": {
        "path": "sidebar_rectangle",
        "name": "Sidebar Rectangle",
        "size": "300x250",
        "position": "sidebar",
        "page_type": "article",
        "environment": "web",
    },
    "in_article_1": {
        "path": "in_article_1",
        "name": "In Article Slot 1",
        "size": "300x250",
        "position": "in_article",
        "page_type": "article",
        "environment": "web",
    },
    "in_article_2": {
        "path": "in_article_2",
        "name": "In Article Slot 2",
        "size": "300x250",
        "position": "in_article",
        "page_type": "article",
        "environment": "web",
    },
    "sticky_footer": {
        "path": "sticky_footer",
        "name": "Sticky Footer",
        "size": "728x90",
        "position": "footer",
        "page_type": "sitewide",
        "environment": "web",
    },
    "video_preroll": {
        "path": "video_preroll",
        "name": "Video Preroll",
        "size": "640x360",
        "position": "video",
        "page_type": "article",
        "environment": "web",
    },
    "category_sidebar_rectangle": {
        "path": "category_sidebar_rectangle",
        "name": "Category Sidebar Rectangle",
        "size": "300x250",
        "position": "sidebar",
        "page_type": "category",
        "environment": "web",
    },
}

PLACEMENT_LIBRARY = {
    "Homepage Prime": ["top_banner", "sidebar_rectangle", "sticky_footer"],
    "Article Prime": ["top_banner", "in_article_1", "in_article_2", "sidebar_rectangle", "sticky_footer", "video_preroll"],
    "Category Prime": ["top_banner", "category_sidebar_rectangle", "sticky_footer"],
}


def get_article(article_id):
    return next((article for article in PUBLISHER_ARTICLES if article["id"] == article_id), None)


def get_category_context(category_slug):
    details = CATEGORY_FEATURES.get(category_slug)
    if not details:
        return None
    articles = [article for article in PUBLISHER_ARTICLES if article["category"] == category_slug]
    return {"slug": category_slug, "articles": articles, **details}


def get_page_slots(page_type):
    page_slot_ids = {
        "home": ["top_banner", "sidebar_rectangle", "sticky_footer"],
        "article": ["top_banner", "in_article_1", "in_article_2", "sidebar_rectangle", "sticky_footer", "video_preroll"],
        "category": ["top_banner", "category_sidebar_rectangle", "sticky_footer"],
    }.get(page_type, [])
    return [SLOT_LIBRARY[slot_id] for slot_id in page_slot_ids]


def bootstrap_mock_publisher_inventory():
    changed = False
    publisher_site = PublisherSite.query.filter_by(slug="adflow-times").first()
    if not publisher_site:
        publisher_site = PublisherSite(
            name=PUBLISHER_NAME,
            slug="adflow-times",
            domain="adflow-times.local",
            primary_category="news",
        )
        db.session.add(publisher_site)
        db.session.flush()
        changed = True
    ad_units_by_path = {ad_unit.path: ad_unit for ad_unit in AdUnit.query.all()}

    for slot in SLOT_LIBRARY.values():
        if slot["path"] in ad_units_by_path:
            ad_unit = ad_units_by_path[slot["path"]]
            if not ad_unit.ad_unit_code:
                ad_unit.ad_unit_code = slot["path"]
                changed = True
            if not ad_unit.slot_name:
                ad_unit.slot_name = slot["name"]
                changed = True
            if not ad_unit.publisher_site_id:
                ad_unit.publisher_site_id = publisher_site.id
                changed = True
            continue
        ad_unit = AdUnit(
            name=slot["name"],
            path=slot["path"],
            ad_unit_code=slot["path"],
            slot_name=slot["name"],
            size_support=slot["size"],
            environment=slot["environment"],
            is_active=True,
            publisher_site_id=publisher_site.id,
        )
        db.session.add(ad_unit)
        changed = True

    if changed:
        db.session.flush()
        ad_units_by_path = {ad_unit.path: ad_unit for ad_unit in AdUnit.query.all()}

    placements_by_name = {placement.name: placement for placement in Placement.query.options(selectinload(Placement.ad_units)).all()}
    for placement_name, slot_ids in PLACEMENT_LIBRARY.items():
        placement = placements_by_name.get(placement_name)
        if not placement:
            placement = Placement(
                name=placement_name,
                device_type="desktop,mobile",
                placement_format="display",
                notes="Auto-generated placement for embedded publisher pages.",
            )
            db.session.add(placement)
            db.session.flush()
            placements_by_name[placement_name] = placement
            changed = True

        desired_units = [ad_units_by_path[slot_id] for slot_id in slot_ids if slot_id in ad_units_by_path]
        desired_ids = {ad_unit.id for ad_unit in desired_units}
        current_ids = {ad_unit.id for ad_unit in placement.ad_units}
        if desired_ids != current_ids:
            placement.ad_units = desired_units
            changed = True

    if changed:
        db.session.commit()


def collect_request_key_values(args):
    key_values = {}
    for key, value in args.items():
        if key.startswith("kv_") and value:
            key_values[key[3:]] = value
        elif key not in RESERVED_REQUEST_KEYS and value:
            key_values[key] = value
    return key_values


def build_request_context(args, session_id):
    slot_id = (args.get("slot_id") or "").strip()
    slot = SLOT_LIBRARY.get(slot_id, {})
    debug_enabled = (args.get("debug") or "").strip().lower() in {"1", "true", "yes"}
    return {
        "slot_id": slot_id,
        "ad_unit_path": slot.get("path", slot_id),
        "page_url": (args.get("page_url") or "").strip(),
        "page_type": (args.get("page") or args.get("page_type") or slot.get("page_type") or "").strip(),
        "slot_position": (args.get("slot_position") or slot.get("position") or "").strip(),
        "device": (args.get("device") or "desktop").strip().lower(),
        "creative_size": (args.get("size") or slot.get("size") or "").strip().lower(),
        "content_category": (args.get("category") or "").strip().lower(),
        "geo": (args.get("geo") or "").strip().lower(),
        "audience": (args.get("audience") or "").strip().lower(),
        "key_values": collect_request_key_values(args),
        "session_id": session_id,
        "debug_enabled": debug_enabled,
    }


def _target_rule_values(line_item, target_type):
    return [
        (rule.target_value or "").strip().lower()
        for rule in line_item.targeting_rules
        if rule.target_type == target_type and (rule.target_value or "").strip()
    ]


def _add_check(checks, reasons, label, passed, message):
    checks.append({"label": label, "passed": passed, "message": message})
    if not passed:
        reasons.append(message)


def _count_session_impressions(line_item_id, session_id):
    if not session_id:
        return 0
    return ImpressionLog.query.filter_by(line_item_id=line_item_id, session_id=session_id).count()


def _pick_creative(approved_creatives):
    ordered = sorted(
        approved_creatives,
        key=lambda creative: (creative.created_at, creative.id or 0),
        reverse=True,
    )
    return ordered[0] if ordered else None


def _build_rejection_summary(reasons):
    if not reasons:
        return "Eligible"
    return "; ".join(dict.fromkeys(reasons))


def _normalize_size(value):
    return (value or "").strip().lower()


def _size_dimensions(size_value):
    normalized = _normalize_size(size_value)
    if "x" not in normalized:
        return None, None
    width_text, height_text = normalized.split("x", 1)
    try:
        return int(width_text), int(height_text)
    except ValueError:
        return None, None


def _creative_status_reason(creative, requested_size):
    if not creative.is_active:
        return f"{creative.name} is inactive."
    if creative.approval_status.lower() != "approved":
        return f"{creative.name} is not approved."
    if _normalize_size(creative.size) != requested_size:
        return f"{creative.name} size {creative.size} does not match slot size {requested_size}."
    return None


def _select_serving_creative(line_item, requested_size):
    creative_audit = []
    eligible_creatives = []
    for creative in line_item.creatives:
        reason = _creative_status_reason(creative, requested_size)
        creative_audit.append(
            {
                "creative": creative.name,
                "eligible": reason is None,
                "reason": reason or "Creative is eligible for serving.",
            }
        )
        if reason is None:
            eligible_creatives.append(creative)

    return _pick_creative(eligible_creatives), creative_audit


def _weighted_pick(candidates, request_context):
    if not candidates:
        return None

    best_priority = min(candidate["line_item"].priority for candidate in candidates)
    finalists = [
        candidate
        for candidate in candidates
        if candidate["line_item"].priority == best_priority
    ]
    if len(finalists) == 1:
        return finalists[0], finalists

    total_weight = sum(max(candidate["line_item"].delivery_weight or 1, 1) for candidate in finalists)
    stable_seed = "|".join(
        [
            request_context.get("slot_id", ""),
            request_context.get("page_url", ""),
            request_context.get("session_id", ""),
            request_context.get("creative_size", ""),
        ]
    )
    rng = Random(stable_seed)
    needle = rng.uniform(0, total_weight)
    running = 0
    for candidate in finalists:
        running += max(candidate["line_item"].delivery_weight or 1, 1)
        if needle <= running:
            return candidate, finalists
    return finalists[-1], finalists


def resolve_creative_render_mode(creative):
    snippet = (creative.tag_snippet or "").strip().lower()
    creative_format = (creative.creative_format or "").strip().lower()
    if creative_format in CREATIVE_FORMATS_WITH_PLACEHOLDER or "<script" in snippet:
        return "third_party"
    if creative_format in CREATIVE_FORMATS_WITH_HTML or (snippet and "<" in snippet and "script" not in snippet):
        return "html"
    return "image"


def resolve_creative_response_type(creative):
    render_mode = resolve_creative_render_mode(creative)
    if render_mode == "third_party":
        return "third_party_tag"
    if render_mode == "html":
        return "html"
    return "image"


def decide_ad_delivery(request_context):
    requested_size = _normalize_size(request_context.get("creative_size"))
    requested_page_type = (request_context.get("page_type") or "").strip().lower()
    requested_position = (request_context.get("slot_position") or "").strip().lower()
    request_ad_unit_path = (request_context.get("ad_unit_path") or "").strip().lower()
    request_device = (request_context.get("device") or "").strip().lower()
    current_day = date.today()
    ad_unit = AdUnit.query.filter_by(path=request_context.get("ad_unit_path")).first()

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

    candidates = []
    eligible_candidates = []

    for line_item in line_items:
        base_evaluation = evaluate_line_item(line_item, request_context, current_day=current_day)
        reasons = list(base_evaluation["reasons"])
        checks = list(base_evaluation["checks"])
        reject_details = []

        order = line_item.order
        _add_check(checks, reasons, "Order Status", order.status.lower() == "active", "Order is paused or not active.")
        _add_check(
            checks,
            reasons,
            "Order Dates",
            order.start_date <= current_day <= order.end_date,
            "Order dates do not cover the request.",
        )
        _add_check(
            checks,
            reasons,
            "Goal Remaining",
            not line_item.goal_impressions or line_item.delivered_impressions < line_item.goal_impressions,
            "Line item has exhausted its impression goal.",
        )
        _add_check(
            checks,
            reasons,
            "Ad Unit Exists",
            ad_unit is not None,
            "Requested ad unit does not exist.",
        )
        _add_check(
            checks,
            reasons,
            "Ad Unit Status",
            ad_unit.is_active if ad_unit else False,
            "Requested ad unit is inactive.",
        )
        _add_check(
            checks,
            reasons,
            "Slot Size",
            _normalize_size(ad_unit.size_support) == requested_size if ad_unit else False,
            "Requested slot size does not match the ad unit definition.",
        )

        ad_unit_rules = _target_rule_values(line_item, "ad_unit")
        _add_check(
            checks,
            reasons,
            "Ad Unit",
            bool(ad_unit_rules) and request_ad_unit_path in ad_unit_rules,
            "Ad unit targeting does not match the request.",
        )

        page_type_rules = _target_rule_values(line_item, "page_type")
        _add_check(
            checks,
            reasons,
            "Page Type",
            True if not page_type_rules else requested_page_type in page_type_rules,
            "Page type targeting does not match the request.",
        )

        slot_position_rules = _target_rule_values(line_item, "slot_position")
        _add_check(
            checks,
            reasons,
            "Slot Position",
            True if not slot_position_rules else requested_position in slot_position_rules,
            "Slot position targeting does not match the request.",
        )

        session_cap_ok = True
        if line_item.frequency_cap:
            session_cap_ok = _count_session_impressions(line_item.id, request_context.get("session_id")) < line_item.frequency_cap
        _add_check(
            checks,
            reasons,
            "Frequency Cap",
            session_cap_ok,
            "Frequency cap reached for the current session.",
        )

        exact_device_match = True
        if line_item.device_targeting:
            exact_device_match = request_device in [
                device.strip().lower() for device in line_item.device_targeting.split(",") if device.strip()
            ]
        _add_check(
            checks,
            reasons,
            "Device Type",
            exact_device_match,
            "Device targeting does not match the request.",
        )

        selected_creative, creative_audit = _select_serving_creative(line_item, requested_size)
        if not selected_creative:
            for creative_check in creative_audit:
                if not creative_check["eligible"]:
                    reject_details.append(creative_check["reason"])
            _add_check(
                checks,
                reasons,
                "Creative Status",
                False,
                creative_audit[0]["reason"] if creative_audit else "No creative is linked to the line item.",
            )
        else:
            checks.append({"label": "Creative Status", "passed": True, "message": f"{selected_creative.name} matched exactly."})

        eligible = not reasons and selected_creative is not None
        candidate = {
            "line_item": line_item,
            "order": order,
            "creative": selected_creative,
            "eligible": eligible,
            "checks": checks,
            "reasons": reasons,
            "summary": _build_rejection_summary(reasons),
            "weight": max(line_item.delivery_weight or 1, 1),
            "reject_details": reject_details,
            "creative_audit": creative_audit,
            "ad_unit_match": request_ad_unit_path in ad_unit_rules,
        }
        candidates.append(candidate)
        if eligible:
            eligible_candidates.append(candidate)

    winning_candidate, finalists = _weighted_pick(eligible_candidates, request_context) if eligible_candidates else (None, [])
    finalist_ids = {candidate["line_item"].id for candidate in finalists}
    if winning_candidate:
        for candidate in eligible_candidates:
            if candidate["line_item"].id == winning_candidate["line_item"].id:
                continue
            if candidate["line_item"].id in finalist_ids:
                candidate["summary"] = (
                    f"Lost weighted tie-break to {winning_candidate['line_item'].name} "
                    f"(weight {winning_candidate['line_item'].delivery_weight})."
                )
            else:
                candidate["summary"] = (
                    f"Lower serving priority than {winning_candidate['line_item'].name}."
                )

    debug_candidates = [
        {
            "line_item": candidate["line_item"].name,
            "order": candidate["order"].name,
            "creative": candidate["creative"].name if candidate["creative"] else None,
            "eligible": candidate["eligible"],
            "priority": candidate["line_item"].priority,
            "weight": candidate["line_item"].delivery_weight,
            "reason": candidate["summary"],
            "rejected_checks": list(dict.fromkeys(candidate["reasons"])),
            "creative_checks": candidate["creative_audit"],
        }
        for candidate in sorted(
            candidates,
            key=lambda item: (
                0 if item["eligible"] else 1,
                item["line_item"].priority,
                -(item["line_item"].delivery_weight or 1),
                -item["line_item"].id,
            ),
        )
    ]

    debug = {
        "requested_slot": request_context.get("slot_id"),
        "requested_size": request_context.get("creative_size"),
        "page_type": request_context.get("page_type"),
        "slot_position": request_context.get("slot_position"),
        "device": request_context.get("device"),
        "selected_line_item": winning_candidate["line_item"].name if winning_candidate else None,
        "selected_creative": winning_candidate["creative"].name if winning_candidate and winning_candidate["creative"] else None,
        "reason": (
            f"Selected at priority {winning_candidate['line_item'].priority} "
            f"with weight {winning_candidate['line_item'].delivery_weight}."
            if winning_candidate
            else "No eligible line item matched the request. House fallback served."
        ),
        "house_served": winning_candidate is None,
        "candidates": debug_candidates if request_context.get("debug_enabled") else [],
    }

    if not winning_candidate:
        return {
            "filled": False,
            "response_type": "house",
            "status": "house",
            "request_context": request_context,
            "debug": debug,
        }

    creative = winning_candidate["creative"]
    line_item = winning_candidate["line_item"]
    order = winning_candidate["order"]
    click_query = urlencode(
        {
            "line_item_id": line_item.id,
            "order_id": order.id,
            "slot_id": request_context.get("slot_id"),
            "page_url": request_context.get("page_url"),
            "device": request_context.get("device"),
            "ad_unit_id": ad_unit.id if ad_unit else "",
        }
    )
    click_url = url_for("publisher.track_click", creative_id=creative.id)
    click_url = f"{click_url}?{click_query}" if click_query else click_url
    impression_query = urlencode(
        {
            "creative_id": creative.id,
            "line_item_id": line_item.id,
            "order_id": order.id,
            "ad_unit_id": ad_unit.id if ad_unit else "",
            "slot_id": request_context.get("slot_id"),
            "page_url": request_context.get("page_url"),
            "page_type": request_context.get("page_type"),
            "device": request_context.get("device"),
            "session_id": request_context.get("session_id"),
        }
    )
    impression_url = url_for("publisher.track_impression")
    impression_url = f"{impression_url}?{impression_query}" if impression_query else impression_url
    width, height = _size_dimensions(creative.size)
    creative_type = resolve_creative_response_type(creative)
    image_url = (
        url_for("publisher.creative_asset", creative_id=creative.id)
        if creative_type == "image"
        else None
    )

    return {
        "filled": True,
        "response_type": "creative",
        "status": "filled",
        "slot_id": request_context.get("slot_id"),
        "creative_id": creative.id,
        "line_item_id": line_item.id,
        "order_id": order.id,
        "creative_type": creative_type,
        "image_url": image_url,
        "creative": creative,
        "line_item": line_item,
        "order": order,
        "ad_unit": ad_unit,
        "click_url": click_url,
        "impression_url": impression_url,
        "width": width,
        "height": height,
        "advertiser": line_item.advertiser.name if line_item.advertiser else None,
        "render_mode": resolve_creative_render_mode(creative),
        "request_context": request_context,
        "debug": debug,
        "impression_payload": {
            "creative_id": creative.id,
            "line_item_id": line_item.id,
            "order_id": order.id,
            "ad_unit_id": ad_unit.id if ad_unit else None,
            "slot_id": request_context.get("slot_id"),
            "page_url": request_context.get("page_url"),
            "page_type": request_context.get("page_type"),
            "device": request_context.get("device"),
            "session_id": request_context.get("session_id"),
            "key_values": request_context.get("key_values") or {},
        },
    }


def record_impression(payload):
    impression = ImpressionLog(
        creative_id=payload.get("creative_id"),
        line_item_id=payload.get("line_item_id"),
        order_id=payload.get("order_id"),
        ad_unit_id=payload.get("ad_unit_id"),
        slot_id=payload.get("slot_id") or "",
        page_url=payload.get("page_url") or "",
        page_type=payload.get("page_type"),
        device=payload.get("device"),
        session_id=payload.get("session_id"),
        request_key_values=payload.get("key_values") or {},
    )
    db.session.add(impression)

    line_item = LineItem.query.get(payload.get("line_item_id"))
    if line_item:
        line_item.delivered_impressions += 1

    db.session.commit()
    return impression


def record_click(creative, line_item_id=None, order_id=None, slot_id="", page_url="", device="", session_id="", ad_unit_id=None):
    click = ClickLog(
        creative_id=creative.id if creative else None,
        line_item_id=line_item_id,
        order_id=order_id,
        ad_unit_id=ad_unit_id,
        slot_id=slot_id or "",
        page_url=page_url,
        device=device,
        session_id=session_id,
        landing_url=creative.destination_url if creative else "",
    )
    db.session.add(click)
    db.session.commit()
    return click


def get_mock_house_ad(slot_id, size):
    palette = [
        ("#123b6d", "#6cb6ff"),
        ("#0f5132", "#58c4a1"),
        ("#8a4b12", "#f7b85a"),
    ]
    start, end = palette[hash(slot_id) % len(palette)]
    return {
        "slot_id": slot_id,
        "size": size,
        "headline": "House Ad Fallback",
        "body": "No paid line item matched this request, so the mock publisher filled the slot with an internal promo.",
        "cta": "Open Admin Console",
        "background_start": start,
        "background_end": end,
    }


def preview_destination_for_slot(slot_id, **extra):
    slot = SLOT_LIBRARY.get(slot_id)
    if not slot:
        return url_for("publisher.home")

    page_type = slot["page_type"]
    query = {"debug": 1, "highlight_slot": slot_id}
    query.update(extra)

    if page_type == "home":
        return f"{url_for('publisher.home')}?{urlencode(query)}"
    if page_type == "article":
        article = PUBLISHER_ARTICLES[0]
        return f"{url_for('publisher.article', article_id=article['id'])}?{urlencode(query)}"
    if page_type == "category":
        category_slug = next(iter(CATEGORY_FEATURES))
        return f"{url_for('publisher.category', category_slug=category_slug)}?{urlencode(query)}"
    return f"{url_for('publisher.home')}?{urlencode(query)}"


def preview_destination_for_line_item(line_item):
    ad_unit_rule = next((rule for rule in line_item.targeting_rules if rule.target_type == "ad_unit" and rule.target_value), None)
    slot_id = (ad_unit_rule.target_value or "").strip() if ad_unit_rule else "homepage_top_leaderboard"
    return preview_destination_for_slot(slot_id, line_item_id=line_item.id)


def preview_destination_for_creative(creative):
    return preview_destination_for_line_item(creative.line_item)
