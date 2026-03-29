from datetime import datetime

from . import TABLE_PREFIX, db


class Order(db.Model):
    __tablename__ = f"{TABLE_PREFIX}orders"

    id = db.Column(db.Integer, primary_key=True)
    advertiser_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{TABLE_PREFIX}advertisers.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(150), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="active")
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    advertiser = db.relationship("Advertiser", back_populates="orders")
    line_items = db.relationship("LineItem", back_populates="order", cascade="all, delete-orphan")
