from datetime import datetime

from . import TABLE_PREFIX, db


class KeyValueKey(db.Model):
    __tablename__ = f"{TABLE_PREFIX}key_value_keys"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    values = db.relationship("KeyValueValue", back_populates="key", cascade="all, delete-orphan")


class KeyValueValue(db.Model):
    __tablename__ = f"{TABLE_PREFIX}key_value_values"

    id = db.Column(db.Integer, primary_key=True)
    key_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{TABLE_PREFIX}key_value_keys.id", ondelete="CASCADE"),
        nullable=False,
    )
    value = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    key = db.relationship("KeyValueKey", back_populates="values")
    targeting_rules = db.relationship("LineItemTargeting", back_populates="key_value_value")

    __table_args__ = (db.UniqueConstraint("key_id", "value", name="uq_adflow_key_value_pair"),)


class LineItemTargeting(db.Model):
    __tablename__ = f"{TABLE_PREFIX}line_item_targeting"

    id = db.Column(db.Integer, primary_key=True)
    line_item_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{TABLE_PREFIX}line_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_type = db.Column(db.String(50), nullable=False)
    operator = db.Column(db.String(20), nullable=False, default="equals")
    target_value = db.Column(db.String(255))
    key_value_value_id = db.Column(db.Integer, db.ForeignKey(f"{TABLE_PREFIX}key_value_values.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    line_item = db.relationship("LineItem", back_populates="targeting_rules")
    key_value_value = db.relationship("KeyValueValue", back_populates="targeting_rules")

    @property
    def display_label(self):
        if self.target_type == "key_value" and self.key_value_value:
            return f"{self.key_value_value.key.name}={self.key_value_value.value}"
        return f"{self.target_type}: {self.target_value}"
