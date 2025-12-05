"""
Collector for AWX/Controller organizations for automation reports.

Collects organization data to support automation ROI reporting and analytics.
"""

from ..util import collector, copy_table, date_where


def _organizations_query(where='TRUE'):
    """
    Query to extract organization data from AWX/Controller database.

    Maps to automation_reports.Organization model.
    """
    return f"""
        SELECT
            org.id AS external_id,
            org.name,
            org.description,
            org.created,
            org.modified
        FROM main_organization org
        WHERE {where}
        ORDER BY org.id ASC
    """


@collector
def automation_reports_organizations(*, db=None, output_dir=None):
    """
    Collect all non-template organizations.

    Returns:
        List of CSV file paths containing organization data
    """
    query = _organizations_query()
    return copy_table(db=db, table='automation_reports_organizations', query=query, output_dir=output_dir)


@collector
def automation_reports_organizations_daily(*, db=None, since=None, until=None, output_dir=None):
    """
    Collect organizations created or modified within a date range.

    Args:
        db: Database connection
        since: Start date for collection
        until: End date for collection
        output_dir: Directory for output CSV files

    Returns:
        List of CSV file paths containing organization data
    """
    where = f"""
        ({date_where('org.created', since, until)}
        OR {date_where('org.modified', since, until)})
    """
    query = _organizations_query(where)
    return copy_table(db=db, table='automation_reports_organizations_daily', query=query, output_dir=output_dir)
