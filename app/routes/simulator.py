from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.orm import defer

from ..models import AdUnit, AuctionSimulation
from ..services import log_activity, login_required, persist_simulation, run_unified_auction, run_waterfall
from ..services.helpers import parse_int


simulator_bp = Blueprint("simulator", __name__, url_prefix="/simulator")


def build_request_context(form):
    ad_unit = AdUnit.query.get(parse_int(form.get("ad_unit_id"), None))
    request_time = form.get("request_time") or datetime.now().strftime("%Y-%m-%dT%H:%M")
    key_values = {}
    for pair in [item for item in form.get("key_values", "").splitlines() if item.strip()]:
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        key_values[key.strip()] = value.strip()
    if form.get("content_category"):
        key_values.setdefault("content_category", form.get("content_category").strip())
    if form.get("geo"):
        key_values.setdefault("geo", form.get("geo").strip())
    if form.get("device"):
        key_values.setdefault("device", form.get("device").strip())
    if form.get("audience"):
        key_values.setdefault("audience", form.get("audience").strip())
    return {
        "ad_unit_id": ad_unit.id if ad_unit else None,
        "ad_unit_path": ad_unit.path if ad_unit else "",
        "device": form.get("device", "").strip(),
        "geo": form.get("geo", "").strip(),
        "audience": form.get("audience", "").strip(),
        "creative_size": form.get("creative_size", "").strip(),
        "time": request_time,
        "content_category": form.get("content_category", "").strip(),
        "key_values": key_values,
    }


@simulator_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    ad_units = AdUnit.query.order_by(AdUnit.path.asc()).all()
    selected_mode = request.form.get("mode", request.args.get("mode", "Waterfall"))
    result = None
    request_context = None

    if request.method == "POST":
        request_context = build_request_context(request.form)
        if not request_context["ad_unit_id"] or not request_context["creative_size"]:
            flash("Ad unit and creative size are required to run a simulation.", "error")
        else:
            result = run_waterfall(request_context) if selected_mode == "Waterfall" else run_unified_auction(request_context)
            simulation = persist_simulation(selected_mode, request_context, result, request_context["ad_unit_id"])
            log_activity("simulation", simulation.id, "run", f"{selected_mode} simulation #{simulation.id} executed.")
            flash(f"{selected_mode} simulation completed.", "success")

    recent_simulations = (
        AuctionSimulation.query.options(
            defer(AuctionSimulation.request_context),
            defer(AuctionSimulation.evaluation_data),
        )
        .order_by(AuctionSimulation.created_at.desc())
        .limit(8)
        .all()
    )
    return render_template(
        "simulator/index.html",
        page_title="Auction Simulator",
        ad_units=ad_units,
        recent_simulations=recent_simulations,
        selected_mode=selected_mode,
        result=result,
        request_context=request_context,
    )


@simulator_bp.route("/<int:simulation_id>")
@login_required
def detail(simulation_id):
    simulation = AuctionSimulation.query.get_or_404(simulation_id)
    return render_template(
        "simulator/detail.html",
        page_title=f"Simulation #{simulation.id}",
        simulation=simulation,
        result=simulation.evaluation_data,
    )
