"""Parsing helpers for the IPQC daily report."""

from datetime import datetime

from deapp.models.extracted_data import ProductionActivity, ReportExtractedData, ExtractedData
from deapp.parsers.utils import (
    extract_html_tables,
    extract_report_date_and_shift,
    matrix_to_records,
    normalize_report_table,
    record_to_production_activity,
    get_line_and_personnel,
)


FIELD_BY_HEADER = {
    "STAGE": "stage",
    "PRODUCT NAME": "product_name",
    "ITEM NAME": "product_name",
    "BATCH NO": "batch_no",
    "NOS": "quantity",
    "START": "start_time",
    "START TIME": "start_time",
    "END": "end_time",
    "END TIME": "end_time",
    "IDLE": "idle_time",
    "STATUS": "status",
    "CHALLENGES": "challenges",
    "ACTION TAKEN": "action_taken_remarks",
    "REMARKS": "action_taken_remarks",
}

def parse_production_activities(
    mail_content: str,
    *,
    subject: str | None = None,
    received_at: datetime | None = None,
) -> ReportExtractedData:
    """Extract activity rows from every table in an IPQC email."""

    extracted_production_data: list[ExtractedData] = []

    for table in extract_html_tables(mail_content):
        activities: list[ProductionActivity] = []

        line, personnel = get_line_and_personnel(table)

        print(line)
        print(personnel)

        matrix = normalize_report_table(table)
        records = matrix_to_records(matrix)
        activities.extend(
            record_to_production_activity(record, FIELD_BY_HEADER)
            for record in records
        )

        extracted_production_data.append(
            ExtractedData(
                production_line= line,
                personnels_responsible=personnel,
                activities=activities
            )
        )

    report_date, shift = extract_report_date_and_shift(
        mail_content,
        subject=subject,
        received_at=received_at,
    )



    return ReportExtractedData(
        date_received=received_at.date().isoformat() if received_at else None,
        report_date=report_date.isoformat() if report_date else None,
        shift=shift or None,
        data=extracted_production_data,
        received_at=received_at,
    )
