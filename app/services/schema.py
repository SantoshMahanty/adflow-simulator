from sqlalchemy import inspect, text

from ..models import TABLE_PREFIX, db


def _append_missing_column(statements, table_name, existing_columns, column_name, ddl):
    if column_name not in existing_columns:
        statements.append(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))


def ensure_runtime_schema():
    inspector = inspect(db.engine)
    dialect = db.engine.dialect.name
    line_item_table = f"{TABLE_PREFIX}line_items"
    if not inspector.has_table(line_item_table):
        return

    statements = []

    line_item_columns = {column["name"] for column in inspector.get_columns(line_item_table)}
    _append_missing_column(statements, line_item_table, line_item_columns, "delivery_weight", "INT NOT NULL DEFAULT 100")
    _append_missing_column(statements, line_item_table, line_item_columns, "workflow_state", "VARCHAR(50) NOT NULL DEFAULT 'Draft'")
    _append_missing_column(statements, line_item_table, line_item_columns, "budget_amount", "NUMERIC(12,2) NOT NULL DEFAULT 0.00")
    _append_missing_column(statements, line_item_table, line_item_columns, "spent_amount", "NUMERIC(12,2) NOT NULL DEFAULT 0.00")
    _append_missing_column(statements, line_item_table, line_item_columns, "daily_impression_cap", "INT NOT NULL DEFAULT 0")
    _append_missing_column(statements, line_item_table, line_item_columns, "daily_spend_cap", "NUMERIC(12,2) NOT NULL DEFAULT 0.00")
    _append_missing_column(statements, line_item_table, line_item_columns, "launch_ready", "BOOLEAN NOT NULL DEFAULT 0")
    _append_missing_column(statements, line_item_table, line_item_columns, "last_launched_at", "DATETIME NULL")

    order_table = f"{TABLE_PREFIX}orders"
    if inspector.has_table(order_table):
        order_columns = {column["name"] for column in inspector.get_columns(order_table)}
        _append_missing_column(statements, order_table, order_columns, "workflow_state", "VARCHAR(50) NOT NULL DEFAULT 'Draft'")
        _append_missing_column(statements, order_table, order_columns, "budget_amount", "NUMERIC(12,2) NOT NULL DEFAULT 0.00")
        _append_missing_column(statements, order_table, order_columns, "spent_amount", "NUMERIC(12,2) NOT NULL DEFAULT 0.00")

    creative_table = f"{TABLE_PREFIX}creatives"
    if inspector.has_table(creative_table):
        creative_columns = {column["name"] for column in inspector.get_columns(creative_table)}
        _append_missing_column(statements, creative_table, creative_columns, "asset_url", "VARCHAR(255) NULL")

    ad_unit_table = f"{TABLE_PREFIX}ad_units"
    if inspector.has_table(ad_unit_table):
        ad_unit_columns = {column["name"] for column in inspector.get_columns(ad_unit_table)}
        _append_missing_column(statements, ad_unit_table, ad_unit_columns, "ad_unit_code", "VARCHAR(255) NULL")
        _append_missing_column(statements, ad_unit_table, ad_unit_columns, "slot_name", "VARCHAR(120) NULL")
        _append_missing_column(statements, ad_unit_table, ad_unit_columns, "publisher_site_id", "INT NULL")

    impression_table = f"{TABLE_PREFIX}impressions"
    if inspector.has_table(impression_table):
        impression_columns = {column["name"] for column in inspector.get_columns(impression_table)}
        _append_missing_column(statements, impression_table, impression_columns, "request_id", "INT NULL")
        _append_missing_column(statements, impression_table, impression_columns, "revenue", "NUMERIC(10,4) NOT NULL DEFAULT 0.0000")
        _append_missing_column(statements, impression_table, impression_columns, "cpm", "NUMERIC(10,2) NOT NULL DEFAULT 0.00")

    click_table = f"{TABLE_PREFIX}clicks"
    if inspector.has_table(click_table):
        click_columns = {column["name"] for column in inspector.get_columns(click_table)}
        _append_missing_column(statements, click_table, click_columns, "request_id", "INT NULL")
        _append_missing_column(statements, click_table, click_columns, "revenue", "NUMERIC(10,4) NOT NULL DEFAULT 0.0000")
        _append_missing_column(statements, click_table, click_columns, "cpm", "NUMERIC(10,2) NOT NULL DEFAULT 0.00")

    if not statements:
        return

    with db.engine.begin() as connection:
        for statement in statements:
            connection.execute(statement)

        # Backfill new ad unit metadata from the legacy path column.
        if inspector.has_table(ad_unit_table):
            connection.execute(text(f"UPDATE {ad_unit_table} SET ad_unit_code = path WHERE ad_unit_code IS NULL"))
            if dialect == "mysql":
                connection.execute(
                    text(
                        f"UPDATE {ad_unit_table} "
                        "SET slot_name = CASE "
                        "WHEN slot_name IS NULL OR slot_name = '' THEN SUBSTRING_INDEX(path, '/', -1) "
                        "ELSE slot_name END"
                    )
                )
            else:
                connection.execute(
                    text(
                        f"UPDATE {ad_unit_table} "
                        "SET slot_name = CASE "
                        "WHEN slot_name IS NULL OR slot_name = '' THEN path "
                        "ELSE slot_name END"
                    )
                )
