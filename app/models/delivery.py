from datetime import datetime
from decimal import Decimal

from . import TABLE_PREFIX, db


class ImpressionLog(db.Model):
    __tablename__ = f"{TABLE_PREFIX}impressions"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}ad_requests.id", ondelete="SET NULL"))
    creative_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}creatives.id", ondelete="SET NULL"))
    line_item_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}line_items.id", ondelete="SET NULL"))
    order_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}orders.id", ondelete="SET NULL"))
    ad_unit_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}ad_units.id", ondelete="SET NULL"))
    slot_id = db.Column(db.String(120), nullable=False, index=True)
    page_url = db.Column(db.String(255), nullable=False)
    page_type = db.Column(db.String(60))
    device = db.Column(db.String(40))
    session_id = db.Column(db.String(120), index=True)
    request_key_values = db.Column(db.JSON)
    revenue = db.Column(db.Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
    cpm = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)


class ClickLog(db.Model):
    __tablename__ = f"{TABLE_PREFIX}clicks"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}ad_requests.id", ondelete="SET NULL"))
    creative_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}creatives.id", ondelete="SET NULL"))
    line_item_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}line_items.id", ondelete="SET NULL"))
    order_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}orders.id", ondelete="SET NULL"))
    ad_unit_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}ad_units.id", ondelete="SET NULL"))
    slot_id = db.Column(db.String(120), nullable=False, index=True)
    page_url = db.Column(db.String(255))
    device = db.Column(db.String(40))
    session_id = db.Column(db.String(120), index=True)
    landing_url = db.Column(db.String(255))
    revenue = db.Column(db.Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
    cpm = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)


class DeliveryLog(db.Model):
    __tablename__ = f"{TABLE_PREFIX}delivery_logs"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}ad_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    line_item_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}line_items.id", ondelete="SET NULL"))
    creative_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}creatives.id", ondelete="SET NULL"))
    event_type = db.Column(db.String(40), nullable=False, index=True)
    loss_reason = db.Column(db.String(120))
    revenue = db.Column(db.Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
    cpm = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
