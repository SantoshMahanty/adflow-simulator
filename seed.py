from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal
from random import Random
import re

from app import create_app
from app.models import (
    ActivityLog,
    AdUnit,
    Advertiser,
    AuctionSimulation,
    Creative,
    KeyValueKey,
    KeyValueValue,
    LineItem,
    LineItemTargeting,
    Order,
    Placement,
    TroubleshootingIssue,
    TroubleshootingSheetRow,
    User,
    db,
)
from app.services.simulation import run_unified_auction, run_waterfall


RNG = Random(360)
TODAY = date.today()
NOW = datetime.now()

TARGET_COUNTS = {
    "advertisers": 50,
    "orders": 200,
    "line_items": 800,
    "creatives": 1200,
    "ad_units": 94,
    "placements": 50,
    "targeting_keys": 14,
    "issue_templates": 32,
    "sheet_rows": 120,
    "simulations": 150,
    "activity_logs": 400,
}

ADVERTISER_CATALOG = [
    ("Nike India Performance", "Sportswear"),
    ("Samsung Ads India", "Consumer Electronics"),
    ("PhonePe Growth Marketing", "Fintech"),
    ("Tata Neu Marketplace", "Commerce"),
    ("Amazon Prime Video India", "Streaming"),
    ("Myntra Fashion Commerce", "Fashion Retail"),
    ("Flipkart Electronics Fest", "Marketplace"),
    ("Airtel Digital Services", "Telecom"),
    ("HDFC Bank Cards", "Banking"),
    ("ICICI Prudential Life", "Insurance"),
    ("Maruti Suzuki Nexa", "Automotive"),
    ("Hyundai India Motors", "Automotive"),
    ("Mahindra Auto", "Automotive"),
    ("MakeMyTrip Domestic", "Travel"),
    ("IndiGo Airlines", "Travel"),
    ("Zomato Dining", "Food Delivery"),
    ("Swiggy Instamart", "Quick Commerce"),
    ("BigBasket Retail Media", "Grocery"),
    ("AJIO Fashion", "Fashion Retail"),
    ("Nykaa Beauty", "Beauty"),
    ("CRED Rewards", "Fintech"),
    ("Groww Investing", "Fintech"),
    ("Zerodha Varsity", "Investing"),
    ("BYJUS Learning", "EdTech"),
    ("Unacademy Plus", "EdTech"),
    ("Dream11 Fantasy Sports", "Gaming"),
    ("MPL Gaming", "Gaming"),
    ("Sony LIV Premium", "Streaming"),
    ("Disney Hotstar India", "Streaming"),
    ("JioCinema Sports", "Streaming"),
    ("Ola Electric", "Mobility"),
    ("Ather Energy", "Mobility"),
    ("Lenovo India Commercial", "Technology"),
    ("Dell Technologies SMB", "Technology"),
    ("HP OmniBook India", "Technology"),
    ("Vivo Smartphones", "Consumer Electronics"),
    ("Oppo Reno Series", "Consumer Electronics"),
    ("OnePlus India", "Consumer Electronics"),
    ("Xiaomi Redmi India", "Consumer Electronics"),
    ("Google Play India", "App Marketplace"),
    ("Meta Quest India", "Gaming Hardware"),
    ("Paytm Wallet", "Fintech"),
    ("Axis Bank Burgundy", "Banking"),
    ("Kotak 811", "Banking"),
    ("LIC India", "Insurance"),
    ("Policybazaar", "Insurance"),
    ("Star Health Insurance", "Insurance"),
    ("Tata 1mg", "Healthcare"),
    ("Apollo 247", "Healthcare"),
    ("Blinkit Quick Commerce", "Quick Commerce"),
]

KEY_VALUE_CATALOG = {
    "geo": [
        "delhi_ncr",
        "mumbai",
        "bengaluru",
        "hyderabad",
        "chennai",
        "kolkata",
        "pune",
        "ahmedabad",
        "jaipur",
        "lucknow",
    ],
    "geo_country": ["in", "ae", "sg"],
    "dma": ["delhi", "mumbai", "bengaluru", "hyderabad", "chennai", "kolkata"],
    "device": ["desktop", "mobile", "tablet", "ctv"],
    "os": ["android", "ios", "windows", "macos", "roku", "fire_tv", "tvos"],
    "browser": ["chrome", "safari", "firefox", "edge", "samsung_internet"],
    "connection_type": ["wifi", "4g", "5g", "broadband"],
    "audience": [
        "sports_fans",
        "movie_lovers",
        "finance_traders",
        "shopping_intenders",
        "gaming_enthusiasts",
        "auto_buyers",
        "frequent_travelers",
        "young_parents",
        "streaming_bingers",
        "app_installers",
    ],
    "content_category": [
        "sports",
        "news",
        "finance",
        "entertainment",
        "technology",
        "shopping",
        "auto",
        "travel",
        "food",
        "kids",
    ],
    "app_bundle": [
        "com.fitlife.mobile",
        "com.newswire.daily",
        "com.shopkart.consumer",
        "com.gamearena.max",
    ],
    "inventory_tier": ["premium", "standard", "remnant"],
    "language": ["en", "hi", "ta", "te", "bn"],
    "supply_channel": ["web", "app", "ctv"],
    "deal_type": ["open_auction", "pmp", "preferred", "programmatic_guaranteed"],
}

WEB_INVENTORY = [
    {
        "publisher": "sportsdaily",
        "category": "sports",
        "sections": [
            ("homepage", [("top_leaderboard", "728x90,970x250", "display", "desktop", "premium"), ("mid_rect", "300x250,336x280", "display", "desktop", "standard")]),
            ("article", [("in_article_native", "300x250,336x280", "native", "mobile", "standard"), ("sticky_sidebar", "300x600", "display", "desktop", "premium")]),
        ],
    },
    {
        "publisher": "newswire",
        "category": "news",
        "sections": [
            ("homepage", [("masthead", "970x250,728x90", "display", "desktop", "premium"), ("mobile_banner", "320x50,320x100", "display", "mobile", "standard")]),
            ("article", [("mid_rect", "300x250", "display", "mobile", "standard"), ("below_article_video", "640x360", "video", "desktop", "premium")]),
        ],
    },
    {
        "publisher": "financepulse",
        "category": "finance",
        "sections": [
            ("markets", [("top_banner", "728x90", "display", "desktop", "premium"), ("infeed_native", "300x250", "native", "mobile", "standard")]),
            ("article", [("mid_rect", "300x250,336x280", "display", "desktop", "standard"), ("adhesion", "320x50", "display", "mobile", "remnant")]),
        ],
    },
    {
        "publisher": "autoarena",
        "category": "auto",
        "sections": [
            ("homepage", [("hero_billboard", "970x250", "display", "desktop", "premium"), ("mobile_banner", "320x50", "display", "mobile", "standard")]),
            ("reviews", [("mid_rect", "300x250", "display", "desktop", "standard"), ("video_preroll", "640x360", "video", "desktop", "premium")]),
        ],
    },
    {
        "publisher": "foodloop",
        "category": "food",
        "sections": [
            ("homepage", [("leaderboard", "728x90", "display", "desktop", "standard"), ("mobile_banner", "320x50", "display", "mobile", "standard")]),
            ("recipes", [("in_article_native", "300x250", "native", "mobile", "standard"), ("sidebar_rect", "300x600", "display", "desktop", "premium")]),
        ],
    },
]

APP_INVENTORY = [
    {
        "app": "fitlife",
        "bundle": "com.fitlife.mobile",
        "category": "sports",
        "screens": [
            ("home", [("banner_top", "320x50,320x100", "display", "mobile", "standard"), ("interstitial_break", "320x480", "display", "mobile", "premium")]),
            ("article", [("feed_native", "300x250", "native", "mobile", "standard"), ("rewarded_video", "640x360", "video", "mobile", "premium")]),
        ],
    },
    {
        "app": "newswire",
        "bundle": "com.newswire.daily",
        "category": "news",
        "screens": [
            ("home", [("banner_top", "320x50", "display", "mobile", "standard"), ("interstitial_break", "320x480", "display", "mobile", "premium")]),
            ("article", [("feed_native", "300x250", "native", "mobile", "standard"), ("video_slot", "640x360", "video", "mobile", "premium")]),
        ],
    },
    {
        "app": "shopkart",
        "bundle": "com.shopkart.consumer",
        "category": "shopping",
        "screens": [
            ("home", [("banner_top", "320x50", "display", "mobile", "standard"), ("interstitial_break", "320x480", "display", "mobile", "premium")]),
            ("product", [("feed_native", "300x250", "native", "mobile", "standard"), ("video_slot", "640x360", "video", "mobile", "premium")]),
        ],
    },
    {
        "app": "gamearena",
        "bundle": "com.gamearena.max",
        "category": "gaming",
        "screens": [
            ("lobby", [("banner_top", "320x50", "display", "mobile", "standard"), ("interstitial_break", "320x480", "display", "mobile", "premium")]),
            ("match", [("rewarded_native", "300x250", "native", "mobile", "standard"), ("rewarded_video", "640x360", "video", "mobile", "premium")]),
        ],
    },
]

CTV_INVENTORY = [
    {
        "network": "streamplus",
        "category": "entertainment",
        "channels": [
            ("premium", [("preroll_hd", "1920x1080", "video", "ctv", "premium"), ("midroll_hd", "1920x1080", "video", "ctv", "premium")]),
            ("movies", [("preroll_hd", "1920x1080", "video", "ctv", "premium"), ("midroll_hd", "1920x1080", "video", "ctv", "standard")]),
        ],
    },
    {
        "network": "sportstv",
        "category": "sports",
        "channels": [
            ("live", [("preroll_hd", "1920x1080", "video", "ctv", "premium"), ("midroll_hd", "1920x1080", "video", "ctv", "premium")]),
            ("replay", [("preroll_hd", "1920x1080", "video", "ctv", "premium"), ("midroll_hd", "1920x1080", "video", "ctv", "standard")]),
        ],
    },
    {
        "network": "moviemax",
        "category": "entertainment",
        "channels": [
            ("premiere", [("preroll_hd", "1920x1080", "video", "ctv", "premium"), ("midroll_hd", "1920x1080", "video", "ctv", "premium")]),
            ("classics", [("preroll_hd", "1920x1080", "video", "ctv", "standard"), ("midroll_hd", "1920x1080", "video", "ctv", "standard")]),
        ],
    },
    {
        "network": "kidszone",
        "category": "kids",
        "channels": [
            ("cartoons", [("preroll_hd", "1920x1080", "video", "ctv", "premium"), ("midroll_hd", "1920x1080", "video", "ctv", "standard")]),
            ("family", [("preroll_hd", "1920x1080", "video", "ctv", "premium"), ("midroll_hd", "1920x1080", "video", "ctv", "standard")]),
        ],
    },
]

ISSUE_TEMPLATES = [
    ("No impressions", "Line item receives zero impressions after launch.", "Paused status, no eligible creative, or ad unit mismatch.", "Check line item status, creative approval, and ad unit targeting.", "Activate the line item, attach an approved creative, and confirm request path.", "high", "Delivery", "Line Items"),
    ("Low delivery", "Delivery is materially below plan.", "Targeting is narrow or CPM is uncompetitive.", "Review pacing, simulator output, and targeting breadth.", "Loosen targeting or improve CPM competitiveness.", "medium", "Delivery", "Reports"),
    ("Creative rejected", "Creative approval failed in QA.", "Policy or tag validation issue.", "Inspect creative approval history and audit notes.", "Update the creative asset or third-party tag and resubmit.", "high", "Creative QA", "Creatives"),
    ("Size mismatch", "Creative dimensions do not match the requested slot.", "Wrong size uploaded or line item size is incorrect.", "Compare ad unit size support against creative size.", "Upload matching sizes and align the line item size.", "medium", "Creative QA", "Creatives"),
    ("Geo mismatch", "Targeted geography does not match the request.", "City, region, or DMA targeting is too narrow.", "Inspect geo fields on the line item and request context.", "Correct the geo targeting or request metadata.", "medium", "Targeting", "Line Items"),
    ("Key-value mismatch", "Required page or app metadata is missing.", "Incorrect key-value setup or missing page annotation.", "Review key-values, simulator input, and publisher implementation.", "Update the key-values or relax the requirement.", "medium", "Targeting", "Key Values"),
    ("Frequency cap reached", "Eligible users stop seeing the campaign after multiple exposures.", "Frequency cap is too restrictive.", "Check frequency cap settings and user-level delivery controls.", "Increase the cap or rebalance audience strategy.", "low", "Delivery", "Line Items"),
    ("Line item paused", "Serving has been manually or operationally paused.", "Ops intervention or campaign hold.", "Check current line item state and notes.", "Resume the line item if campaign is approved to serve.", "high", "Operations", "Line Items"),
    ("Ad unit tag missing", "No ad requests are reaching the server.", "Publisher tag is missing or broken.", "Validate implementation on the publisher side.", "Deploy or repair the ad tag.", "high", "Implementation", "Ad Units"),
    ("Lost in auction", "Candidate was eligible but lost the impression.", "Another line item cleared with a stronger effective CPM.", "Review the unified auction results and competitive set.", "Increase bid value or adjust prioritization.", "medium", "Auction", "Simulator"),
    ("Upcoming launch not yet live", "Campaign has not started serving yet.", "Flight dates begin in the future.", "Compare current date with line item and order flight dates.", "Wait for the start date or move the flight forward.", "low", "Scheduling", "Orders"),
    ("Expired campaign", "Campaign stopped serving after flight end.", "End date has passed.", "Validate order and line item end dates.", "Extend the flight or clone a new line item.", "medium", "Scheduling", "Orders"),
    ("Budget exhausted", "Campaign stopped pacing due to budget depletion.", "Spend cap or impression goal was reached.", "Review pacing dashboard and goal consumption.", "Increase budget or rotate in a backup line item.", "medium", "Budget", "Reports"),
    ("Invalid click-through URL", "Creative cannot pass validation for click destination.", "Malformed or blocked landing page URL.", "Inspect creative destination URLs and QA logs.", "Correct the URL and re-approve the creative.", "medium", "Creative QA", "Creatives"),
    ("VAST response error", "Video ad response is failing VAST validation.", "Broken XML or unavailable media file.", "Validate VAST URL and playback response.", "Repair the VAST tag or replace the asset.", "high", "Video", "Creatives"),
    ("Ad unit not mapped", "Targeted ad unit is not attached to the line item setup.", "Missing ad unit or placement targeting rule.", "Inspect ad unit targeting rules and placement links.", "Add the correct ad unit path to the line item.", "high", "Targeting", "Ad Units"),
    ("Device mismatch", "Request device does not match the configured target.", "Device targeting is too narrow.", "Compare request device against device targeting.", "Adjust the device targeting or request metadata.", "medium", "Targeting", "Line Items"),
    ("Audience mismatch", "Audience segment targeting is not satisfied.", "Unavailable or incorrect segment mapping.", "Check audience keys and segment ingestion.", "Fix segment mapping or loosen the audience filter.", "medium", "Targeting", "Line Items"),
    ("Browser mismatch", "Browser targeting blocks otherwise valid requests.", "Overly specific browser filter.", "Inspect browser key-values and request browser.", "Broaden browser targeting if not required.", "low", "Targeting", "Key Values"),
    ("App bundle mismatch", "In-app request is coming from the wrong app bundle.", "Line item targets a different bundle.", "Check app bundle key-values and SDK metadata.", "Correct the app bundle rule or publisher metadata.", "medium", "App Delivery", "Key Values"),
    ("CTV SSAI integration gap", "Server-side ad insertion metadata is missing.", "Improper SSAI integration or stream annotation.", "Review SSAI request fields and device metadata.", "Fix SSAI mapping before scaling delivery.", "high", "CTV", "Simulator"),
    ("Latency timeout", "Ad response is timing out before render.", "Slow third-party tag or network latency.", "Check response timing and third-party tag waterfall.", "Replace or optimize the slow creative.", "medium", "Performance", "Creatives"),
    ("Blocked by brand safety", "Brand safety rules prevented serving.", "Sensitive content or exclusion rule matched.", "Inspect content category exclusions and brand safety settings.", "Update content rules or move campaign to safer inventory.", "medium", "Safety", "Line Items"),
    ("Underbid in PMP", "Preferred marketplace candidate is losing price competition.", "Bid CPM or floor strategy is too low.", "Review PMP clearing prices and effective CPM.", "Increase PMP CPM or rebalance deal mix.", "medium", "Auction", "Simulator"),
    ("Missing consent string", "Consent metadata is absent for regulated traffic.", "CMP integration gap.", "Verify privacy signals in the request.", "Fix CMP implementation or suppress delivery where required.", "high", "Privacy", "Ad Units"),
    ("Category exclusion hit", "Content category exclusion prevents serving.", "Exclusion list overlaps with current page content.", "Compare page content category to exclusion rules.", "Refine the exclusion list.", "medium", "Safety", "Key Values"),
    ("Viewability pacing issue", "Campaign underserves on high-viewability inventory.", "Viewability filters are too strict.", "Inspect inventory quality and pacing filters.", "Expand supply or soften viewability requirements.", "medium", "Delivery", "Reports"),
    ("Impression cap threshold", "Impression goal is nearly exhausted.", "Campaign is close to completion.", "Check delivered versus goal.", "Increase goal or prepare a replacement line item.", "low", "Budget", "Line Items"),
    ("Broken macro in tag", "Dynamic macro expansion is failing in the third-party tag.", "Malformed macro or unsupported token.", "Validate rendered tag output in QA.", "Repair the macro string and retest.", "high", "Implementation", "Creatives"),
    ("Creative inactive", "Creative exists but is not active for serving.", "Manual deactivation or sync issue.", "Review creative active flag and latest changes.", "Reactivate the creative or upload a replacement.", "medium", "Creative QA", "Creatives"),
    ("Publisher blocklist match", "Publisher or app is blocklisted for the campaign.", "Blocklist overrides supply eligibility.", "Review blocklists and ad unit ancestry.", "Remove the block or map the campaign to allowed inventory.", "medium", "Targeting", "Ad Units"),
    ("Deal ID mismatch", "PMP request deal ID does not match the configured line item.", "Incorrect deal metadata.", "Compare request deal_id against line item setup.", "Fix the deal ID mapping in request generation.", "medium", "Programmatic", "Simulator"),
]

ACTIVE_SCENARIO_PACKS = [
    ["healthy", "low_delivery", "geo_sensitive", "lost_in_auction"],
    ["healthy", "no_approved_creative", "size_mismatch", "paused"],
    ["healthy", "key_value_sensitive", "low_delivery", "draft"],
    ["healthy", "healthy", "geo_sensitive", "lost_in_auction"],
]

SCENARIO_TO_ISSUE = {
    "healthy": "Low delivery",
    "low_delivery": "Low delivery",
    "paused": "Line item paused",
    "upcoming": "Upcoming launch not yet live",
    "draft": "Creative inactive",
    "expired": "Expired campaign",
    "no_approved_creative": "No impressions",
    "size_mismatch": "Size mismatch",
    "geo_sensitive": "Geo mismatch",
    "key_value_sensitive": "Key-value mismatch",
    "lost_in_auction": "Lost in auction",
}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def title_from_slug(value: str) -> str:
    return value.replace("_", " ").title()


def random_datetime(days_back: int = 180) -> datetime:
    return NOW - timedelta(
        days=RNG.randint(0, days_back),
        hours=RNG.randint(0, 23),
        minutes=RNG.randint(0, 59),
        seconds=RNG.randint(0, 59),
    )


def created_from_range(start_date: date, end_date: date) -> datetime:
    span = max((end_date - start_date).days, 1)
    offset = RNG.randint(0, span)
    return datetime.combine(start_date + timedelta(days=offset), datetime.min.time())


def quantize_cpm(value: float) -> Decimal:
    return Decimal(f"{value:.2f}")


def brand_code(name: str) -> str:
    words = [part for part in re.split(r"[^A-Za-z0-9]+", name) if part][:3]
    return "".join(word[:3].upper() for word in words)[:10]


def status_dates(status: str) -> tuple[date, date]:
    if status == "active":
        start = TODAY - timedelta(days=RNG.randint(5, 60))
        end = TODAY + timedelta(days=RNG.randint(10, 70))
    elif status == "paused":
        start = TODAY - timedelta(days=RNG.randint(10, 45))
        end = TODAY + timedelta(days=RNG.randint(5, 40))
    elif status == "upcoming":
        start = TODAY + timedelta(days=RNG.randint(3, 45))
        end = start + timedelta(days=RNG.randint(14, 60))
    elif status == "expired":
        end = TODAY - timedelta(days=RNG.randint(2, 45))
        start = end - timedelta(days=RNG.randint(20, 90))
    else:
        start = TODAY + timedelta(days=RNG.randint(7, 30))
        end = start + timedelta(days=RNG.randint(14, 45))
    return start, end


def line_item_status_for_scenario(scenario: str) -> str:
    return {
        "healthy": "active",
        "low_delivery": "active",
        "paused": "paused",
        "upcoming": "upcoming",
        "draft": "draft",
        "expired": "expired",
        "no_approved_creative": "active",
        "size_mismatch": "active",
        "geo_sensitive": "active",
        "key_value_sensitive": "active",
        "lost_in_auction": "active",
    }[scenario]


def line_item_dates(order_start: date, order_end: date, scenario: str) -> tuple[date, date]:
    if scenario in {"upcoming", "draft"}:
        start = max(order_start, TODAY + timedelta(days=RNG.randint(1, 20)))
        end = min(order_end, start + timedelta(days=RNG.randint(14, 45)))
    elif scenario == "expired":
        end = min(order_end, TODAY - timedelta(days=RNG.randint(1, 14)))
        start = max(order_start, end - timedelta(days=RNG.randint(14, 45)))
    else:
        start = max(order_start, TODAY - timedelta(days=RNG.randint(3, 30)))
        end = min(order_end, TODAY + timedelta(days=RNG.randint(7, 45)))
        if end <= start:
            end = start + timedelta(days=14)
    return start, end


def choose_order_environment(vertical: str, position: int) -> str:
    if position == 2:
        return RNG.choice(["web", "app"])
    preferred = {
        "Streaming": ["ctv", "web"],
        "Gaming": ["app", "web"],
        "App Marketplace": ["app", "web"],
        "Quick Commerce": ["app", "web"],
        "Travel": ["web", "app"],
        "Banking": ["web", "app"],
        "Insurance": ["web", "app"],
        "Technology": ["web", "ctv"],
        "Consumer Electronics": ["ctv", "web", "app"],
    }
    return RNG.choice(preferred.get(vertical, ["web", "app", "ctv"]))


def choose_order_status(advertiser_index: int, position: int) -> str:
    if position == 0:
        return "active"
    if position == 1:
        return "paused" if advertiser_index % 4 == 0 else "active"
    if position == 2:
        return "upcoming"
    return "expired"


def objective_pool(environment: str) -> list[str]:
    return {
        "web": ["Brand Reach", "Homepage Takeover", "Retail Burst", "Content Sponsorship", "Video Reach"],
        "app": ["App Installs", "Retention Push", "Offer Reminder", "Cross-Sell Burst", "Rewarded Reach"],
        "ctv": ["Big Screen Reach", "Household Reach", "Premiere Sponsorship", "Sports Preroll Reach", "Midroll Scale"],
    }[environment]


def line_item_type_ladder(environment: str) -> list[str]:
    return {
        "web": ["Sponsorship", "Standard", "Preferred Deal", "Network"],
        "app": ["Standard", "Preferred Deal", "AdX/Price Priority", "Network"],
        "ctv": ["Programmatic Guaranteed", "Preferred Deal", "Standard", "Network"],
    }[environment]


def priority_for_type(line_item_type: str) -> int:
    base = {
        "Sponsorship": 1,
        "Preferred Deal": 2,
        "Programmatic Guaranteed": 3,
        "Standard": 4,
        "AdX/Price Priority": 6,
        "Network": 8,
        "House": 12,
    }[line_item_type]
    return base + RNG.randint(0, 1)


def creative_format_for_leaf(environment: str, slot_format: str) -> str:
    if environment == "ctv":
        return "ctv"
    if slot_format == "video":
        return "video"
    if slot_format == "native":
        return "native"
    return "display"


def deal_type_for_line_item(line_item_type: str) -> str:
    return {
        "Sponsorship": "preferred",
        "Preferred Deal": "preferred",
        "Programmatic Guaranteed": "programmatic_guaranteed",
        "Standard": "pmp",
        "AdX/Price Priority": "open_auction",
        "Network": "open_auction",
        "House": "open_auction",
    }.get(line_item_type, "open_auction")


def choose_browser(device: str) -> str:
    if device == "mobile":
        return RNG.choice(["chrome", "safari", "samsung_internet"])
    if device == "desktop":
        return RNG.choice(["chrome", "firefox", "edge", "safari"])
    return "chrome"


def choose_os(environment: str) -> str:
    if environment == "app":
        return RNG.choice(["android", "ios"])
    if environment == "ctv":
        return RNG.choice(["roku", "fire_tv", "tvos"])
    return RNG.choice(["windows", "macos"])


def goal_for_environment(environment: str, line_item_type: str) -> int:
    ranges = {
        "web": (250_000, 2_500_000),
        "app": (180_000, 1_800_000),
        "ctv": (80_000, 650_000),
    }
    low, high = ranges[environment]
    multiplier = {
        "Sponsorship": 1.4,
        "Programmatic Guaranteed": 1.2,
        "Preferred Deal": 1.0,
        "Standard": 0.9,
        "AdX/Price Priority": 0.7,
        "Network": 0.55,
        "House": 0.35,
    }.get(line_item_type, 0.8)
    return int(RNG.randint(low, high) * multiplier)


def delivered_for_scenario(goal: int, scenario: str) -> int:
    ranges = {
        "healthy": (0.48, 0.92),
        "low_delivery": (0.06, 0.34),
        "paused": (0.10, 0.58),
        "upcoming": (0.00, 0.00),
        "draft": (0.00, 0.02),
        "expired": (0.42, 1.05),
        "no_approved_creative": (0.00, 0.08),
        "size_mismatch": (0.01, 0.12),
        "geo_sensitive": (0.12, 0.55),
        "key_value_sensitive": (0.08, 0.40),
        "lost_in_auction": (0.08, 0.36),
    }
    low, high = ranges[scenario]
    return int(goal * RNG.uniform(low, high))


def cpm_for_line_item(environment: str, line_item_type: str, scenario: str) -> Decimal:
    base = {"web": 4.2, "app": 6.1, "ctv": 16.8}[environment]
    type_bonus = {
        "Sponsorship": 8.5,
        "Preferred Deal": 5.0,
        "Programmatic Guaranteed": 7.5,
        "Standard": 2.4,
        "AdX/Price Priority": 1.2,
        "Network": 0.4,
        "House": -2.8,
    }.get(line_item_type, 1.0)
    scenario_modifier = {
        "low_delivery": -0.8,
        "lost_in_auction": -2.6,
        "paused": -0.4,
        "expired": -0.2,
        "no_approved_creative": 0.0,
        "size_mismatch": 0.2,
    }.get(scenario, 0.0)
    noise = RNG.uniform(-1.1, 1.8)
    return quantize_cpm(max(base + type_bonus + scenario_modifier + noise, 0.4))


def build_order_name(advertiser_name: str, environment: str, objective: str, status: str, sequence: int) -> str:
    market = RNG.choice(["India National", "Tier 1 Cities", "Delhi NCR", "South India", "Metro Scale"])
    return f"{brand_code(advertiser_name)} | FY26-Q{((TODAY.month - 1) // 3) + 1} | {environment.upper()} | {objective} | {market} | {status.title()} | {sequence:02d}"


def build_line_item_name(order_name: str, theme: str, line_item_type: str, size: str, sequence: int) -> str:
    order_code = order_name.split("|")[0].strip()
    return f"{order_code} | {theme} | {line_item_type} | {size} | LI-{sequence:02d}"


def build_creative_name(advertiser_name: str, creative_format: str, size: str, sequence: int) -> str:
    return f"{brand_code(advertiser_name)} | {creative_format.upper()} | {size} | CR-{sequence:02d}"


def note_for_line_item(environment: str, objective: str, scenario: str, category: str, geo_targeting: str) -> str:
    fragments = {
        "healthy": "Primary line item serving against live inventory.",
        "low_delivery": "Observed pacing pressure against current goals.",
        "paused": "Temporarily held by ops while campaign settings are reviewed.",
        "upcoming": "Launch scheduled but not yet active.",
        "draft": "Draft setup pending final approval.",
        "expired": "Legacy setup retained for historical troubleshooting.",
        "no_approved_creative": "Creative QA is holding this line item from serving.",
        "size_mismatch": "Creative package requires size remediation before scale.",
        "geo_sensitive": "Geo-restricted layer for a focused regional audience.",
        "key_value_sensitive": "Strict metadata gating applied for segment precision.",
        "lost_in_auction": "Competing against stronger effective CPM candidates.",
    }
    return f"{objective} campaign across {category} inventory in {geo_targeting}. {fragments[scenario]} Environment: {environment.upper()}."


def reset_schema() -> None:
    db.drop_all()
    db.create_all()


def create_admin_user() -> User:
    admin = User(
        name="AdFlow Admin",
        email="admin@adflow.local",
        role="admin",
        created_at=NOW - timedelta(days=120),
    )
    admin.set_password("Admin@123")
    db.session.add(admin)
    db.session.flush()
    return admin


def create_key_values() -> dict[str, dict[str, KeyValueValue]]:
    lookup: dict[str, dict[str, KeyValueValue]] = {}
    for key_name, values in KEY_VALUE_CATALOG.items():
        key = KeyValueKey(
            name=key_name,
            description=f"{title_from_slug(key_name)} targeting key",
            created_at=random_datetime(240),
        )
        db.session.add(key)
        db.session.flush()
        lookup[key_name] = {}
        for value in values:
            row = KeyValueValue(
                key=key,
                value=value,
                description=f"{key_name}={value}",
                created_at=random_datetime(240),
            )
            db.session.add(row)
            lookup[key_name][value] = row
    db.session.flush()
    return lookup


def add_ad_unit(name: str, path: str, size_support: str, environment: str, parent: AdUnit | None) -> AdUnit:
    ad_unit = AdUnit(
        name=name,
        path=path,
        size_support=size_support,
        environment=environment,
        is_active=True,
        parent=parent,
        created_at=random_datetime(200),
    )
    db.session.add(ad_unit)
    db.session.flush()
    return ad_unit


def create_ad_units() -> list[dict]:
    leaf_units: list[dict] = []

    web_root = add_ad_unit("web", "/web", "728x90,970x250,300x250,300x600,320x50,640x360", "web", None)
    for site in WEB_INVENTORY:
        site_node = add_ad_unit(site["publisher"], f"/web/{site['publisher']}", "728x90,300x250,300x600,970x250", "web", web_root)
        for section_name, slots in site["sections"]:
            section_node = add_ad_unit(section_name, f"{site_node.path}/{section_name}", "728x90,300x250,300x600,970x250,320x50,640x360", "web", site_node)
            for slot_name, size_support, slot_format, device, tier in slots:
                leaf = add_ad_unit(slot_name, f"{section_node.path}/{slot_name}", size_support, "web", section_node)
                leaf_units.append(
                    {
                        "ad_unit": leaf,
                        "environment": "web",
                        "sizes": [item.strip() for item in size_support.split(",")],
                        "slot_format": slot_format,
                        "device": device,
                        "inventory_tier": tier,
                        "content_category": site["category"],
                        "label": site["publisher"],
                    }
                )

    app_root = add_ad_unit("app", "/app", "320x50,320x100,320x480,300x250,640x360", "app", None)
    for app_item in APP_INVENTORY:
        app_node = add_ad_unit(app_item["app"], f"/app/{app_item['app']}", "320x50,320x100,320x480,300x250,640x360", "app", app_root)
        for screen_name, slots in app_item["screens"]:
            screen_node = add_ad_unit(screen_name, f"{app_node.path}/{screen_name}", "320x50,320x100,320x480,300x250,640x360", "app", app_node)
            for slot_name, size_support, slot_format, device, tier in slots:
                leaf = add_ad_unit(slot_name, f"{screen_node.path}/{slot_name}", size_support, "app", screen_node)
                leaf_units.append(
                    {
                        "ad_unit": leaf,
                        "environment": "app",
                        "sizes": [item.strip() for item in size_support.split(",")],
                        "slot_format": slot_format,
                        "device": device,
                        "inventory_tier": tier,
                        "content_category": app_item["category"],
                        "app_bundle": app_item["bundle"],
                        "label": app_item["app"],
                    }
                )

    ctv_root = add_ad_unit("ctv", "/ctv", "1920x1080", "ctv", None)
    for network in CTV_INVENTORY:
        network_node = add_ad_unit(network["network"], f"/ctv/{network['network']}", "1920x1080", "ctv", ctv_root)
        for channel_name, slots in network["channels"]:
            channel_node = add_ad_unit(channel_name, f"{network_node.path}/{channel_name}", "1920x1080", "ctv", network_node)
            for slot_name, size_support, slot_format, device, tier in slots:
                leaf = add_ad_unit(slot_name, f"{channel_node.path}/{slot_name}", size_support, "ctv", channel_node)
                leaf_units.append(
                    {
                        "ad_unit": leaf,
                        "environment": "ctv",
                        "sizes": [item.strip() for item in size_support.split(",")],
                        "slot_format": slot_format,
                        "device": device,
                        "inventory_tier": tier,
                        "content_category": network["category"],
                        "label": network["network"],
                    }
                )

    return leaf_units


def create_placements(leaf_units: list[dict]) -> list[Placement]:
    placements: list[Placement] = []
    env_groups = {
        environment: [item for item in leaf_units if item["environment"] == environment]
        for environment in ["web", "app", "ctv"]
    }
    placement_names = [
        "Homepage Premium Rail",
        "Article Mid-Page Cluster",
        "Metro Reach Bundle",
        "Performance Native Set",
        "Video Scale Pack",
        "Commerce High Intent Pack",
        "Sports Championship Takeover",
        "Finance Decisioning Layer",
        "News Breaking Inventory Set",
        "CTV Household Reach Pack",
    ]

    for index in range(TARGET_COUNTS["placements"]):
        environment = RNG.choices(["web", "app", "ctv"], weights=[0.45, 0.3, 0.25], k=1)[0]
        group = env_groups[environment]
        selected = RNG.sample(group, k=min(len(group), RNG.randint(2, 4)))
        format_value = "video" if environment == "ctv" else RNG.choice(["display", "native", "video"])
        device = "ctv" if environment == "ctv" else ("mobile" if environment == "app" else RNG.choice(["desktop", "mobile"]))
        placement = Placement(
            name=f"{selected[0]['label'].title()} | {placement_names[index % len(placement_names)]} | {index + 1:02d}",
            device_type=device,
            placement_format=format_value,
            notes=f"{environment.upper()} placement grouping for {selected[0]['content_category']} inventory and ops testing.",
            created_at=random_datetime(150),
        )
        placement.ad_units = [item["ad_unit"] for item in selected]
        db.session.add(placement)
        placements.append(placement)

    db.session.flush()
    return placements


def create_advertisers() -> list[Advertiser]:
    advertisers = []
    for name, vertical in ADVERTISER_CATALOG:
        advertiser = Advertiser(
            name=name,
            vertical=vertical,
            status="active",
            created_at=random_datetime(300),
        )
        db.session.add(advertiser)
        advertisers.append(advertiser)
    db.session.flush()
    return advertisers


def create_orders(advertisers: list[Advertiser]) -> list[dict]:
    orders: list[dict] = []
    for advertiser_index, advertiser in enumerate(advertisers):
        for position in range(4):
            status = choose_order_status(advertiser_index, position)
            environment = choose_order_environment(advertiser.vertical, position)
            objective = RNG.choice(objective_pool(environment))
            start_date, end_date = status_dates(status)
            order = Order(
                advertiser=advertiser,
                name=build_order_name(advertiser.name, environment, objective, status, position + 1),
                start_date=start_date,
                end_date=end_date,
                status=status,
                notes=f"{objective} order for {environment.upper()} inventory. Managed market: {RNG.choice(['India National', 'Delhi NCR', 'Metro Cities', 'South India'])}.",
                created_at=created_from_range(start_date - timedelta(days=30), start_date),
            )
            db.session.add(order)
            orders.append(
                {
                    "order": order,
                    "advertiser": advertiser,
                    "environment": environment,
                    "objective": objective,
                    "status": status,
                    "sequence": position + 1,
                }
            )
    db.session.flush()
    return orders


def scenario_pack_for_order(order_record: dict, absolute_index: int) -> list[str]:
    status = order_record["status"]
    if status == "active":
        return ACTIVE_SCENARIO_PACKS[absolute_index % len(ACTIVE_SCENARIO_PACKS)]
    if status == "paused":
        return ["paused", "paused", "draft", "no_approved_creative"]
    if status == "upcoming":
        return ["upcoming", "draft", "upcoming", "draft"]
    return ["expired", "expired", "low_delivery", "geo_sensitive"]


def candidate_leaf_units(leaf_units: list[dict], environment: str, vertical: str) -> list[dict]:
    vertical_preferences = {
        "Sportswear": ["sports"],
        "Streaming": ["entertainment", "kids", "sports"],
        "Consumer Electronics": ["technology", "entertainment", "sports"],
        "Fintech": ["finance", "news", "shopping"],
        "Commerce": ["shopping", "food"],
        "Marketplace": ["shopping", "news"],
        "Food Delivery": ["food"],
        "Quick Commerce": ["food", "shopping"],
        "Grocery": ["food", "shopping"],
        "Beauty": ["shopping"],
        "Travel": ["travel", "news"],
        "Gaming": ["gaming", "sports"],
        "Automotive": ["auto", "news"],
        "Healthcare": ["news", "food"],
    }
    preferred = vertical_preferences.get(vertical, [])
    matches = [item for item in leaf_units if item["environment"] == environment and item["content_category"] in preferred]
    return matches or [item for item in leaf_units if item["environment"] == environment]


def line_item_theme(environment: str, slot_format: str, scenario: str, slot_index: int) -> str:
    base = {
        "web": ["Reach Layer", "Commerce Retargeting", "Native Engagement", "Audience Backup"],
        "app": ["Install Burst", "Retention Layer", "Offer Reminder", "Rewarded Extension"],
        "ctv": ["Preroll Reach", "Midroll Frequency", "Household Layer", "Sports Lift"],
    }[environment][slot_index]
    scenario_suffix = {
        "healthy": "Primary",
        "low_delivery": "Pacing Watch",
        "paused": "Hold",
        "upcoming": "Launch Prep",
        "draft": "Draft Setup",
        "expired": "Legacy",
        "no_approved_creative": "QA Hold",
        "size_mismatch": "Size QA",
        "geo_sensitive": "Regional",
        "key_value_sensitive": "Metadata Gate",
        "lost_in_auction": "Auction Watch",
    }[scenario]
    return f"{base} {scenario_suffix}".strip()


def append_key_value_rule(line_item: LineItem, key_lookup: dict[str, dict[str, KeyValueValue]], key_name: str, value_name: str) -> None:
    value = key_lookup[key_name][value_name]
    line_item.targeting_rules.append(
        LineItemTargeting(
            target_type="key_value",
            key_value_value=value,
            created_at=random_datetime(120),
        )
    )


def create_line_items_and_creatives(
    order_records: list[dict],
    leaf_units: list[dict],
    key_lookup: dict[str, dict[str, KeyValueValue]],
) -> tuple[list[dict], list[Creative]]:
    line_item_records: list[dict] = []
    creatives: list[Creative] = []
    extra_creative_indexes = set(RNG.sample(range(TARGET_COUNTS["line_items"]), TARGET_COUNTS["creatives"] - TARGET_COUNTS["line_items"]))
    line_item_index = 0
    creative_index = 0

    for order_offset, order_record in enumerate(order_records):
        scenario_pack = scenario_pack_for_order(order_record, order_offset)
        environment = order_record["environment"]
        advertiser = order_record["advertiser"]
        order = order_record["order"]
        order_candidates = candidate_leaf_units(leaf_units, environment, advertiser.vertical)

        for slot_index, scenario in enumerate(scenario_pack):
            leaf = RNG.choice(order_candidates)
            size = RNG.choice(leaf["sizes"])
            line_item_type = line_item_type_ladder(environment)[slot_index]
            if scenario == "lost_in_auction":
                line_item_type = "Network" if environment != "ctv" else "Standard"
            if scenario == "paused":
                line_item_type = "Standard"
            if scenario == "draft":
                line_item_type = "House" if environment == "web" else line_item_type

            status = line_item_status_for_scenario(scenario)
            start_date, end_date = line_item_dates(order.start_date, order.end_date, scenario)
            geo_values = RNG.sample(KEY_VALUE_CATALOG["geo"], k=RNG.randint(1, 2))
            geo_targeting = ",".join(geo_values)
            audience = RNG.choice(KEY_VALUE_CATALOG["audience"])
            language = RNG.choice(KEY_VALUE_CATALOG["language"])
            device = leaf["device"]
            os_value = choose_os(environment)
            browser = choose_browser(device)

            line_item = LineItem(
                advertiser=advertiser,
                order=order,
                name=build_line_item_name(
                    order.name,
                    line_item_theme(environment, leaf["slot_format"], scenario, slot_index),
                    line_item_type,
                    size,
                    slot_index + 1,
                ),
                line_item_type=line_item_type,
                priority=priority_for_type(line_item_type),
                start_date=start_date,
                end_date=end_date,
                goal_impressions=goal_for_environment(environment, line_item_type),
                delivered_impressions=0,
                cpm=cpm_for_line_item(environment, line_item_type, scenario),
                frequency_cap=RNG.randint(1, 6 if environment == "ctv" else 8),
                creative_size=size,
                geo_targeting=geo_targeting,
                device_targeting=device,
                audience_targeting=audience,
                status=status,
                notes=note_for_line_item(environment, order_record["objective"], scenario, leaf["content_category"], geo_targeting),
                created_at=created_from_range(order.start_date - timedelta(days=21), start_date),
            )
            line_item.delivered_impressions = delivered_for_scenario(line_item.goal_impressions, scenario)
            db.session.add(line_item)

            line_item.targeting_rules.append(LineItemTargeting(target_type="ad_unit", target_value=leaf["ad_unit"].path, created_at=random_datetime(120)))
            line_item.targeting_rules.append(LineItemTargeting(target_type="content_category", target_value=leaf["content_category"], created_at=random_datetime(120)))
            append_key_value_rule(line_item, key_lookup, "geo_country", "in")
            append_key_value_rule(line_item, key_lookup, "geo", geo_values[0])
            append_key_value_rule(line_item, key_lookup, "device", device)
            append_key_value_rule(line_item, key_lookup, "audience", audience)
            append_key_value_rule(line_item, key_lookup, "inventory_tier", leaf["inventory_tier"])
            append_key_value_rule(line_item, key_lookup, "language", language)
            append_key_value_rule(line_item, key_lookup, "supply_channel", environment)
            append_key_value_rule(line_item, key_lookup, "deal_type", deal_type_for_line_item(line_item_type))

            if environment == "web":
                append_key_value_rule(line_item, key_lookup, "browser", browser)
            if environment == "app":
                append_key_value_rule(line_item, key_lookup, "app_bundle", leaf["app_bundle"])
                append_key_value_rule(line_item, key_lookup, "os", os_value if os_value in key_lookup["os"] else "android")
            if environment == "ctv":
                append_key_value_rule(line_item, key_lookup, "os", os_value if os_value in key_lookup["os"] else "roku")

            if scenario == "key_value_sensitive":
                if environment == "web":
                    append_key_value_rule(line_item, key_lookup, "browser", "safari")
                elif environment == "app":
                    append_key_value_rule(line_item, key_lookup, "os", "ios")
                else:
                    append_key_value_rule(line_item, key_lookup, "os", "tvos")

            creative_count = 2 if line_item_index in extra_creative_indexes else 1
            for variant in range(creative_count):
                creative_index += 1
                creative_size = size
                approval_status = "approved"
                is_active = True

                if scenario == "no_approved_creative":
                    approval_status = RNG.choice(["pending", "rejected", "broken"])
                elif scenario == "size_mismatch":
                    creative_size = "300x250" if size != "300x250" else "728x90"
                elif scenario == "draft" and variant == 0:
                    approval_status = "pending"
                elif variant == 1 and scenario not in {"size_mismatch", "no_approved_creative"}:
                    approval_status = RNG.choice(["approved", "pending", "rejected"])
                    is_active = approval_status == "approved" and RNG.choice([True, True, False])

                creative_format = creative_format_for_leaf(environment, leaf["slot_format"])
                destination = f"https://{slugify(advertiser.name)}.example.com/{slugify(order_record['objective'])}/{creative_index}"
                snippet = (
                    f"https://vast.example.com/{slugify(advertiser.name)}/{creative_index}.xml"
                    if creative_format in {"video", "ctv"}
                    else f"<script>serve('{brand_code(advertiser.name)}','{creative_index}');</script>"
                )

                creative = Creative(
                    line_item=line_item,
                    name=build_creative_name(advertiser.name, creative_format, creative_size, variant + 1),
                    creative_format=creative_format,
                    size=creative_size,
                    destination_url=destination,
                    approval_status=approval_status,
                    tag_snippet=snippet,
                    preview_text=f"{title_from_slug(slugify(order_record['objective']))} creative for {advertiser.name}",
                    is_active=is_active,
                    created_at=created_from_range(line_item.start_date - timedelta(days=14), line_item.start_date),
                )
                db.session.add(creative)
                creatives.append(creative)

            line_item_records.append(
                {
                    "line_item": line_item,
                    "advertiser": advertiser,
                    "order": order,
                    "leaf": leaf,
                    "scenario": scenario,
                    "environment": environment,
                    "device": device,
                    "browser": browser,
                    "os": os_value,
                    "language": language,
                    "geo_values": geo_values,
                    "audience": audience,
                }
            )
            line_item_index += 1

    db.session.flush()
    return line_item_records, creatives


def create_issue_templates() -> dict[str, TroubleshootingIssue]:
    issue_map: dict[str, TroubleshootingIssue] = {}
    for title, symptoms, causes, where_to_check, recommended_fix, severity, category, module in ISSUE_TEMPLATES:
        issue = TroubleshootingIssue(
            title=title,
            symptoms=symptoms,
            likely_causes=causes,
            where_to_check=where_to_check,
            recommended_fix=recommended_fix,
            severity=severity,
            category=category,
            related_module=module,
            created_at=random_datetime(240),
        )
        db.session.add(issue)
        issue_map[title] = issue
    db.session.flush()
    return issue_map


def create_sheet_rows(issue_map: dict[str, TroubleshootingIssue], line_item_records: list[dict]) -> list[TroubleshootingSheetRow]:
    owners = [
        "Riya Ops",
        "Aman AdOps",
        "Nisha QA",
        "Karthik Programmatic",
        "Megha Yield",
        "Arjun Trafficking",
        "Pooja CTV Ops",
        "Rahul Delivery",
    ]
    candidate_records = [record for record in line_item_records if record["scenario"] in SCENARIO_TO_ISSUE]
    sampled_records = RNG.sample(candidate_records, TARGET_COUNTS["sheet_rows"])
    rows: list[TroubleshootingSheetRow] = []

    for index, record in enumerate(sampled_records, start=1):
        line_item = record["line_item"]
        issue_title = SCENARIO_TO_ISSUE[record["scenario"]]
        issue_template = issue_map[issue_title]
        row_status = RNG.choices(["open", "in_progress", "resolved", "blocked"], weights=[0.45, 0.3, 0.15, 0.1], k=1)[0]
        due_date = TODAY + timedelta(days=RNG.randint(1, 10)) if row_status in {"open", "in_progress", "blocked"} else TODAY - timedelta(days=RNG.randint(1, 10))

        row = TroubleshootingSheetRow(
            issue_title=issue_title,
            line_item=line_item,
            campaign_name=line_item.order.name,
            problem=f"{line_item.name} is showing symptoms consistent with '{issue_title.lower()}'.",
            possible_reason=issue_template.likely_causes,
            where_to_check=issue_template.where_to_check,
            suggested_fix=issue_template.recommended_fix,
            severity=issue_template.severity,
            owner=owners[index % len(owners)],
            due_date=due_date,
            status=row_status,
            notes=f"Scenario source: {record['scenario']}. Inventory path: {record['leaf']['ad_unit'].path}.",
            created_at=random_datetime(90),
        )
        db.session.add(row)
        rows.append(row)

    db.session.flush()
    return rows


def request_context_from_record(record: dict, force_failure: bool) -> dict:
    line_item = record["line_item"]
    leaf = record["leaf"]
    key_values = {
        rule.key_value_value.key.name: rule.key_value_value.value
        for rule in line_item.targeting_rules
        if rule.target_type == "key_value" and rule.key_value_value
    }
    content_category = next((rule.target_value for rule in line_item.targeting_rules if rule.target_type == "content_category"), leaf["content_category"])
    context = {
        "ad_unit_id": leaf["ad_unit"].id,
        "ad_unit_path": leaf["ad_unit"].path,
        "device": record["device"],
        "geo": record["geo_values"][0],
        "audience": record["audience"],
        "creative_size": line_item.creative_size,
        "time": datetime.combine(TODAY, datetime.min.time()).isoformat(),
        "content_category": content_category,
        "key_values": dict(key_values),
    }
    context["key_values"].setdefault("content_category", content_category)
    context["key_values"].setdefault("geo", context["geo"])
    context["key_values"].setdefault("device", context["device"])
    context["key_values"].setdefault("audience", context["audience"])

    if force_failure:
        failure_mode = RNG.choice(["geo", "device", "size", "key_value", "ad_unit"])
        if failure_mode == "geo":
            alternatives = [value for value in KEY_VALUE_CATALOG["geo"] if value != context["geo"]]
            context["geo"] = RNG.choice(alternatives)
            context["key_values"]["geo"] = context["geo"]
        elif failure_mode == "device":
            alternatives = [value for value in KEY_VALUE_CATALOG["device"] if value != context["device"]]
            context["device"] = RNG.choice(alternatives)
            context["key_values"]["device"] = context["device"]
        elif failure_mode == "size":
            context["creative_size"] = "300x250" if context["creative_size"] != "300x250" else "728x90"
        elif failure_mode == "key_value":
            if "os" in context["key_values"]:
                alternatives = [value for value in KEY_VALUE_CATALOG["os"] if value != context["key_values"]["os"]]
                context["key_values"]["os"] = RNG.choice(alternatives)
            elif "browser" in context["key_values"]:
                alternatives = [value for value in KEY_VALUE_CATALOG["browser"] if value != context["key_values"]["browser"]]
                context["key_values"]["browser"] = RNG.choice(alternatives)
            else:
                context["key_values"]["inventory_tier"] = "remnant" if context["key_values"].get("inventory_tier") != "remnant" else "premium"
        else:
            alternatives = [item for item in record["leaf_pool"] if item["ad_unit"].id != leaf["ad_unit"].id and item["environment"] == record["environment"]]
            if alternatives:
                chosen = RNG.choice(alternatives)
                context["ad_unit_id"] = chosen["ad_unit"].id
                context["ad_unit_path"] = chosen["ad_unit"].path

    return context


def create_simulations(line_item_records: list[dict], leaf_units: list[dict]) -> list[AuctionSimulation]:
    records = [record for record in line_item_records if record["line_item"].status in {"active", "paused", "expired", "upcoming", "draft"}]
    simulations: list[AuctionSimulation] = []
    for record in records:
        record["leaf_pool"] = leaf_units

    sampled_records = RNG.sample(records, TARGET_COUNTS["simulations"])
    for index, record in enumerate(sampled_records, start=1):
        force_failure = record["scenario"] not in {"healthy", "low_delivery", "lost_in_auction"} or RNG.choice([True, False, False])
        request_context = request_context_from_record(record, force_failure=force_failure)
        mode = "Waterfall" if index % 2 == 0 else "Unified Auction"
        result = run_waterfall(request_context) if mode == "Waterfall" else run_unified_auction(request_context)
        simulation = AuctionSimulation(
            mode=mode,
            ad_unit_id=request_context["ad_unit_id"],
            request_context=request_context,
            winner_line_item_id=result["winner"]["id"] if result.get("winner") else None,
            evaluation_data=result,
            created_at=random_datetime(60),
        )
        db.session.add(simulation)
        simulations.append(simulation)

    db.session.flush()
    return simulations


def create_activity_logs(
    admin: User,
    advertisers: list[Advertiser],
    order_records: list[dict],
    line_item_records: list[dict],
    creatives: list[Creative],
    issue_map: dict[str, TroubleshootingIssue],
    sheet_rows: list[TroubleshootingSheetRow],
    simulations: list[AuctionSimulation],
) -> list[ActivityLog]:
    logs: list[ActivityLog] = []
    simulation_pool = simulations[:]
    issue_pool = list(issue_map.values())

    for _ in range(TARGET_COUNTS["activity_logs"]):
        entity_type = RNG.choices(["advertiser", "order", "line_item", "creative", "issue", "sheet_row", "simulation"], weights=[1, 2, 5, 4, 2, 2, 3], k=1)[0]

        if entity_type == "advertiser":
            advertiser = RNG.choice(advertisers)
            action = RNG.choice(["created", "reviewed", "updated"])
            entity_id = advertiser.id
            message = f"Advertiser {advertiser.name} {action} for current demand planning."
        elif entity_type == "order":
            order_record = RNG.choice(order_records)
            action = RNG.choice(["created", "updated", "paused", "scheduled"])
            entity_id = order_record["order"].id
            message = f"Order {order_record['order'].name} moved through {action} workflow."
        elif entity_type == "line_item":
            record = RNG.choice(line_item_records)
            action = RNG.choice(["created", "updated", "evaluated", "trafficked"])
            entity_id = record["line_item"].id
            message = f"Line item {record['line_item'].name} {action}; status is {record['line_item'].status}."
        elif entity_type == "creative":
            creative = RNG.choice(creatives)
            action = RNG.choice(["approved", "rejected", "synced", "updated"])
            entity_id = creative.id
            message = f"Creative {creative.name} {action} with state {creative.approval_status}."
        elif entity_type == "issue":
            issue = RNG.choice(issue_pool)
            action = RNG.choice(["reviewed", "updated", "documented"])
            entity_id = issue.id
            message = f"Issue template {issue.title} {action} for ops knowledge base."
        elif entity_type == "sheet_row":
            row = RNG.choice(sheet_rows)
            action = RNG.choice(["assigned", "updated", "resolved"])
            entity_id = row.id
            message = f"Troubleshooting row {row.issue_title} {action} to {row.owner}."
        else:
            simulation = RNG.choice(simulation_pool)
            action = "run"
            entity_id = simulation.id
            winner = simulation.winner_line_item.name if simulation.winner_line_item else "No winner"
            message = f"{simulation.mode} simulation #{simulation.id} completed with winner: {winner}."

        log = ActivityLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            message=message,
            details={"seeded": True},
            actor_id=admin.id,
            created_at=random_datetime(45),
        )
        db.session.add(log)
        logs.append(log)

    db.session.flush()
    return logs


def print_summary() -> None:
    line_item_status = Counter(status for (status,) in db.session.query(LineItem.status).all())
    creative_status = Counter(status for (status,) in db.session.query(Creative.approval_status).all())
    order_status = Counter(status for (status,) in db.session.query(Order.status).all())
    simulation_modes = Counter(mode for (mode,) in db.session.query(AuctionSimulation.mode).all())

    print("Seed completed.")
    print("Default admin login: admin@adflow.local / Admin@123")
    print("Seed summary:")
    print(f"  Advertisers: {Advertiser.query.count()}")
    print(f"  Orders: {Order.query.count()}")
    print(f"  Line Items: {LineItem.query.count()}")
    print(f"  Creatives: {Creative.query.count()}")
    print(f"  Ad Units: {AdUnit.query.count()}")
    print(f"  Placements: {Placement.query.count()}")
    print(f"  Targeting Keys: {KeyValueKey.query.count()}")
    print(f"  Targeting Values: {KeyValueValue.query.count()}")
    print(f"  Troubleshooting Issues: {TroubleshootingIssue.query.count()}")
    print(f"  Troubleshooting Sheet Rows: {TroubleshootingSheetRow.query.count()}")
    print(f"  Auction Simulations: {AuctionSimulation.query.count()}")
    print(f"  Activity Logs: {ActivityLog.query.count()}")
    print(f"  Line Item Status Mix: {dict(line_item_status)}")
    print(f"  Order Status Mix: {dict(order_status)}")
    print(f"  Creative Approval Mix: {dict(creative_status)}")
    print(f"  Simulation Modes: {dict(simulation_modes)}")


def main() -> None:
    app = create_app()
    with app.app_context():
        reset_schema()
        admin = create_admin_user()
        key_lookup = create_key_values()
        leaf_units = create_ad_units()
        create_placements(leaf_units)
        advertisers = create_advertisers()
        order_records = create_orders(advertisers)
        line_item_records, creatives = create_line_items_and_creatives(order_records, leaf_units, key_lookup)
        issue_map = create_issue_templates()
        sheet_rows = create_sheet_rows(issue_map, line_item_records)
        db.session.commit()

        simulations = create_simulations(line_item_records, leaf_units)
        db.session.commit()

        create_activity_logs(admin, advertisers, order_records, line_item_records, creatives, issue_map, sheet_rows, simulations)
        db.session.commit()
        print_summary()


if __name__ == "__main__":
    main()
