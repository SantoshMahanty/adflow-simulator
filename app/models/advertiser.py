from datetime import datetime

from . import TABLE_PREFIX, db


class Advertiser(db.Model):
    __tablename__ = f"{TABLE_PREFIX}advertisers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    vertical = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="active")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    orders = db.relationship("Order", back_populates="advertiser", cascade="all, delete-orphan")
    line_items = db.relationship("LineItem", back_populates="advertiser")
