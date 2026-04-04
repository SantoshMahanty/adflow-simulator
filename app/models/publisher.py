from datetime import datetime

from . import TABLE_PREFIX, db


class PublisherSite(db.Model):
    __tablename__ = f"{TABLE_PREFIX}publisher_sites"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(120), nullable=False, unique=True)
    domain = db.Column(db.String(255))
    status = db.Column(db.String(50), nullable=False, default="active")
    primary_category = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    ad_units = db.relationship("AdUnit", back_populates="publisher_site")
    ad_requests = db.relationship("AdRequest", back_populates="publisher_site")
