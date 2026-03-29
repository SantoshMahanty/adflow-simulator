from datetime import datetime

from . import TABLE_PREFIX, db


class AdUnit(db.Model):
    __tablename__ = f"{TABLE_PREFIX}ad_units"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    path = db.Column(db.String(255), nullable=False, unique=True)
    size_support = db.Column(db.String(120), nullable=False)
    environment = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    parent_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}ad_units.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    parent = db.relationship(
        "AdUnit",
        remote_side=[id],
        backref=db.backref("children", lazy="joined", passive_deletes=True),
    )
    placements = db.relationship(
        "Placement",
        secondary=f"{TABLE_PREFIX}placement_ad_units",
        back_populates="ad_units",
    )
