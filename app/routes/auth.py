from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..services import authenticate_user, get_current_user


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user():
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "error")
        else:
            user = authenticate_user(email, password)
            if user:
                session["user_id"] = user.id
                flash("Welcome back to AdFlow Admin Simulator.", "success")
                return redirect(url_for("dashboard.index"))
            flash("Invalid email or password.", "error")

    return render_template("auth/login.html", page_title="Login")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))
