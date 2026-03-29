from datetime import datetime

from . import TABLE_PREFIX, db


class Creative(db.Model):
    __tablename__ = f"{TABLE_PREFIX}creatives"

    id = db.Column(db.Integer, primary_key=True)
    line_item_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{TABLE_PREFIX}line_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(150), nullable=False)
    creative_format = db.Column(db.String(50), nullable=False)
    size = db.Column(db.String(30), nullable=False)
    destination_url = db.Column(db.String(255))
    approval_status = db.Column(db.String(50), nullable=False, default="pending")
    tag_snippet = db.Column(db.Text)
    preview_text = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    line_item = db.relationship("LineItem", back_populates="creatives")
