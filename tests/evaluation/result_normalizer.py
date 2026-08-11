from datetime import date, datetime
from decimal import Decimal


def normalize_value(value):

    if isinstance(value, Decimal):
        return round(float(value), 6)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, float):
        return round(value, 6)

    return value


def normalize_rows(rows: list[dict]):

    normalized = []

    for row in rows:

        normalized_row = {
            str(key): normalize_value(value)
            for key, value in row.items()
        }

        normalized.append(normalized_row)

    # ---------------------------------------------------------
    # Normalize dictionary key ordering.
    #
    # This ensures:
    #
    # {"product_name": "...", "category_name": "..."}
    #
    # equals:
    #
    # {"category_name": "...", "product_name": "..."}
    #
    # ---------------------------------------------------------

    normalized = [
        dict(sorted(row.items()))
        for row in normalized
    ]

    return normalized