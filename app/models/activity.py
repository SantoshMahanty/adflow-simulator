from datetime import datetime

from . import TABLE_PREFIX, db


class ActivityLog(db.Model):
    __tablename__ = f"{TABLE_PREFIX}activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.Integer)
    action = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    details = db.Column(db.JSON)
    actor_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    actor = db.relationship("User", back_populates="activity_logs")
