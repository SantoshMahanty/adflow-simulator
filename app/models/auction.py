from datetime import datetime
from decimal import Decimal

from . import TABLE_PREFIX, db


class AuctionSimulation(db.Model):
    __tablename__ = f"{TABLE_PREFIX}auction_simulations"

    id = db.Column(db.Integer, primary_key=True)
    mode = db.Column(db.String(50), nullable=False)
    ad_unit_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}ad_units.id", ondelete="SET NULL"))
    request_context = db.Column(db.JSON, nullable=False)
    winner_line_item_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{TABLE_PREFIX}line_items.id", ondelete="SET NULL"),
    )
    evaluation_data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    ad_unit = db.relationship("AdUnit")
    winner_line_item = db.relationship("LineItem", back_populates="simulations")


class AdRequest(db.Model):
    __tablename__ = f"{TABLE_PREFIX}ad_requests"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    publisher_site_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}publisher_sites.id", ondelete="SET NULL"))
    ad_unit_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}ad_units.id", ondelete="SET NULL"))
    winning_line_item_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}line_items.id", ondelete="SET NULL"))
    winning_creative_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}creatives.id", ondelete="SET NULL"))
    ad_unit_code = db.Column(db.String(255), nullable=False, index=True)
    slot_id = db.Column(db.String(120), nullable=False, index=True)
    page_url = db.Column(db.String(255), nullable=False)
    page_type = db.Column(db.String(60))
    device_type = db.Column(db.String(40))
    geo = db.Column(db.String(80))
    session_id = db.Column(db.String(120), index=True)
    content_category = db.Column(db.String(80))
    creative_size = db.Column(db.String(30))
    request_params = db.Column(db.JSON, nullable=False)
    request_status = db.Column(db.String(40), nullable=False, default="received")
    render_status = db.Column(db.String(40), nullable=False, default="pending")
    winner_reason = db.Column(db.String(255))
    fallback_reason = db.Column(db.String(255))
    impression_logged = db.Column(db.Boolean, nullable=False, default=False)
    click_logged = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    publisher_site = db.relationship("PublisherSite", back_populates="ad_requests")
    ad_unit = db.relationship("AdUnit", back_populates="ad_requests")
    winning_line_item = db.relationship("LineItem", back_populates="winning_requests", foreign_keys=[winning_line_item_id])
    winning_creative = db.relationship("Creative", foreign_keys=[winning_creative_id])
    candidates = db.relationship("AuctionCandidate", back_populates="request", cascade="all, delete-orphan", order_by="AuctionCandidate.candidate_rank")
    result = db.relationship("AuctionResult", back_populates="request", uselist=False, cascade="all, delete-orphan")


class AuctionCandidate(db.Model):
    __tablename__ = f"{TABLE_PREFIX}auction_candidates"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}ad_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    line_item_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}line_items.id", ondelete="SET NULL"))
    creative_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}creatives.id", ondelete="SET NULL"))
    candidate_rank = db.Column(db.Integer, nullable=False, default=0)
    eligible = db.Column(db.Boolean, nullable=False, default=False)
    win_reason = db.Column(db.String(120))
    loss_reason = db.Column(db.String(120))
    priority_bucket = db.Column(db.String(40))
    cpm = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    effective_cpm = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    pacing_score = db.Column(db.Numeric(8, 4), nullable=False, default=Decimal("0.0000"))
    evaluation = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    request = db.relationship("AdRequest", back_populates="candidates")
    line_item = db.relationship("LineItem", back_populates="auction_candidates")
    creative = db.relationship("Creative")


class AuctionResult(db.Model):
    __tablename__ = f"{TABLE_PREFIX}auction_results"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}ad_requests.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    winner_line_item_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}line_items.id", ondelete="SET NULL"))
    winner_creative_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}creatives.id", ondelete="SET NULL"))
    status = db.Column(db.String(40), nullable=False, default="no_fill")
    response_type = db.Column(db.String(40), nullable=False, default="house")
    rendered = db.Column(db.Boolean, nullable=False, default=False)
    reason = db.Column(db.String(255))
    fallback_type = db.Column(db.String(40))
    revenue = db.Column(db.Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
    cpm = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    request = db.relationship("AdRequest", back_populates="result")
    winner_line_item = db.relationship("LineItem", foreign_keys=[winner_line_item_id])
    winner_creative = db.relationship("Creative", foreign_keys=[winner_creative_id])
