from datetime import datetime
from functools import wraps

from flask import flash, g, redirect, session, url_for

from ..models import User, db


def authenticate_user(email, password):
    user = User.query.filter(User.email.ilike(email.strip())).first()
    if not user or not user.check_password(password):
        return None

    user.last_login_at = datetime.utcnow()
    db.session.commit()
    return user


def get_current_user():
    if getattr(g, "user", None):
        return g.user
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not get_current_user():
            flash("Please sign in to access AdFlow Admin Simulator.", "error")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped_view
