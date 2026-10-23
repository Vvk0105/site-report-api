from datetime import datetime, timezone


def generate_report_number(
    report_id: int,
) -> str:

    return f"SR-{datetime.now(timezone.utc):%Y%m%d}-{report_id:06d}"
