from uuid import uuid4

from flask import Blueprint, Response, abort, jsonify, redirect, render_template, request, session, url_for

from ..models import AdRequest, Creative, LineItem, PublisherSite
from ..services.ad_server import (
    PUBLISHER_ARTICLES,
    PUBLISHER_NAME,
    bootstrap_mock_publisher_inventory,
    get_article,
    get_category_context,
    get_mock_house_ad,
    get_page_slots,
    preview_destination_for_creative,
    preview_destination_for_line_item,
    preview_destination_for_slot,
)
from ..services import execute_auction, record_click_for_request, record_impression_for_request
from ..services.helpers import parse_int


publisher_bp = Blueprint("publisher", __name__)
TEST_AUCTION_SLOT = {
    "path": "test_top_banner",
    "name": "Auction Test Top Banner",
    "size": "728x90",
    "position": "top",
    "page_type": "auction_test",
    "environment": "web",
}


def ensure_publisher_session():
    session_id = session.get("publisher_session_id")
    if not session_id:
        session_id = f"pub-{uuid4().hex}"
        session["publisher_session_id"] = session_id
    return session_id


def build_page_context(page_type, page_title, category="", article=None):
    return {
        "page_title": page_title,
        "publisher_name": PUBLISHER_NAME,
        "page_type": page_type,
        "page_url": request.base_url,
        "debug_mode": request.args.get("debug") == "1",
        "highlight_slot": request.args.get("highlight_slot", "").strip(),
        "slots": get_page_slots(page_type),
        "page_category": category,
        "article": article,
        "articles": PUBLISHER_ARTICLES,
    }


def build_impression_payload_from_request():
    payload = request.get_json(silent=True) or {}
    if not payload:
        payload = {
            "request_id": request.args.get("request_id", "").strip(),
            "creative_id": parse_int(request.args.get("creative_id"), None),
            "line_item_id": parse_int(request.args.get("line_item_id"), None),
            "order_id": parse_int(request.args.get("order_id"), None),
            "ad_unit_id": parse_int(request.args.get("ad_unit_id"), None),
            "slot_id": request.args.get("slot_id", "").strip(),
            "page_url": request.args.get("page_url", "").strip(),
            "page_type": request.args.get("page_type", "").strip(),
            "device": request.args.get("device", "").strip(),
            "session_id": request.args.get("session_id", "").strip(),
            "key_values": {},
        }
    payload["session_id"] = payload.get("session_id") or ensure_publisher_session()
    return payload


def build_creative_svg(creative):
    advertiser_name = creative.line_item.advertiser.name if creative.line_item and creative.line_item.advertiser else "Advertiser"
    width_text, height_text = (creative.size or "300x250").lower().split("x", 1) if "x" in (creative.size or "").lower() else ("300", "250")
    width = int(width_text)
    height = int(height_text)
    headline = (creative.preview_text or creative.name or "Creative").strip()
    safe_headline = headline.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_advertiser = advertiser_name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_size = (creative.size or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{safe_headline}">
<defs>
<linearGradient id="creative-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
<stop offset="0%" stop-color="#102a56" />
<stop offset="100%" stop-color="#1f6ed4" />
</linearGradient>
</defs>
<rect width="{width}" height="{height}" rx="14" ry="14" fill="url(#creative-gradient)" />
<rect x="12" y="12" width="{max(width - 24, 0)}" height="{max(height - 24, 0)}" rx="12" ry="12" fill="rgba(255,255,255,0.08)" />
<text x="24" y="{max(int(height * 0.34), 28)}" fill="#ffffff" font-family="Arial, sans-serif" font-size="{max(int(height * 0.18), 14)}" font-weight="700">{safe_headline}</text>
<text x="24" y="{max(int(height * 0.62), 48)}" fill="#dbeafe" font-family="Arial, sans-serif" font-size="{max(int(height * 0.12), 12)}">{safe_advertiser}</text>
<text x="{max(width - 24, 24)}" y="{max(height - 18, 18)}" text-anchor="end" fill="#bfdbfe" font-family="Arial, sans-serif" font-size="{max(int(height * 0.11), 11)}">{safe_size}</text>
</svg>"""


@publisher_bp.before_app_request
def ensure_mock_inventory():
    if not getattr(publisher_bp, "_publisher_inventory_ready", False):
        bootstrap_mock_publisher_inventory()
        if not PublisherSite.query.filter_by(slug="adflow-times").first():
            from ..models import db

            db.session.add(
                PublisherSite(
                    name=PUBLISHER_NAME,
                    slug="adflow-times",
                    domain="adflow-times.local",
                    primary_category="news",
                )
            )
            db.session.commit()
        publisher_bp._publisher_inventory_ready = True


@publisher_bp.route("/publisher/home")
def home():
    ensure_publisher_session()
    context = build_page_context("home", "Publisher Home", category="news")
    return render_template("publisher/home.html", **context)


@publisher_bp.route("/publisher/test-auction")
def test_auction():
    ensure_publisher_session()
    context = build_page_context("auction_test", "Auction Test Page", category="news")
    context["slots"] = [TEST_AUCTION_SLOT]
    context["test_summary"] = {
        "slot_id": TEST_AUCTION_SLOT["path"],
        "expected_candidates": 5,
        "expected_behavior": "All 5 line items should be evaluated, but only the winning creative should render.",
    }
    return render_template("publisher/test_auction.html", **context)


@publisher_bp.route("/publisher/article/<int:article_id>")
def article(article_id):
    ensure_publisher_session()
    article_record = get_article(article_id)
    if not article_record:
        abort(404)
    context = build_page_context("article", article_record["title"], category=article_record["category"], article=article_record)
    return render_template("publisher/article.html", **context)


@publisher_bp.route("/publisher/category/<category_slug>")
def category(category_slug):
    ensure_publisher_session()
    category_context = get_category_context(category_slug)
    if not category_context:
        abort(404)
    context = build_page_context("category", category_context["title"], category=category_slug)
    context["category_context"] = category_context
    return render_template("publisher/category.html", **context)


@publisher_bp.route("/publisher/preview/line-item/<int:line_item_id>")
def preview_line_item(line_item_id):
    line_item = LineItem.query.get_or_404(line_item_id)
    return redirect(preview_destination_for_line_item(line_item))


@publisher_bp.route("/publisher/preview/creative/<int:creative_id>")
def preview_creative(creative_id):
    creative = Creative.query.get_or_404(creative_id)
    return redirect(preview_destination_for_creative(creative))


@publisher_bp.route("/publisher/preview/slot/<slot_id>")
def preview_slot(slot_id):
    return redirect(preview_destination_for_slot(slot_id))


@publisher_bp.route("/publisher/creative-asset/<int:creative_id>.svg")
def creative_asset(creative_id):
    creative = Creative.query.get_or_404(creative_id)
    return Response(build_creative_svg(creative), mimetype="image/svg+xml")


@publisher_bp.route("/serve-ad")
@publisher_bp.route("/publisher/ad")
def serve_ad():
    session_id = ensure_publisher_session()
    request_context = {
        "ad_unit_code": request.args.get("ad_unit_code", "").strip() or request.args.get("slot_id", "").strip(),
        "slot_id": request.args.get("slot_id", "").strip(),
        "page_url": request.args.get("page_url", "").strip() or request.base_url,
        "page_type": request.args.get("page", "").strip() or request.args.get("page_type", "").strip(),
        "device_type": request.args.get("device_type", "").strip() or request.args.get("device", "").strip(),
        "size": request.args.get("size", "").strip(),
        "category": request.args.get("category", "").strip() or request.args.get("content_category", "").strip(),
        "slot_position": request.args.get("slot_position", "").strip(),
        "geo": request.args.get("geo", "").strip(),
        "audience": request.args.get("audience", "").strip(),
        "session_id": session_id,
        "timestamp": request.args.get("timestamp", "").strip(),
        "key_values": {key[3:]: value for key, value in request.args.items() if key.startswith("kv_") and value},
        "debug": request.args.get("debug") == "1",
    }
    auction_request = execute_auction(request_context)
    result = auction_request.result
    debug = {
        "requested_slot": auction_request.slot_id,
        "requested_size": auction_request.creative_size,
        "device": auction_request.device_type,
        "considered_count": len(auction_request.candidates),
        "eligible_count": len([candidate for candidate in auction_request.candidates if candidate.eligible]),
        "ineligible_count": len([candidate for candidate in auction_request.candidates if not candidate.eligible]),
        "reason": result.reason if result else auction_request.fallback_reason,
        "selected_line_item": auction_request.winning_line_item.name if auction_request.winning_line_item else None,
        "selected_creative": auction_request.winning_creative.name if auction_request.winning_creative else None,
        "candidates": [
            {
                "line_item": candidate.line_item.name if candidate.line_item else "Unknown",
                "priority": candidate.line_item.priority if candidate.line_item else None,
                "weight": candidate.line_item.delivery_weight if candidate.line_item else None,
                "eligible": candidate.eligible,
                "reason": candidate.win_reason or candidate.loss_reason or "eligible",
                "rejected_checks": [check["message"] for check in candidate.evaluation.get("checks", []) if not check.get("passed")],
            }
            for candidate in auction_request.candidates
        ]
        if request.args.get("debug") == "1"
        else [],
    }

    if auction_request.winning_creative and result and result.status == "filled":
        render_mode = result.response_type
        delivery = {
            "creative": auction_request.winning_creative,
            "line_item": auction_request.winning_line_item,
            "order": auction_request.winning_line_item.order if auction_request.winning_line_item else None,
            "request_id": auction_request.request_id,
            "image_url": url_for("publisher.creative_asset", creative_id=auction_request.winning_creative_id)
            if render_mode == "image"
            else None,
            "click_url": url_for("publisher.track_click", creative_id=auction_request.winning_creative_id, request_id=auction_request.request_id),
            "render_mode": "third_party" if render_mode == "third_party_tag" else render_mode,
            "width": parse_int((auction_request.creative_size or "x").split("x", 1)[0], None),
            "height": parse_int((auction_request.creative_size or "x").split("x", 1)[1] if "x" in (auction_request.creative_size or "") else "", None),
        }
        html = render_template("publisher/partials/served_creative.html", delivery=delivery)
        return jsonify(
            {
                "status": "filled",
                "filled": True,
                "request_id": auction_request.request_id,
                "slot_id": auction_request.slot_id,
                "creative_id": auction_request.winning_creative_id,
                "line_item_id": auction_request.winning_line_item_id,
                "order_id": auction_request.winning_line_item.order_id if auction_request.winning_line_item else None,
                "creative_type": result.response_type,
                "image_url": delivery["image_url"],
                "response_type": result.response_type,
                "render_status": auction_request.render_status,
                "html": html,
                "click_url": delivery["click_url"],
                "impression_url": url_for("publisher.track_impression", request_id=auction_request.request_id),
                "width": delivery["width"],
                "height": delivery["height"],
                "advertiser": auction_request.winning_line_item.advertiser.name if auction_request.winning_line_item else None,
                "impression_payload": {
                    "request_id": auction_request.request_id,
                    "creative_id": auction_request.winning_creative_id,
                    "page_url": auction_request.page_url,
                    "page_type": auction_request.page_type,
                    "device_type": auction_request.device_type,
                    "session_id": auction_request.session_id,
                    "key_values": auction_request.request_params.get("key_values", {}),
                },
                "auction_url": url_for("auctions.detail", request_id=auction_request.request_id),
                "debug": debug,
            }
        )

    house_ad = get_mock_house_ad(auction_request.slot_id, auction_request.creative_size)
    html = render_template("publisher/partials/house_ad.html", house_ad=house_ad)
    return jsonify(
        {
            "status": "house",
            "filled": False,
            "request_id": auction_request.request_id,
            "slot_id": auction_request.slot_id,
            "creative_id": None,
            "line_item_id": None,
            "order_id": None,
            "creative_type": "house",
            "image_url": None,
            "response_type": "house",
            "render_status": auction_request.render_status,
            "html": html,
            "click_url": None,
            "impression_url": None,
            "width": parse_int((auction_request.creative_size or "x").split("x", 1)[0], None),
            "height": parse_int((auction_request.creative_size or "x").split("x", 1)[1] if "x" in (auction_request.creative_size or "") else "", None),
            "advertiser": "House",
            "impression_payload": None,
            "auction_url": url_for("auctions.detail", request_id=auction_request.request_id),
            "debug": debug,
        }
    )


@publisher_bp.route("/track/impression", methods=["GET", "POST"])
def track_impression():
    payload = build_impression_payload_from_request()
    if not payload.get("request_id"):
        return jsonify({"ok": False, "error": "Missing request id for impression tracking."}), 400
    result = record_impression_for_request(payload["request_id"], payload)
    status_code = 200 if result.get("ok") else 409
    return jsonify(result), status_code


@publisher_bp.route("/track/click/<int:creative_id>")
@publisher_bp.route("/track/click", methods=["POST"])
def track_click(creative_id=None):
    if request.method == "POST":
        payload = request.get_json(silent=True) or request.form
        request_id = (payload.get("request_id") or "").strip()
        creative_id = parse_int(payload.get("creative_id"), None)
    else:
        payload = request.args
        request_id = request.args.get("request_id", "").strip()

    if request_id and creative_id is None:
        ad_request = AdRequest.query.filter_by(request_id=request_id).first()
        creative_id = ad_request.winning_creative_id if ad_request else None

    if request_id:
        ad_request = AdRequest.query.filter_by(request_id=request_id).first_or_404()
        if creative_id != ad_request.winning_creative_id:
            abort(409)

    creative = Creative.query.get_or_404(creative_id)
    if request_id:
        click = record_click_for_request(request_id, creative_id=creative_id)
        if click is None:
            abort(409)
    return redirect(creative.destination_url or "/publisher/home")
