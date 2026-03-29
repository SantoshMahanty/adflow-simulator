from datetime import datetime
from decimal import Decimal, InvalidOperation


def parse_date(value, default=None):
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default


def parse_int(value, default=0):
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_decimal(value, default="0.00"):
    if value in (None, ""):
        return Decimal(default)
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def split_csv_values(value):
    if not value:
        return []
    return [item.strip().lower() for item in value.split(",") if item.strip()]
