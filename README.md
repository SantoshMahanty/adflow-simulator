# AdFlow Admin Simulator

AdFlow Admin Simulator is a beginner-friendly Flask + MySQL project that behaves like a small ad operations platform.

It has two connected parts:

1. An admin dashboard where you create advertisers, orders, line items, creatives, ad units, placements, and targeting rules.
2. A mock publisher website where those records are actually used to request ads, pick a winner, render the creative, and log impressions and clicks.

This means the project is not just CRUD. You can follow the full story from setup to delivery.

## 1. What This Project Is Teaching You

If you are very new, this project helps you practice these ideas in one place:

- how a Flask app is structured
- how routes, templates, and services work together
- how SQLAlchemy models represent database tables
- how login works with sessions
- how admin forms save data into MySQL
- how business rules are written in Python
- how ad-tech concepts like targeting, eligibility, auctions, impressions, and clicks work

## 2. Ad-Tech Words in Simple English

These words show up all over the project:

- `Advertiser`: the brand or client
- `Order`: a campaign under that advertiser
- `Line Item`: the delivery rules for a campaign
- `Creative`: the actual ad asset that gets shown
- `Ad Unit`: the place on the page where an ad can appear
- `Placement`: a group of ad units
- `Targeting`: rules like geo, device, page type, slot position, audience, and key-values
- `Auction`: the logic that decides which eligible line item wins
- `Impression`: logged when the ad is viewed
- `Click`: logged when the user clicks the ad

## 3. Project Structure

This is the main folder layout:

```text
adflow_admin_simulator/
|-- app/
|   |-- __init__.py
|   |-- models/
|   |-- routes/
|   |-- services/
|   |-- static/
|   `-- templates/
|-- config.py
|-- run.py
|-- seed.py
|-- seed_test_auction.py
|-- verify_test_auction_flow.py
`-- requirements.txt
```

What each top-level part does:

- `run.py`
  Starts the Flask server.
- `config.py`
  Loads environment variables like DB host, DB name, DB user, and secret key.
- `app/__init__.py`
  Creates the Flask app, connects the database, registers routes, and runs startup bootstrap logic.
- `app/models/`
  Database tables live here.
- `app/routes/`
  URL endpoints and page handling live here.
- `app/services/`
  Reusable business logic lives here.
- `app/templates/`
  HTML pages live here.
- `app/static/`
  CSS and JavaScript live here.
- `seed.py`
  Inserts demo data so the app is usable immediately.
- `seed_test_auction.py`
  Creates a clean deterministic auction fixture for learning and testing.
- `verify_test_auction_flow.py`
  Runs an end-to-end check of the auction flow in code.

## 4. Which File Is Responsible for Which Feature

This is the most important section if you are learning the codebase.

### App startup

- `run.py`
  This is the file you run with `python run.py`.
- `app/__init__.py`
  This is where the Flask app is created.
  It also:
  - loads config
  - initializes SQLAlchemy
  - registers blueprints
  - loads the logged-in user before requests
  - creates tables on startup
  - runs schema/bootstrap helpers
- `config.py`
  Builds the database connection string from `.env`.

### Login and logout

- `app/routes/auth.py`
  Handles `/auth/login` and `/auth/logout`.
- `app/services/auth.py`
  Contains helper logic for authentication and current-user lookup.
- `app/models/user.py`
  Stores admin users and password logic.
- `app/templates/auth/login.html`
  Login page UI.

### Dashboard

- `app/routes/dashboard.py`
  Handles the dashboard pages.
- `app/services/dashboard.py`
  Builds dashboard summary data.
- `app/templates/dashboard/index.html`
  Dashboard page.
- `app/templates/dashboard/settings.html`
  Settings page.

### Advertisers

- `app/routes/advertisers.py`
  Advertiser pages and form handling.
- `app/models/advertiser.py`
  Advertiser table.
- `app/templates/advertisers/`
  Advertiser UI pages.

### Orders

- `app/routes/orders.py`
  Order pages and form handling.
- `app/models/order.py`
  Order table.
- `app/templates/orders/`
  Order UI pages.

### Line items

- `app/routes/line_items.py`
  Main place for line item create, edit, detail, delete, filtering, and targeting sync.
- `app/models/line_item.py`
  Line item database table and targeting relationships.
- `app/services/eligibility.py`
  Core eligibility checks used to decide whether a line item can serve.
- `app/services/launch.py`
  Launch readiness and workflow-state helpers.
- `app/templates/line_items/`
  Line item UI pages.

If you want to understand "why did this line item pass or fail?", read these files first:

- `app/routes/line_items.py`
- `app/services/eligibility.py`

### Creatives

- `app/routes/creatives.py`
  Creative pages and form handling.
- `app/models/creative.py`
  Creative table.
- `app/templates/creatives/`
  Creative UI pages.

### Ad units and placements

- `app/routes/ad_units.py`
  Ad unit pages.
- `app/routes/placements.py`
  Placement pages.
- `app/models/ad_unit.py`
  Ad unit table.
- `app/models/placement.py`
  Placement table.
- `app/templates/ad_units/`
  Ad unit UI pages.
- `app/templates/placements/`
  Placement UI pages.

### Key-values and targeting rules

- `app/routes/key_values.py`
  Key-value management screens.
- `app/models/key_value.py`
  Key-value tables.
- `app/routes/line_items.py`
  Applies key-values to line items through targeting rules.

### Auction simulator

- `app/routes/simulator.py`
  Handles the simulator form and simulator result pages.
- `app/services/simulation.py`
  Contains the waterfall and unified auction logic used by the simulator.
- `app/templates/simulator/`
  Simulator UI pages.
- `app/models/auction.py`
  Stores saved simulation history.

### Live publisher pages

- `app/routes/publisher.py`
  Handles publisher pages, ad requests, creative preview, impression logging, and click tracking.
- `app/services/ad_server.py`
  Creates mock publisher slots, articles, placements, and helper data for the publisher site.
- `app/services/auction_engine.py`
  Runs the live request auction and stores request-level delivery data.
- `app/templates/publisher/`
  Publisher pages and ad slot partials.
- `app/static/js/publisher.js`
  Front-end code for publisher slot behavior.
- `app/models/publisher.py`
  Publisher site table.
- `app/models/delivery.py`
  Delivery, impression, click, and request tracking models.

If you want to understand "how does a page request an ad and get a winner?", read these files first:

- `app/routes/publisher.py`
- `app/services/ad_server.py`
- `app/services/auction_engine.py`

### Auction logs and diagnostics

- `app/routes/auctions.py`
  Shows stored ad requests and detailed diagnostics.
- `app/templates/auctions/`
  Auction logs UI.
- `app/services/auction_engine.py`
  Builds the request-level debug data.

### Reports

- `app/routes/reports.py`
  Reports page and CSV export.
- `app/services/reporting.py`
  Aggregates totals, summaries, failures, and export rows.
- `app/templates/reports/index.html`
  Reports page UI.

### Troubleshooting module

- `app/routes/troubleshooting.py`
  Troubleshooting issue library and troubleshooting sheet pages.
- `app/models/troubleshooting.py`
  Troubleshooting-related tables.
- `app/templates/troubleshooting/`
  Troubleshooting UI.

### Activity logging

- `app/services/activity.py`
  Logs create, update, delete, and simulation actions.
- `app/models/activity.py`
  Activity log table.

### API endpoints

- `app/routes/api.py`
  JSON endpoints for advertisers, orders, line items, creatives, line item launch, and report data.

## 5. Important Models

If you are learning the database structure, start with these:

- `app/models/user.py`
- `app/models/advertiser.py`
- `app/models/order.py`
- `app/models/line_item.py`
- `app/models/creative.py`
- `app/models/ad_unit.py`
- `app/models/placement.py`
- `app/models/key_value.py`
- `app/models/auction.py`
- `app/models/delivery.py`
- `app/models/publisher.py`
- `app/models/troubleshooting.py`

## 6. How the App Starts When You Run It

When you run:

```powershell
python run.py
```

this is what happens:

1. `run.py` imports `create_app()` from `app/__init__.py`.
2. `app/__init__.py` creates the Flask app.
3. `config.py` loads environment variables from `.env`.
4. SQLAlchemy is initialized.
5. All route blueprints are registered.
6. On startup, the app runs:
   - `db.create_all()`
   - `ensure_runtime_schema()`
   - `bootstrap_mock_publisher_inventory()`
7. The server starts on `http://127.0.0.1:5000`.

## 7. How to Run the Project for the First Time

### Step 1. Make sure you have these installed

- Python 3.11 or newer
- MySQL running locally

### Step 2. Create the database

Run this inside MySQL:

```sql
CREATE DATABASE gamsetup CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Step 3. Configure `.env`

Copy `.env.example` to `.env`.

Example values:

```text
SECRET_KEY=change-this-secret-key
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=gamsetup
DB_USER=root
DB_PASSWORD=root
```

### Step 4. Create a virtual environment

PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Command Prompt:

```cmd
python -m venv .venv
.venv\Scripts\activate
```

### Step 5. Install Python packages

```powershell
pip install -r requirements.txt
```

### Step 6. Seed demo data

```powershell
python seed.py
```

This creates demo records and the default admin user.

### Step 7. Start the server

```powershell
python run.py
```

Open this in your browser:

[http://127.0.0.1:5000](http://127.0.0.1:5000)

### Step 8. Log in

- Email: `admin@adflow.local`
- Password: `Admin@123`

## 8. Beginner Manual Testing Guide

If you want to test the app feature by feature in the browser, follow this order.

### Test 1. Login

1. Open `/auth/login`
2. Log in using the default admin account
3. Confirm the dashboard opens

Main files:

- `app/routes/auth.py`
- `app/services/auth.py`
- `app/templates/auth/login.html`

### Test 2. Create an advertiser

1. Open the Advertisers page
2. Create a new advertiser
3. Confirm it appears in the advertiser list and detail page

Main files:

- `app/routes/advertisers.py`
- `app/models/advertiser.py`
- `app/templates/advertisers/`

### Test 3. Create an order

1. Open the Orders page
2. Create an order under your advertiser
3. Make sure the dates include today

Main files:

- `app/routes/orders.py`
- `app/models/order.py`
- `app/templates/orders/`

### Test 4. Create a line item

1. Open the Line Items page
2. Create a line item under the order
3. Set:
   - status to active
   - workflow state to Live
   - matching creative size
   - matching targeting values
4. Save and open the detail page
5. Check the eligibility section

Main files:

- `app/routes/line_items.py`
- `app/services/eligibility.py`
- `app/services/launch.py`
- `app/templates/line_items/`

### Test 5. Create a creative

1. Open the Creatives page
2. Create a creative linked to the line item
3. Make sure:
   - it is active
   - approval status is approved
   - size matches the slot

Main files:

- `app/routes/creatives.py`
- `app/models/creative.py`
- `app/templates/creatives/`

### Test 6. Open publisher pages

1. Open `/publisher/home`
2. Open `/publisher/article/1`
3. Open `/publisher/category/technology`
4. Watch slots request ads

Main files:

- `app/routes/publisher.py`
- `app/services/ad_server.py`
- `app/static/js/publisher.js`
- `app/templates/publisher/`

### Test 7. Use the auction test page

Open:

`/publisher/test-auction?debug=1`

This page is useful because it isolates one slot and shows debugging information more clearly.

Main files:

- `app/routes/publisher.py`
- `app/services/test_auction_fixture.py`
- `app/templates/publisher/test_auction.html`

### Test 8. Check auction logs

1. After a publisher page requests an ad, open `/auctions/`
2. Open a request detail page
3. Confirm you can see candidate decisions, winner details, and failure reasons

Main files:

- `app/routes/auctions.py`
- `app/services/auction_engine.py`
- `app/templates/auctions/`

### Test 9. Check reports

1. Open `/reports/`
2. Change filters if needed
3. Export CSV from `/reports/export`

Main files:

- `app/routes/reports.py`
- `app/services/reporting.py`
- `app/templates/reports/index.html`

## 9. Best End-to-End Learning Flow

If you want to understand the whole product, do this:

1. Log in.
2. Create an advertiser.
3. Create an order.
4. Create a line item.
5. Create a creative.
6. Make sure the creative size and targeting match a publisher slot.
7. Open a publisher page.
8. Let the page request an ad.
9. Open auction logs.
10. Check reports.

This teaches you how admin data becomes live delivery behavior.

## 10. Automated Test and Verification Scripts

Besides manual browser testing, this repo has two useful scripts.

### `seed_test_auction.py`

Run:

```powershell
python seed_test_auction.py
```

What it does:

- creates a deterministic 5-line-item auction fixture
- creates a clean test publisher slot
- creates the admin login if missing
- prints the test page URL and seeded line items

Main files behind it:

- `seed_test_auction.py`
- `app/services/test_auction_fixture.py`

### `verify_test_auction_flow.py`

Run:

```powershell
python verify_test_auction_flow.py
```

What it checks:

- the publisher test page loads
- the slot makes a live ad request
- exactly five seeded line items are evaluated
- the expected winner is selected
- impression logging works
- click logging works
- diagnostics data is correct
- no-fill fallback works when targeting does not match

Main files behind it:

- `verify_test_auction_flow.py`
- `app/services/test_auction_fixture.py`
- `app/routes/publisher.py`
- `app/services/auction_engine.py`

## 11. Useful URLs While Learning

- `/auth/login`
- `/`
- `/line-items/`
- `/creatives/`
- `/simulator/`
- `/publisher/home`
- `/publisher/test-auction?debug=1`
- `/auctions/`
- `/reports/`

## 12. JSON/API Endpoints

These are code-driven endpoints, useful if you want to test with Postman or JavaScript later:

- `POST /advertisers`
- `POST /orders`
- `POST /line-items`
- `POST /creatives`
- `POST /launch-line-item`
- `GET /delivery/report`
- `GET /serve-ad`
- `GET /publisher/ad`

These are handled in:

- `app/routes/api.py`
- `app/routes/publisher.py`

## 13. Recommended Reading Order for a New Student

If you want to read the code without getting lost, use this order:

1. `run.py`
2. `config.py`
3. `app/__init__.py`
4. `app/models/__init__.py`
5. `app/models/user.py`
6. `app/routes/auth.py`
7. `app/routes/dashboard.py`
8. `app/routes/line_items.py`
9. `app/services/eligibility.py`
10. `app/routes/simulator.py`
11. `app/services/simulation.py`
12. `app/routes/publisher.py`
13. `app/services/ad_server.py`
14. `app/services/auction_engine.py`
15. `app/routes/reports.py`
16. `app/services/reporting.py`
17. `seed.py`
18. `verify_test_auction_flow.py`

## 14. Common Beginner Questions

### Where does the server start?

`run.py`

### Where is the Flask app created?

`app/__init__.py`

### Where are the database tables defined?

Inside `app/models/`

### Where are page URLs handled?

Inside `app/routes/`

### Where is the business logic?

Inside `app/services/`

### Where is the HTML?

Inside `app/templates/`

### Where is the CSS and JavaScript?

- `app/static/css/styles.css`
- `app/static/js/app.js`
- `app/static/js/publisher.js`

### Where is the live auction logic?

- `app/services/auction_engine.py`
- `app/services/eligibility.py`
- `app/services/simulation.py`

## 15. Notes

- This project expects a local MySQL database.
- It is built for learning and local development.
- The app uses `db.create_all()` on startup, which is okay for a learning project but not the same as a production migration system.
