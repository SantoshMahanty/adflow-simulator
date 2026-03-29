from datetime import datetime

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
