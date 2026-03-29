from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from . import TABLE_PREFIX, db


class User(db.Model):
    __tablename__ = f"{TABLE_PREFIX}users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="admin")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime)

    activity_logs = db.relationship("ActivityLog", back_populates="actor")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
