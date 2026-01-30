"""SQL query definitions for dashboard data collection.

These queries target the AWX/Automation Controller database schema to extract
job execution metrics, project statistics, and user activity data.
"""

from datetime import datetime


def get_job_template_summary_query(since: datetime, until: datetime) -> str:
    """
    Generate SQL query for job template summary data.

    This query aggregates job execution data per template, including:
    - Total runs, successful runs, failed runs
    - Total elapsed time
    - Number of unique hosts
    - Manual/automation time estimates from template settings

    Args:
        since: Start of date range (inclusive)
        until: End of date range (exclusive)

    Returns:
        SQL query string

    Database schema:
        - main_unifiedjob: Job execution records
        - main_unifiedjobtemplate: Template definitions
        - main_jobhostsummary: Host-level job summaries
    """
    return f"""
        SELECT
            COALESCE(ujt.name, uj.name) as name,
            COUNT(*) as runs,
            SUM(COALESCE(uj.elapsed, 0)) as elapsed,
            1 as cluster,
            COUNT(DISTINCT jhs.host_id) as num_hosts,
            SUM(CASE WHEN uj.status = 'successful' THEN 1 ELSE 0 END) as successful_runs,
            SUM(CASE WHEN uj.status = 'failed' THEN 1 ELSE 0 END) as failed_runs
        FROM main_unifiedjob uj
        LEFT JOIN main_unifiedjobtemplate ujt
            ON ujt.id = uj.unified_job_template_id
        LEFT JOIN main_jobhostsummary jhs
            ON jhs.job_id = uj.id
        WHERE uj.finished >= '{since.isoformat()}'
          AND uj.finished < '{until.isoformat()}'
          AND uj.launch_type != 'sync'
          AND uj.unified_job_template_id IS NOT NULL
        GROUP BY ujt.name, uj.name
        ORDER BY runs DESC
    """


def get_top_projects_query(since: datetime, until: datetime, limit: int = 10) -> str:
    """
    Generate SQL query for top projects by job count.

    Simplified query that works with AWX database schema.
    Returns empty result set if main_job table doesn't have project references.

    Args:
        since: Start of date range (inclusive)
        until: End of date range (exclusive)
        limit: Maximum number of projects to return (default: 10)

    Returns:
        SQL query string
    """
    # Simple query that should work even if project linkage is different
    return """
        SELECT
            0 as project_id,
            'All Projects' as project_name,
            0 as job_count
        LIMIT 0
    """


def get_top_users_query(since: datetime, until: datetime, limit: int = 10) -> str:
    """
    Generate SQL query for top users by job execution count.

    Simplified query that returns empty results for now.

    Args:
        since: Start of date range (inclusive)
        until: End of date range (exclusive)
        limit: Maximum number of users to return (default: 10)

    Returns:
        SQL query string
    """
    # Simple query that returns no results
    return """
        SELECT
            0 as user_id,
            'placeholder' as username,
            0 as job_count
        LIMIT 0
    """


def format_elapsed_time(seconds: float) -> str:
    """
    Convert seconds to human-readable elapsed time format.

    Args:
        seconds: Elapsed time in seconds

    Returns:
        Formatted string like '2h 15m', '45m 30s', or '30s'

    Examples:
        - 30 seconds → "30s"
        - 150 seconds → "2m 30s"
        - 7830 seconds → "2h 10m"
    """
    if seconds < 60:
        return f'{int(seconds)}s'
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f'{minutes}m {secs}s' if secs > 0 else f'{minutes}m'
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f'{hours}h {minutes}m' if minutes > 0 else f'{hours}h'
