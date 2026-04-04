from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
TABLE_PREFIX = "adflow_"


from .activity import ActivityLog
from .ad_unit import AdUnit
from .advertiser import Advertiser
from .auction import AdRequest, AuctionCandidate, AuctionResult, AuctionSimulation
from .creative import Creative
from .delivery import ClickLog, DeliveryLog, ImpressionLog
from .key_value import KeyValueKey, KeyValueValue, LineItemTargeting
from .line_item import LineItem
from .order import Order
from .placement import Placement, placement_ad_units
from .publisher import PublisherSite
from .troubleshooting import TroubleshootingIssue, TroubleshootingSheetRow
from .user import User

__all__ = [
    "db",
    "TABLE_PREFIX",
    "User",
    "PublisherSite",
    "Advertiser",
    "Order",
    "LineItem",
    "Creative",
    "ImpressionLog",
    "ClickLog",
    "DeliveryLog",
    "AdUnit",
    "Placement",
    "placement_ad_units",
    "KeyValueKey",
    "KeyValueValue",
    "LineItemTargeting",
    "TroubleshootingIssue",
    "TroubleshootingSheetRow",
    "AuctionSimulation",
    "AdRequest",
    "AuctionCandidate",
    "AuctionResult",
    "ActivityLog",
]
