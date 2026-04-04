from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from ..models import (
    AdUnit,
    Advertiser,
    Creative,
    LineItem,
    LineItemTargeting,
    Order,
    Placement,
    PublisherSite,
    User,
    db,
)


TEST_ADMIN_EMAIL = "admin@adflow.local"
TEST_ADMIN_PASSWORD = "Admin@123"
TEST_PUBLISHER_SLUG = "auction-lab-daily"
TEST_SLOT_CODE = "test_top_banner"
TEST_PAGE_TYPE = "auction_test"
TEST_CATEGORY = "news"
TEST_GEO = "delhi_ncr"
TEST_DEVICE = "desktop"
TEST_AUDIENCE = "sports_fans"
TEST_SLOT_POSITION = "top"


def _build_target_rule(line_item, target_type, target_value):
    return LineItemTargeting(
        line_item=line_item,
        target_type=target_type,
        operator="equals",
        target_value=target_value,
    )


def seed_test_auction_fixture(reset_database=False):
    """Create a deterministic 5-way auction fixture for runtime verification.

    The fixture uses an isolated ad unit so the request sees exactly five live
    competitors and nothing else. That makes both the UI and the DB logs easy to
    reason about while learning the auction flow.
    """

    if reset_database:
        db.drop_all()
        db.create_all()

    admin = User.query.filter_by(email=TEST_ADMIN_EMAIL).first()
    if not admin:
        admin = User(name="AdFlow Admin", email=TEST_ADMIN_EMAIL, role="admin")
        admin.set_password(TEST_ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.flush()

    publisher = PublisherSite.query.filter_by(slug=TEST_PUBLISHER_SLUG).first()
    if not publisher:
        publisher = PublisherSite(
            name="Auction Lab Daily",
            slug=TEST_PUBLISHER_SLUG,
            domain="auction-lab.local",
            status="active",
            primary_category=TEST_CATEGORY,
        )
        db.session.add(publisher)
        db.session.flush()

    ad_unit = AdUnit.query.filter_by(path=TEST_SLOT_CODE).first()
    if not ad_unit:
        ad_unit = AdUnit(
            name="Auction Test Top Banner",
            path=TEST_SLOT_CODE,
            ad_unit_code=TEST_SLOT_CODE,
            slot_name="Auction Test Top Banner",
            size_support="728x90",
            environment="web",
            is_active=True,
            publisher_site_id=publisher.id,
        )
        db.session.add(ad_unit)
        db.session.flush()

    placement = Placement.query.filter_by(name="Auction Test Placement").first()
    if not placement:
        placement = Placement(
            name="Auction Test Placement",
            device_type="desktop",
            placement_format="display",
            notes="Single-slot deterministic placement for live auction verification.",
        )
        placement.ad_units = [ad_unit]
        db.session.add(placement)

    advertiser = Advertiser.query.filter_by(name="Auction Test Advertiser").first()
    if not advertiser:
        advertiser = Advertiser(name="Auction Test Advertiser", vertical="Technology", status="active")
        db.session.add(advertiser)
        db.session.flush()

    today = date.today()
    order = Order.query.filter_by(name="Auction Test Order").first()
    if not order:
        order = Order(
            advertiser=advertiser,
            name="Auction Test Order",
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=14),
            status="active",
            workflow_state="Live",
            budget_amount=Decimal("5000.00"),
            spent_amount=Decimal("0.00"),
            notes="Dedicated order for the isolated publisher auction test page.",
        )
        db.session.add(order)
        db.session.flush()

    if LineItem.query.filter(LineItem.name.like("Auction Test LI %")).count() == 0:
        cpm_values = ["12.50", "10.25", "9.10", "8.40", "7.75"]
        weights = [120, 100, 90, 80, 70]
        for index, (cpm_value, weight) in enumerate(zip(cpm_values, weights), start=1):
            line_item = LineItem(
                advertiser=advertiser,
                order=order,
                name=f"Auction Test LI {index}",
                line_item_type="Standard",
                priority=6,
                delivery_weight=weight,
                start_date=today - timedelta(days=1),
                end_date=today + timedelta(days=14),
                goal_impressions=100000,
                delivered_impressions=0,
                cpm=Decimal(cpm_value),
                frequency_cap=5,
                creative_size="728x90",
                geo_targeting=TEST_GEO,
                device_targeting=TEST_DEVICE,
                audience_targeting=TEST_AUDIENCE,
                status="active",
                workflow_state="Live",
                budget_amount=Decimal("1000.00"),
                spent_amount=Decimal("0.00"),
                daily_impression_cap=5000,
                daily_spend_cap=Decimal("250.00"),
                launch_ready=True,
                last_launched_at=datetime.utcnow(),
                notes="Deterministic live competitor for the single-slot auction test page.",
            )
            db.session.add(line_item)
            db.session.flush()

            db.session.add_all(
                [
                    _build_target_rule(line_item, "ad_unit", TEST_SLOT_CODE),
                    _build_target_rule(line_item, "page_type", TEST_PAGE_TYPE),
                    _build_target_rule(line_item, "slot_position", TEST_SLOT_POSITION),
                    _build_target_rule(line_item, "content_category", TEST_CATEGORY),
                ]
            )

            creative = Creative(
                line_item=line_item,
                name=f"Auction Test Creative {index}",
                creative_format="image",
                size="728x90",
                destination_url=f"https://example.com/auction-test/{index}",
                approval_status="approved",
                asset_url=f"https://cdn.example.com/auction-test/{index}.png",
                preview_text=f"Auction Test Winner Candidate #{index}",
                is_active=True,
            )
            db.session.add(creative)

    db.session.commit()

    line_items = (
        LineItem.query.filter(LineItem.name.like("Auction Test LI %"))
        .order_by(LineItem.cpm.desc(), LineItem.id.asc())
        .all()
    )
    return {
        "admin_email": TEST_ADMIN_EMAIL,
        "admin_password": TEST_ADMIN_PASSWORD,
        "publisher_url": "/publisher/test-auction?debug=1",
        "slot_id": TEST_SLOT_CODE,
        "page_type": TEST_PAGE_TYPE,
        "page_url": "http://127.0.0.1:5000/publisher/test-auction?debug=1",
        "device_type": TEST_DEVICE,
        "geo": TEST_GEO,
        "category": TEST_CATEGORY,
        "audience": TEST_AUDIENCE,
        "slot_position": TEST_SLOT_POSITION,
        "size": "728x90",
        "line_items": [
            {
                "id": line_item.id,
                "name": line_item.name,
                "cpm": float(line_item.cpm or 0),
                "weight": line_item.delivery_weight,
            }
            for line_item in line_items
        ],
    }
