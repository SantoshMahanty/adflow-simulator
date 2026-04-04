from app import create_app
from app.services.test_auction_fixture import seed_test_auction_fixture


def main():
    app = create_app()
    with app.app_context():
        fixture = seed_test_auction_fixture(reset_database=True)
        print("Deterministic auction fixture seeded.")
        print(f"Admin login: {fixture['admin_email']} / {fixture['admin_password']}")
        print(f"Publisher test page: {fixture['publisher_url']}")
        print(f"Slot: {fixture['slot_id']}")
        print("Competing line items:")
        for item in fixture["line_items"]:
            print(f"  - {item['name']} | CPM {item['cpm']:.2f} | Weight {item['weight']}")


if __name__ == "__main__":
    main()
