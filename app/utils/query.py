from sqlalchemy import asc, desc


def safe_sort_column(model, name: str, allowed: set[str], default: str):
    """
    Map a client supplied sort key onto a whitelisted model column.
    Unknown keys fall back to the default instead of touching arbitrary attributes.
    """
    column_name = name if name in allowed else default
    return getattr(model, column_name)


def apply_order(query, column, order: str):
    return query.order_by(asc(column) if order == "asc" else desc(column))


def escape_like(value: str) -> str:
    """Escape LIKE wildcards so user input is matched literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
