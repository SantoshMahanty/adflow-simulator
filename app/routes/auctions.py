from flask import Blueprint, jsonify, render_template, request
from sqlalchemy.orm import joinedload, selectinload

from ..models import AdRequest, AuctionCandidate
from ..services import build_request_diagnostics, login_required


auctions_bp = Blueprint("auctions", __name__, url_prefix="/auctions")


@auctions_bp.route("/")
@login_required
def index():
    ad_requests = (
        AdRequest.query.options(
            joinedload(AdRequest.ad_unit),
            joinedload(AdRequest.winning_line_item),
            joinedload(AdRequest.winning_creative),
            joinedload(AdRequest.result),
        )
        .order_by(AdRequest.created_at.desc())
        .limit(100)
        .all()
    )
    return render_template("auctions/index.html", page_title="Auction Logs", ad_requests=ad_requests)


@auctions_bp.route("/<request_id>")
@login_required
def detail(request_id):
    ad_request = (
        AdRequest.query.options(
            joinedload(AdRequest.ad_unit),
            joinedload(AdRequest.publisher_site),
            joinedload(AdRequest.winning_line_item),
            joinedload(AdRequest.winning_creative),
            joinedload(AdRequest.result),
            selectinload(AdRequest.candidates).joinedload(AuctionCandidate.line_item),
            selectinload(AdRequest.candidates).joinedload(AuctionCandidate.creative),
        )
        .filter_by(request_id=request_id)
        .first_or_404()
    )
    diagnostics = build_request_diagnostics(ad_request)
    if request.args.get("format") == "json":
        return jsonify(diagnostics)
    return render_template(
        "auctions/detail.html",
        page_title=f"Auction {ad_request.request_id}",
        ad_request=ad_request,
        diagnostics=diagnostics,
    )
