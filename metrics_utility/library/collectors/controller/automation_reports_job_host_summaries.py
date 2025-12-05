"""
Collector for AWX/Controller job host summaries for automation reports.

Collects per-host execution statistics for detailed job analysis.
"""

from ..util import collector, copy_table, date_where


def _job_host_summaries_query(where='TRUE'):
    """
    Query to extract job host summary data from AWX/Controller database.

    Maps to automation_reports.JobHostSummary model.
    Includes per-host execution stats for each job run.
    """
    return f"""
        SELECT
            jhs.id,
            jhs.job_id,
            jhs.host_id,
            h.name AS host_name,
            jhs.changed,
            jhs.dark,
            jhs.failures,
            jhs.ok,
            jhs.processed,
            jhs.skipped,
            jhs.failed,
            jhs.ignored,
            jhs.rescued,
            jhs.created,
            jhs.modified
        FROM main_jobhostsummary jhs
        LEFT JOIN main_host h ON jhs.host_id = h.id
        WHERE {where}
        ORDER BY jhs.job_id DESC, jhs.id ASC
    """


@collector
def automation_reports_job_host_summaries(*, db=None, since=None, until=None, output_dir=None):
    """
    Collect job host summaries within a date range.

    Since this can be a very large dataset, date range filtering is recommended.
    Filters by the job's finished date via a join.

    Args:
        db: Database connection
        since: Start date for collection (filters by job finished date)
        until: End date for collection (filters by job finished date)
        output_dir: Directory for output CSV files

    Returns:
        List of CSV file paths containing job host summary data
    """
    if since or until:
        # Join with main_unifiedjob to filter by job finished date
        where = f"""
            jhs.job_id IN (
                SELECT uj.id FROM main_unifiedjob uj
                WHERE {date_where('uj.finished', since, until)}
            )
        """
    else:
        where = 'TRUE'

    query = _job_host_summaries_query(where)
    return copy_table(db=db, table='automation_reports_job_host_summaries', query=query, output_dir=output_dir)


@collector
def automation_reports_job_host_summaries_daily(*, db=None, since=None, until=None, output_dir=None):
    """
    Collect job host summaries for jobs finished within a specific date range.

    Optimized for daily collection - filters by job finished date.

    Args:
        db: Database connection
        since: Start date for collection
        until: End date for collection
        output_dir: Directory for output CSV files

    Returns:
        List of CSV file paths containing job host summary data
    """
    where = f"""
        jhs.job_id IN (
            SELECT uj.id FROM main_unifiedjob uj
            WHERE {date_where('uj.finished', since, until)}
        )
    """
    query = _job_host_summaries_query(where)
    return copy_table(db=db, table='automation_reports_job_host_summaries_daily', query=query, output_dir=output_dir)
