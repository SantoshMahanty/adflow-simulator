# AdFlow Admin Simulator

AdFlow Admin Simulator is a student-friendly Flask project that mimics a simplified ad operations platform, inspired by tools like Google Ad Manager (GAM) and DV360.

It is useful for learning how ad tech platforms are structured, how admin dashboards are organized, and how auction or eligibility logic can be modeled in code.

## What Students Can Learn

This project is a good practice app for understanding:

- Flask application structure with blueprints
- SQLAlchemy models and database relationships
- Jinja template rendering
- CRUD flows for admin panels
- Authentication with session-based login
- Ad tech concepts such as advertisers, orders, line items, creatives, ad units, placements, targeting, and auctions
- Business-rule evaluation in Python

## Project Features

- Dashboard overview
- Advertiser, order, line item, creative, ad unit, and placement management
- Key-value targeting setup
- Waterfall auction simulation
- Unified auction simulation
- Troubleshooting issues library
- Internal troubleshooting sheet with CSV export
- Reporting views

## Tech Stack

- Python
- Flask
- MySQL
- SQLAlchemy
- Jinja2
- HTML, CSS, and Vanilla JavaScript

## Python Packages Used

The main packages listed in `requirements.txt` are:

- `Flask==3.1.0`
  Main web framework used to build routes, handle requests, manage sessions, and render templates.

- `Flask-SQLAlchemy==3.1.1`
  Adds SQLAlchemy integration to Flask. It is used for defining models, relationships, and database queries.

- `PyMySQL==1.1.1`
  MySQL database driver used by SQLAlchemy to connect the Flask app to MySQL.

- `python-dotenv==1.0.1`
  Loads values from `.env` into environment variables so database credentials and secrets do not need to be hardcoded.

## What Each Package Does in This Project

- `Flask`
  Runs the application server, connects URLs to Python functions, supports sessions for login, and renders the Jinja HTML templates.

- `Flask-SQLAlchemy`
  Manages tables like advertisers, orders, line items, creatives, ad units, placements, troubleshooting records, and simulation history.

- `PyMySQL`
  Makes the MySQL connection string in `config.py` work with SQLAlchemy.

- `python-dotenv`
  Reads values such as `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and `SECRET_KEY` from the `.env` file during startup.

## Project Structure

```text
adflow_admin_simulator/
  app/
    models/        # Database models
    routes/        # Flask blueprints and page routes
    services/      # Business logic such as eligibility and simulation
    static/        # CSS and JavaScript
    templates/     # Jinja HTML templates
  config.py        # App configuration
  run.py           # App entry point
  seed.py          # Demo data loader
  requirements.txt # Python dependencies
  README.md
```

## Application Packages and Their Functionalities

The `app/` folder is the main package of the project. It is split into smaller packages so the code stays organized.

### `app/__init__.py`

This is the Flask app factory.

It is responsible for:

- creating the Flask application
- loading config values
- initializing the database
- registering all blueprints
- loading the logged-in user before each request
- registering error pages

### `app/models/`

This package contains the database schema using SQLAlchemy models.

Important models:

- `user.py`
  Stores admin users and supports login/password checking.

- `advertiser.py`
  Represents the advertiser or client.

- `order.py`
  Represents a campaign order under an advertiser.

- `line_item.py`
  Stores delivery logic such as priority, CPM, targeting, dates, size, and status.

- `creative.py`
  Stores ad creative details such as format, size, approval status, and activity state.

- `ad_unit.py`
  Represents ad inventory locations where ads can serve.

- `placement.py`
  Groups multiple ad units together.

- `key_value.py`
  Stores key-value targeting configuration and line item targeting rules.

- `auction.py`
  Stores saved auction simulation runs and winners.

- `troubleshooting.py`
  Stores troubleshooting issue templates and troubleshooting sheet rows.

- `activity.py`
  Stores activity log events like create, update, delete, and simulation actions.

### `app/routes/`

This package contains Flask blueprints and page-level request handling.

Important route modules:

- `auth.py`
  Login and logout flows.

- `dashboard.py`
  Home dashboard and settings page.

- `advertisers.py`
  Advertiser listing, detail pages, and form actions.

- `orders.py`
  Order listing, creation, editing, and detail views.

- `line_items.py`
  Line item listing, filters, create/edit/delete actions, and detail evaluation.

- `creatives.py`
  Creative management flows.

- `ad_units.py`
  Ad unit creation and listing.

- `placements.py`
  Placement creation and inventory grouping.

- `key_values.py`
  Key-value setup for targeting.

- `simulator.py`
  Auction simulator form, simulation execution, and simulation history.

- `troubleshooting.py`
  Troubleshooting issue library and troubleshooting sheet workflows.

- `reports.py`
  Reporting dashboard that summarizes delivery, simulations, and issue categories.

### `app/services/`

This package contains reusable business logic that is separate from the route handlers.

Important service modules:

- `auth.py`
  Authentication helpers and `login_required`.

- `dashboard.py`
  Dashboard summary calculations.

- `eligibility.py`
  Core business rules for checking whether a line item is eligible to serve.

- `simulation.py`
  Waterfall and unified auction logic.

- `reporting.py`
  Reporting aggregation logic.

- `activity.py`
  Logging helper for activity records.

- `helpers.py`
  Shared parsing helpers such as integer, decimal, and date conversion.

### `app/templates/`

Contains all Jinja HTML templates used to render pages.

Main template groups:

- `auth/`
- `dashboard/`
- `advertisers/`
- `orders/`
- `line_items/`
- `creatives/`
- `ad_units/`
- `placements/`
- `key_values/`
- `simulator/`
- `troubleshooting/`
- `reports/`
- `partials/`
- `errors/`

### `app/static/`

Contains front-end assets:

- `css/styles.css`
  Main styling for the dashboard UI.

- `js/app.js`
  Front-end interactions and page behavior.

### Top-level Files

- `config.py`
  Loads environment variables and database configuration.

- `run.py`
  Starts the Flask app.

- `seed.py`
  Creates tables and inserts demo data for learning and testing.

- `requirements.txt`
  Lists Python package dependencies.

## Before You Start

Make sure you have:

- Python 3.11+ installed
- MySQL installed and running
- A database user that can create and update tables

## Create the Database

Run this in MySQL:

```sql
CREATE DATABASE gamsetup CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## Environment Variables

The project includes a local `.env` file and `.env.example`.

Default local settings:

```text
DB_USER=root
DB_PASSWORD=root
DB_NAME=gamsetup
```

If your MySQL setup is different, update the `.env` file.

## Installation

1. Create a virtual environment:

```bash
python -m venv .venv
```

2. Activate it:

Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```bash
.venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Seed the database with demo data:

```bash
python seed.py
```

## Run the App

Start the Flask server:

```bash
python run.py
```

Then open:

[http://127.0.0.1:5000](http://127.0.0.1:5000)

## Default Login

- Email: `admin@adflow.local`
- Password: `Admin@123`

## How the Data Model Works

The app roughly follows this ad-tech flow:

1. An `Advertiser` represents the client or brand.
2. An `Order` groups campaign work for that advertiser.
3. A `Line Item` defines delivery rules such as dates, pricing, targeting, and priority.
4. A `Creative` is the ad asset that can serve for a line item.
5. An `Ad Unit` represents inventory on the site or app.
6. A `Placement` groups ad units together.
7. The simulator checks which line items are eligible for a given request and decides a winner.

## Available Features

Below is a more detailed list of what students can explore inside the app.

### 1. Authentication

- Admin login page
- Session-based user authentication
- Logout support
- Route protection using `login_required`

### 2. Dashboard

- Summary cards and overview data
- Quick navigation into different admin areas
- Settings view with high-level counts

### 3. Advertiser Management

- Create advertisers
- View advertiser details
- Track advertiser status and vertical
- See related orders and line items

### 4. Order Management

- Create and edit orders
- Connect orders to advertisers
- Set order-level date ranges and status
- View order details

### 5. Line Item Management

- Create, edit, delete, and view line items
- Set line item priority and type
- Configure CPM and delivery goals
- Define start and end dates
- Set size, geo, device, and audience targeting
- Attach key-value targeting
- Assign ad unit targeting
- Check line item eligibility on detail and list pages
- Filter line items by advertiser, type, status, date, geo, and device

### 6. Creative Management

- Create and edit creatives
- Link creatives to line items
- Store format, size, approval status, and destination URL
- Mark creatives active or inactive

### 7. Inventory Management

- Create and list ad units
- Define inventory paths
- Group ad units into placements
- View how placements map to ad inventory

### 8. Targeting Setup

- Create key-value keys
- Create key-value values
- Attach key-value rules to line items
- Simulate request matching based on request metadata

### 9. Auction Simulator

- Run a waterfall simulation
- Run a unified auction simulation
- Input request context such as ad unit, geo, device, audience, size, and key-values
- View candidate demand
- Inspect eligibility outcomes
- See the winner and rejection reasons
- Save simulation history to the database

### 10. Troubleshooting Module

- Browse common issue types
- Maintain a troubleshooting sheet
- Use stored troubleshooting records for learning and review
- Export troubleshooting sheet data as CSV

### 11. Reporting

- View aggregate counts across advertisers, orders, line items, and simulations
- See line item status summaries
- Review issue category distribution
- Review advertiser activity summaries
- Analyze simulation outcomes and failure reasons

### 12. Activity Logging

- Records important actions in the app
- Useful for understanding admin workflows and audit-style tracking

## Important Files for Students

- `app/__init__.py`: Flask app factory and blueprint registration
- `app/models/`: SQLAlchemy models
- `app/routes/`: Page handlers and form processing
- `app/services/eligibility.py`: Line item eligibility logic
- `app/services/simulation.py`: Waterfall and unified auction logic
- `seed.py`: Demo dataset creation

## Suggested Learning Path

If you are studying this project for practice, a good reading order is:

1. `run.py`
2. `app/__init__.py`
3. `config.py`
4. `app/models/`
5. `app/routes/auth.py`
6. `app/routes/dashboard.py`
7. `app/routes/line_items.py`
8. `app/services/eligibility.py`
9. `app/services/simulation.py`
10. `seed.py`

## Notes

- `seed.py` is idempotent, which means you can run it again without dropping the full database.
- App tables use the `adflow_` prefix so they can live inside a shared database.
- The app uses `db.create_all()` for local setup instead of migrations.
- Simulation runs are saved in the `adflow_auction_simulations` table.

## Possible Student Improvements

Good next steps if you want to practice enhancing the project:

- Add form validation with Flask-WTF
- Add CSRF protection
- Add pagination to large list pages
- Add pytest tests for eligibility and simulation logic
- Improve filtering and reporting
- Make simulator date/time behavior fully configurable
