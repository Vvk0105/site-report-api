from datetime import datetime


def generate_report_number(
    report_id: int,
):

    date = datetime.utcnow().strftime("%Y%m%d")

    return f"SR-{date}-{report_id:06d}"