from flask import Flask, g, render_template, session

from config import DevelopmentConfig

from .models import User, db
from .routes.ad_units import ad_units_bp
from .routes.advertisers import advertisers_bp
from .routes.auth import auth_bp
from .routes.creatives import creatives_bp
from .routes.dashboard import dashboard_bp
from .routes.key_values import key_values_bp
from .routes.line_items import line_items_bp
from .routes.orders import orders_bp
from .routes.placements import placements_bp
from .routes.reports import reports_bp
from .routes.simulator import simulator_bp
from .routes.troubleshooting import troubleshooting_bp


def create_app(config_object=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)

    register_blueprints(app)
    register_context(app)
    register_error_handlers(app)

    @app.before_request
    def load_current_user():
        user_id = session.get("user_id")
        g.user = db.session.get(User, user_id) if user_id else None

    @app.cli.command("init-db")
    def init_db_command():
        with app.app_context():
            db.create_all()
            print("Database tables created.")

    return app


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(advertisers_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(line_items_bp)
    app.register_blueprint(creatives_bp)
    app.register_blueprint(ad_units_bp)
    app.register_blueprint(placements_bp)
    app.register_blueprint(key_values_bp)
    app.register_blueprint(simulator_bp)
    app.register_blueprint(troubleshooting_bp)
    app.register_blueprint(reports_bp)


def register_context(app):
    @app.context_processor
    def inject_navigation():
        sidebar_nav = [
            {"label": "Dashboard", "endpoint": "dashboard.index"},
            {
                "label": "Inventory",
                "children": [
                    {"label": "Advertisers", "endpoint": "advertisers.index"},
                    {"label": "Orders", "endpoint": "orders.index"},
                    {"label": "Line Items", "endpoint": "line_items.index"},
                    {"label": "Creatives", "endpoint": "creatives.index"},
                    {"label": "Ad Units", "endpoint": "ad_units.index"},
                    {"label": "Placements", "endpoint": "placements.index"},
                ],
            },
            {"label": "Targeting", "children": [{"label": "Key Values", "endpoint": "key_values.index"}]},
            {"label": "Simulators", "children": [{"label": "Auction", "endpoint": "simulator.index"}]},
            {
                "label": "Troubleshooting",
                "children": [
                    {"label": "Issues Library", "endpoint": "troubleshooting.issues"},
                    {"label": "Troubleshooting Sheet", "endpoint": "troubleshooting.sheet"},
                ],
            },
            {"label": "Reports", "endpoint": "reports.index"},
            {"label": "Settings", "endpoint": "dashboard.settings"},
        ]
        return {"sidebar_nav": sidebar_nav}


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html", page_title="Page Not Found"), 404

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template("errors/500.html", page_title="Server Error"), 500
