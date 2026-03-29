from datetime import datetime

from . import TABLE_PREFIX, db


placement_ad_units = db.Table(
    f"{TABLE_PREFIX}placement_ad_units",
    db.Column(
        "placement_id",
        db.Integer,
        db.ForeignKey(f"{TABLE_PREFIX}placements.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "ad_unit_id",
        db.Integer,
        db.ForeignKey(f"{TABLE_PREFIX}ad_units.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Placement(db.Model):
    __tablename__ = f"{TABLE_PREFIX}placements"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    device_type = db.Column(db.String(50), nullable=False)
    placement_format = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    ad_units = db.relationship("AdUnit", secondary=placement_ad_units, back_populates="placements")
