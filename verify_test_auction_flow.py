from app import create_app
from app.models import AdRequest, ClickLog, DeliveryLog, ImpressionLog, User, db
from app.services.test_auction_fixture import (
    TEST_AUDIENCE,
    TEST_CATEGORY,
    TEST_DEVICE,
    TEST_GEO,
    TEST_PAGE_TYPE,
    TEST_SLOT_CODE,
    seed_test_auction_fixture,
)


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def main():
    app = create_app()
    with app.app_context():
        fixture = seed_test_auction_fixture(reset_database=True)
        client = app.test_client()

        admin = User.query.filter_by(email=fixture["admin_email"]).first()
        with client.session_transaction() as session:
            session["user_id"] = admin.id

        page_response = client.get("/publisher/test-auction?debug=1")
        assert_equal(page_response.status_code, 200, "Publisher test page should load")
        page_html = page_response.get_data(as_text=True)
        if TEST_SLOT_CODE not in page_html:
            raise AssertionError("Publisher test page did not render the isolated auction slot.")

        ad_response = client.get(
            "/publisher/ad",
            query_string={
                "ad_unit_code": TEST_SLOT_CODE,
                "slot_id": TEST_SLOT_CODE,
                "page_type": TEST_PAGE_TYPE,
                "page_url": fixture["page_url"],
                "size": fixture["size"],
                "device_type": TEST_DEVICE,
                "category": TEST_CATEGORY,
                "slot_position": fixture["slot_position"],
                "geo": TEST_GEO,
                "audience": TEST_AUDIENCE,
                "debug": "1",
            },
        )
        assert_equal(ad_response.status_code, 200, "Auction request should return JSON")
        payload = ad_response.get_json()
        assert_equal(payload["status"], "filled", "Auction should return a winner")
        assert_equal(len(payload["debug"]["candidates"]), 5, "Exactly five line items should be evaluated")
        assert_equal(payload["debug"]["considered_count"], 5, "Considered count should reflect all targeted competitors")
        assert_equal(payload["debug"]["eligible_count"], 5, "Eligible count should reflect filtered auction entrants")
        assert_equal(payload["debug"]["ineligible_count"], 0, "Ineligible count should be zero in the positive scenario")

        eligible_candidates = [candidate for candidate in payload["debug"]["candidates"] if candidate["eligible"]]
        assert_equal(len(eligible_candidates), 5, "All five seeded line items should be eligible")
        winner_name = payload["debug"]["selected_line_item"]
        considered_names = [candidate["line_item"] for candidate in payload["debug"]["candidates"]]
        if winner_name not in considered_names:
            raise AssertionError("Winning line item must be part of the five evaluated candidates.")
        if "Auction Test LI 1" != winner_name:
            raise AssertionError(f"Expected Auction Test LI 1 to win the highest-CPM auction, got {winner_name}.")
        assert_equal(payload["debug"]["selected_creative"], "Auction Test Creative 1", "Winning creative should be selected")
        if f"/publisher/creative-asset/{payload['creative_id']}.svg" not in (payload["html"] or ""):
            raise AssertionError("Rendered creative HTML did not contain the winning creative asset.")

        impression_response = client.post("/track/impression", json=payload["impression_payload"])
        assert_equal(impression_response.status_code, 200, "Impression endpoint should succeed")
        impression_json = impression_response.get_json()
        assert_equal(impression_json["ok"], True, "Impression should be logged")

        click_response = client.get(f"/track/click/{payload['creative_id']}?request_id={payload['request_id']}")
        assert_equal(click_response.status_code, 302, "Click endpoint should redirect to the destination URL")

        diagnostics_response = client.get(f"/auctions/{payload['request_id']}?format=json")
        assert_equal(diagnostics_response.status_code, 200, "Diagnostics JSON should load for the request")
        diagnostics = diagnostics_response.get_json()
        assert_equal(diagnostics["winner"], "Auction Test LI 1", "Diagnostics should report the winning line item")
        assert_equal(len(diagnostics["candidates"]), 5, "Diagnostics should list all evaluated candidates")
        assert_equal(diagnostics["eligible_count"], 5, "Diagnostics should show all five lines as eligible")
        assert_equal(diagnostics["ineligible_count"], 0, "Diagnostics should show no filtered lines for the positive path")
        assert_equal(diagnostics["impression_status"], True, "Diagnostics should show the impression as fired")
        assert_equal(diagnostics["click_status"], True, "Diagnostics should show the click as logged")

        ad_request = AdRequest.query.filter_by(request_id=payload["request_id"]).first()
        assert_equal(ad_request.render_status, "rendered", "Request render status should advance after impression")
        assert_equal(ImpressionLog.query.filter_by(request_id=ad_request.id).count(), 1, "One impression row should be stored")
        assert_equal(ClickLog.query.filter_by(request_id=ad_request.id).count(), 1, "One click row should be stored")

        delivery_events = [
            row.event_type
            for row in DeliveryLog.query.filter_by(request_id=ad_request.id).order_by(DeliveryLog.id.asc()).all()
        ]
        for expected_event in ["request", "eligible", "win", "impression", "click"]:
            if expected_event not in delivery_events:
                raise AssertionError(f"Missing delivery event {expected_event!r} in delivery logs.")

        no_fill_response = client.get(
            "/publisher/ad",
            query_string={
                "ad_unit_code": TEST_SLOT_CODE,
                "slot_id": TEST_SLOT_CODE,
                "page_type": TEST_PAGE_TYPE,
                "page_url": fixture["page_url"],
                "size": fixture["size"],
                "device_type": TEST_DEVICE,
                "category": TEST_CATEGORY,
                "slot_position": fixture["slot_position"],
                "geo": "mumbai",
                "audience": TEST_AUDIENCE,
                "debug": "1",
            },
        )
        assert_equal(no_fill_response.status_code, 200, "No-fill request should still return JSON")
        no_fill_payload = no_fill_response.get_json()
        assert_equal(no_fill_payload["status"], "house", "Fallback should serve when no eligible line item remains")
        assert_equal(no_fill_payload["filled"], False, "Fallback response should not mark the slot as filled")
        assert_equal(no_fill_payload["debug"]["eligible_count"], 0, "No-fill path should have zero eligible candidates")
        assert_equal(no_fill_payload["debug"]["ineligible_count"], 5, "No-fill path should filter out all five candidates")
        if no_fill_payload["click_url"] is not None or no_fill_payload["impression_url"] is not None:
            raise AssertionError("Fallback responses must not expose winner tracking URLs.")

        print("Auction flow verification passed.")
        print(f"Publisher test page: {fixture['publisher_url']}")
        print("Candidates considered:")
        for candidate in diagnostics["candidates"]:
            print(
                f"  - {candidate['line_item']}: eligible={candidate['eligible']} "
                f"win={candidate['win_reason'] or '-'} loss={candidate['loss_reason'] or '-'} cpm={candidate['cpm']}"
            )
        print(f"Winner: {diagnostics['winner']} / {diagnostics['creative']}")
        print(f"Diagnostics URL: /auctions/{payload['request_id']}")


if __name__ == "__main__":
    main()
