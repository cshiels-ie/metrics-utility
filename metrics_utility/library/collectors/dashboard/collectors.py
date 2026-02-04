"""Collector functions for dashboard metrics.

These collectors use the @register decorator pattern from metrics-utility to
define data collection functions that can be called by metrics-service.

Each collector:
1. Executes SQL queries against the AWX database
2. Processes results to match automation-reports data format
3. Returns JSON-serializable data structures
"""

from datetime import datetime, timezone
from typing import Any

from metrics_utility.base import register

from .queries import (
    format_elapsed_time,
    get_job_template_summary_query,
    get_top_projects_query,
    get_top_users_query,
)


@register('dashboard_job_templates', '1.0', format='json', description='Job template summary for automation-reports dashboard')
def dashboard_job_templates(since: datetime, until: datetime, db, **kwargs) -> dict[str, Any]:
    """
    Collect job template summary data for the dashboard.

    This collector gathers comprehensive job execution metrics per template,
    including run counts, success/failure rates, elapsed time, and cost calculations.

    Args:
        since: Start of date range (inclusive)
        until: End of date range (exclusive)
        db: Database connection
        **kwargs: Additional parameters

    Returns:
        dict with keys:
            - job_templates: List of template data matching Report interface
            - count: Total number of templates
            - timestamp: Collection time (ISO format)

    Output format matches automation-reports Report TypeScript interface:
        {
            name: string,
            runs: number,
            elapsed: number (in seconds),
            elapsed_str: string,
            cluster: number,
            num_hosts: number,
            time_taken_manually_execute_minutes: number,
            time_taken_create_automation_minutes: number,
            successful_runs: number,
            failed_runs: number,
            automated_costs: string,
            manual_costs: string,
            savings: string
        }
    """
    query = get_job_template_summary_query(since, until)

    with db.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        results = []

        for row in cursor.fetchall():
            template_data = dict(zip(columns, row))

            # Calculate derived fields
            # Convert to float to avoid Decimal/float type mixing issues
            elapsed_seconds = float(template_data.get('elapsed', 0) or 0)
            template_data['elapsed_str'] = format_elapsed_time(elapsed_seconds)

            # Add time estimate fields (defaults since AWX doesn't store these)
            # These are used for cost calculations
            manual_time_mins = 60  # Default: 60 minutes to do manually
            auto_time_mins = 30  # Default: 30 minutes to create automation

            template_data['time_taken_manually_execute_minutes'] = manual_time_mins
            template_data['time_taken_create_automation_minutes'] = auto_time_mins

            # Cost calculations (hourly rate: $50/hour labor)
            # Convert to float to handle potential Decimal types from database
            runs = float(template_data.get('runs', 0))

            hourly_rate = 50.0

            # Manual cost: time per execution * number of runs * hourly rate
            manual_cost = (manual_time_mins * runs * hourly_rate) / 60

            # Automated cost: one-time setup cost + operational costs
            # Setup cost: time to create automation * hourly rate
            # Operational cost: actual elapsed time * infrastructure rate ($10/hour)
            setup_cost = (auto_time_mins * hourly_rate) / 60
            operational_cost = (elapsed_seconds / 3600) * 10
            auto_cost = setup_cost + operational_cost

            # Calculate savings
            savings = manual_cost - auto_cost

            # Store as numeric values (frontend will format with currency symbols)
            template_data['automated_costs'] = round(auto_cost, 2)
            template_data['manual_costs'] = round(manual_cost, 2)
            template_data['savings'] = round(savings, 2)

            # Ensure numeric fields are proper types (not Decimal)
            template_data['runs'] = int(runs)
            template_data['elapsed'] = elapsed_seconds
            template_data['num_hosts'] = int(template_data.get('num_hosts', 0) or 0)
            template_data['successful_runs'] = int(template_data.get('successful_runs', 0) or 0)
            template_data['failed_runs'] = int(template_data.get('failed_runs', 0) or 0)
            template_data['cluster'] = int(template_data.get('cluster', 1) or 1)

            results.append(template_data)

    return {'job_templates': results, 'count': len(results), 'timestamp': datetime.now(timezone.utc).isoformat()}


@register('dashboard_top_projects', '1.0', format='json', description='Top projects by job count for automation-reports dashboard')
def dashboard_top_projects(since: datetime, until: datetime, db, limit: int = 10, **kwargs) -> dict[str, Any]:
    """
    Collect top projects by job execution count.

    Args:
        since: Start of date range (inclusive)
        until: End of date range (exclusive)
        db: Database connection
        limit: Maximum number of projects to return (default: 10)
        **kwargs: Additional parameters

    Returns:
        dict with keys:
            - top_projects: List of project data
            - count: Number of projects returned
            - timestamp: Collection time (ISO format)

    Output format:
        {
            project_id: number,
            project_name: string,
            job_count: number
        }
    """
    query = get_top_projects_query(since, until, limit)

    with db.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        results = []

        for row in cursor.fetchall():
            project_data = dict(zip(columns, row))
            results.append(project_data)

    return {'top_projects': results, 'count': len(results), 'timestamp': datetime.now(timezone.utc).isoformat()}


@register('dashboard_top_users', '1.0', format='json', description='Top users by job execution count for automation-reports dashboard')
def dashboard_top_users(since: datetime, until: datetime, db, limit: int = 10, **kwargs) -> dict[str, Any]:
    """
    Collect top users by job execution count.

    Args:
        since: Start of date range (inclusive)
        until: End of date range (exclusive)
        db: Database connection
        limit: Maximum number of users to return (default: 10)
        **kwargs: Additional parameters

    Returns:
        dict with keys:
            - top_users: List of user data
            - count: Number of users returned
            - timestamp: Collection time (ISO format)

    Output format:
        {
            user_id: number,
            username: string,
            job_count: number
        }
    """
    query = get_top_users_query(since, until, limit)

    with db.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        results = []

        for row in cursor.fetchall():
            user_data = dict(zip(columns, row))
            results.append(user_data)

    return {'top_users': results, 'count': len(results), 'timestamp': datetime.now(timezone.utc).isoformat()}
