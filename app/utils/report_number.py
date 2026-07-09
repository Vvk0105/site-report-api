from datetime import datetime


def generate_report_number(
    report_id: int,
) -> str:

    return f"SR-{datetime.utcnow():%Y%m%d}-{report_id:06d}"