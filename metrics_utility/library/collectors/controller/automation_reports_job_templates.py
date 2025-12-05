"""
Collector for AWX/Controller job templates for automation reports.

Collects job template data including ROI calculation fields for automation analytics.
"""

from ..util import collector, copy_table, date_where


def _job_templates_query(where='TRUE'):
    """
    Query to extract job template data from AWX/Controller database.

    Maps to automation_reports.JobTemplate model with ROI fields.
    """
    return f"""
        SELECT
            ujt.id AS external_id,
            ujt.name,
            ujt.description,
            ujt.organization_id,
            jt.project_id,
            jt.inventory_id,
            ujt.execution_environment_id,
            ujt.created,
            ujt.modified,
            -- ROI calculation fields (defaults match Django model)
            60 AS time_taken_manually_execute_minutes,
            240 AS time_taken_create_automation_minutes
        FROM main_jobtemplate jt
        JOIN main_unifiedjobtemplate ujt ON jt.unifiedjobtemplate_ptr_id = ujt.id
        WHERE {where}
        ORDER BY ujt.id ASC
    """


@collector
def automation_reports_job_templates(*, db=None, output_dir=None):
    """
    Collect all non-template job templates.

    Returns:
        List of CSV file paths containing job template data
    """
    query = _job_templates_query()
    return copy_table(db=db, table='automation_reports_job_templates', query=query, output_dir=output_dir)


@collector
def automation_reports_job_templates_daily(*, db=None, since=None, until=None, output_dir=None):
    """
    Collect job templates created or modified within a date range.

    Args:
        db: Database connection
        since: Start date for collection
        until: End date for collection
        output_dir: Directory for output CSV files

    Returns:
        List of CSV file paths containing job template data
    """
    where = f"""
        ({date_where('ujt.created', since, until)}
        OR {date_where('ujt.modified', since, until)})
    """
    query = _job_templates_query(where)
    return copy_table(db=db, table='automation_reports_job_templates_daily', query=query, output_dir=output_dir)
