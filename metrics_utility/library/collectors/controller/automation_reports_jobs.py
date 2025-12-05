"""
Collector for AWX/Controller jobs for automation reports.

Collects comprehensive job execution data for automation ROI reporting and analytics.
"""

from ..util import collector, copy_table, date_where


def _jobs_query(where='TRUE'):
    """
    Query to extract job execution data from AWX/Controller database.

    Maps to automation_reports.Job model with comprehensive execution details.
    Joins main_job with main_unifiedjob for complete data.
    """
    return f"""
        SELECT
            uj.id AS external_id,
            uj.name,
            uj.description,
            'job' AS type,
            j.job_type,
            uj.launch_type,
            uj.status,
            uj.started,
            uj.finished,
            uj.elapsed,
            uj.failed,
            uj.created,
            uj.modified,

            -- Relationships
            j.job_template_id,
            j.inventory_id,
            j.project_id,
            uj.organization_id,
            uj.execution_environment_id,
            uj.instance_group_id,
            uj.created_by_id,

            -- Host counts (aggregated from job_host_summary)
            COALESCE(
                (SELECT COUNT(DISTINCT host_id)
                 FROM main_jobhostsummary
                 WHERE job_id = uj.id), 0
            ) AS num_hosts,

            COALESCE(
                (SELECT SUM(changed)
                 FROM main_jobhostsummary
                 WHERE job_id = uj.id), 0
            ) AS changed_hosts_count,

            COALESCE(
                (SELECT SUM(dark)
                 FROM main_jobhostsummary
                 WHERE job_id = uj.id), 0
            ) AS dark_hosts_count,

            COALESCE(
                (SELECT SUM(failures)
                 FROM main_jobhostsummary
                 WHERE job_id = uj.id), 0
            ) AS failures_hosts_count,

            COALESCE(
                (SELECT SUM(ok)
                 FROM main_jobhostsummary
                 WHERE job_id = uj.id), 0
            ) AS ok_hosts_count,

            COALESCE(
                (SELECT SUM(processed)
                 FROM main_jobhostsummary
                 WHERE job_id = uj.id), 0
            ) AS processed_hosts_count,

            COALESCE(
                (SELECT SUM(skipped)
                 FROM main_jobhostsummary
                 WHERE job_id = uj.id), 0
            ) AS skipped_hosts_count,

            COALESCE(
                (SELECT SUM(CASE WHEN failed THEN 1 ELSE 0 END)
                 FROM main_jobhostsummary
                 WHERE job_id = uj.id), 0
            ) AS failed_hosts_count,

            COALESCE(
                (SELECT SUM(ignored)
                 FROM main_jobhostsummary
                 WHERE job_id = uj.id), 0
            ) AS ignored_hosts_count,

            COALESCE(
                (SELECT SUM(rescued)
                 FROM main_jobhostsummary
                 WHERE job_id = uj.id), 0
            ) AS rescued_hosts_count

        FROM main_job j
        JOIN main_unifiedjob uj ON j.unifiedjob_ptr_id = uj.id
        WHERE {where}
        ORDER BY uj.finished DESC NULLS LAST, uj.id DESC
    """


@collector
def automation_reports_jobs(*, db=None, since=None, until=None, output_dir=None):
    """
    Collect jobs within a date range.

    This is the primary collector for job execution data. Since job data can be
    very large, date range filtering is recommended.

    Args:
        db: Database connection
        since: Start date for collection (filters by finished date)
        until: End date for collection (filters by finished date)
        output_dir: Directory for output CSV files

    Returns:
        List of CSV file paths containing job execution data
    """
    # Default to filtering by finished date if date range provided
    if since or until:
        where = date_where('uj.finished', since, until)
    else:
        where = 'TRUE'

    query = _jobs_query(where)
    return copy_table(db=db, table='automation_reports_jobs', query=query, output_dir=output_dir)


@collector
def automation_reports_jobs_daily(*, db=None, since=None, until=None, output_dir=None):
    """
    Collect jobs finished within a specific date range.

    Optimized for daily collection - filters by finished date.

    Args:
        db: Database connection
        since: Start date for collection
        until: End date for collection
        output_dir: Directory for output CSV files

    Returns:
        List of CSV file paths containing job execution data
    """
    where = date_where('uj.finished', since, until)
    query = _jobs_query(where)
    return copy_table(db=db, table='automation_reports_jobs_daily', query=query, output_dir=output_dir)
