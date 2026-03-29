from datetime import datetime
from decimal import Decimal

from . import TABLE_PREFIX, db


class LineItem(db.Model):
    __tablename__ = f"{TABLE_PREFIX}line_items"

    id = db.Column(db.Integer, primary_key=True)
    advertiser_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{TABLE_PREFIX}advertisers.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{TABLE_PREFIX}orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(180), nullable=False)
    line_item_type = db.Column(db.String(60), nullable=False)
    priority = db.Column(db.Integer, nullable=False, default=6)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    goal_impressions = db.Column(db.Integer, nullable=False, default=0)
    delivered_impressions = db.Column(db.Integer, nullable=False, default=0)
    cpm = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    frequency_cap = db.Column(db.Integer, nullable=False, default=0)
    creative_size = db.Column(db.String(30), nullable=False)
    geo_targeting = db.Column(db.String(255))
    device_targeting = db.Column(db.String(255))
    audience_targeting = db.Column(db.String(255))
    status = db.Column(db.String(50), nullable=False, default="draft")
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    advertiser = db.relationship("Advertiser", back_populates="line_items")
    order = db.relationship("Order", back_populates="line_items")
    creatives = db.relationship("Creative", back_populates="line_item", cascade="all, delete-orphan")
    targeting_rules = db.relationship(
        "LineItemTargeting",
        back_populates="line_item",
        cascade="all, delete-orphan",
        order_by="LineItemTargeting.target_type",
    )
    simulations = db.relationship("AuctionSimulation", back_populates="winner_line_item", passive_deletes=True)
    troubleshooting_rows = db.relationship(
        "TroubleshootingSheetRow",
        back_populates="line_item",
        passive_deletes=True,
    )

    @property
    def delivery_percent(self):
        if not self.goal_impressions:
            return 0
        return round((self.delivered_impressions / self.goal_impressions) * 100, 1)

    @property
    def remaining_goal(self):
        return max(self.goal_impressions - self.delivered_impressions, 0)

    @property
    def targeting_summary(self):
        parts = []
        if self.geo_targeting:
            parts.append(f"Geo: {self.geo_targeting}")
        if self.device_targeting:
            parts.append(f"Device: {self.device_targeting}")
        if self.audience_targeting:
            parts.append(f"Audience: {self.audience_targeting}")
        if self.targeting_rules:
            parts.extend(rule.display_label for rule in self.targeting_rules[:3])
        return " | ".join(parts) if parts else "Open targeting"
