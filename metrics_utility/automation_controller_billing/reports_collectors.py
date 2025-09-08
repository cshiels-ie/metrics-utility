"""
Reports/Use-cases collector module for AWX Automation Controller metrics.

This module contains collectors that return JSON data for various reporting
use cases instead of CSV data, providing structured data for analysis and
reporting.
"""

from django.db import connection
from django.utils.translation import gettext_lazy as _

from metrics_utility.base import register


def _execute_query(query, params=None):
    """Execute a database query and return results as list of dicts."""
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


@register('config', '1.0', description=_('Reports configuration'), config=True)
def config(since, **kwargs):
    """Configuration collector for reports module."""
    return {
        'version': '1.0',
        'module': 'reports_collectors',
        'description': 'JSON-based reporting collectors for AWX metrics',
    }


@register(
    'active_clusters_count',
    '1.0',
    format='json',
    description=_('Active number of clusters'),
)
def active_clusters_count(since, until, **kwargs):
    """
    Count of active clusters - determined by recent job activity.
    A cluster is considered active if it has had job activity in the given
    time period.
    """
    query = """
        SELECT COUNT(DISTINCT controller_node) as active_clusters
        FROM main_unifiedjob
        WHERE controller_node IS NOT NULL
        AND controller_node != ''
        AND created >= %s AND created < %s
    """

    result = _execute_query(query, [since, until])
    return {
        'active_clusters': result[0]['active_clusters'] if result else 0,
        'period_start': since.isoformat(),
        'period_end': until.isoformat(),
    }


@register(
    'active_clusters_by_controller_version',
    '1.0',
    format='json',
    description=_('Active clusters by controller version'),
)
def active_clusters_by_controller_version(since, until, **kwargs):
    """
    Count of active clusters grouped by controller version.
    Uses the ansible_version field from unified jobs as a proxy for
    controller version.
    """
    query = """
        SELECT
            ansible_version,
            COUNT(DISTINCT controller_node) as cluster_count
        FROM main_unifiedjob
        WHERE controller_node IS NOT NULL
        AND controller_node != ''
        AND ansible_version IS NOT NULL
        AND ansible_version != ''
        AND created >= %s AND created < %s
        GROUP BY ansible_version
        ORDER BY cluster_count DESC
    """

    result = _execute_query(query, [since, until])
    return {
        'clusters_by_version': result,
        'period_start': since.isoformat(),
        'period_end': until.isoformat(),
    }


@register(
    'total_modules_automated',
    '1.0',
    format='json',
    description=_('Total number of modules automated'),
)
def total_modules_automated(since, until, **kwargs):
    """
    Total count of unique modules used across all jobs.
    Extracts module information from job events.
    """
    query = """
        SELECT COUNT(DISTINCT
            CASE
                WHEN event_data::jsonb ? 'task_action'
                THEN event_data::jsonb->>'task_action'
                WHEN event_data::jsonb ? 'resolved_action'
                THEN event_data::jsonb->>'resolved_action'
                ELSE NULL
            END
        ) as total_modules
        FROM main_jobevent
        WHERE created >= %s AND created < %s
        AND event = 'runner_on_ok'
        AND (
            (event_data::jsonb ? 'task_action' AND
             event_data::jsonb->>'task_action' != '')
            OR (event_data::jsonb ? 'resolved_action' AND
                event_data::jsonb->>'resolved_action' != '')
        )
    """

    result = _execute_query(query, [since, until])
    return {
        'total_modules_automated': (result[0]['total_modules'] if result else 0),
        'period_start': since.isoformat(),
        'period_end': until.isoformat(),
    }


@register(
    'job_duration_stats_by_template',
    '1.0',
    format='json',
    description=_('Job duration statistics by template'),
)
def job_duration_stats_by_template(since, until, **kwargs):
    """
    Job duration statistics (average, min, max, total) grouped by template.
    """
    query = """
        SELECT
            ujt.name as template_name,
            ujt.id as template_id,
            COUNT(*) as job_count,
            AVG(uj.elapsed) as avg_duration_seconds,
            MIN(uj.elapsed) as min_duration_seconds,
            MAX(uj.elapsed) as max_duration_seconds,
            SUM(uj.elapsed) as total_duration_seconds,
            AVG(uj.elapsed) / 60.0 as avg_duration_minutes,
            MIN(uj.elapsed) / 60.0 as min_duration_minutes,
            MAX(uj.elapsed) / 60.0 as max_duration_minutes,
            SUM(uj.elapsed) / 60.0 as total_duration_minutes
        FROM main_unifiedjob uj
        JOIN main_unifiedjobtemplate ujt
            ON uj.unified_job_template_id = ujt.id
        WHERE uj.created >= %s AND uj.created < %s
        AND uj.elapsed IS NOT NULL
        AND uj.status IN ('successful', 'failed')
        GROUP BY ujt.id, ujt.name
        ORDER BY job_count DESC
    """

    result = _execute_query(query, [since, until])
    return {
        'job_duration_stats': result,
        'period_start': since.isoformat(),
        'period_end': until.isoformat(),
    }


@register(
    'avg_tasks_by_template',
    '1.0',
    format='json',
    description=_('Average tasks by template'),
)
def avg_tasks_by_template(since, until, **kwargs):
    """
    Average number of tasks executed per job, grouped by template.
    """
    query = """
        SELECT
            ujt.name as template_name,
            ujt.id as template_id,
            COUNT(DISTINCT uj.id) as job_count,
            COUNT(je.id) as total_tasks,
            AVG(task_counts.task_count) as avg_tasks_per_job
        FROM main_unifiedjob uj
        JOIN main_unifiedjobtemplate ujt
            ON uj.unified_job_template_id = ujt.id
        LEFT JOIN main_jobevent je ON uj.id = je.job_id
        LEFT JOIN (
            SELECT
                job_id,
                COUNT(*) as task_count
            FROM main_jobevent
            WHERE event = 'runner_on_ok'
            GROUP BY job_id
        ) task_counts ON uj.id = task_counts.job_id
        WHERE uj.created >= %s AND uj.created < %s
        AND uj.status IN ('successful', 'failed')
        GROUP BY ujt.id, ujt.name
        HAVING COUNT(DISTINCT uj.id) > 0
        ORDER BY avg_tasks_per_job DESC
    """

    result = _execute_query(query, [since, until])
    return {
        'avg_tasks_by_template': result,
        'period_start': since.isoformat(),
        'period_end': until.isoformat(),
    }


@register(
    'job_execution_stats',
    '1.0',
    format='json',
    description=_('Job execution statistics'),
)
def job_execution_stats(since, until, **kwargs):
    """
    Job execution statistics including success/failure counts and ratios.
    """
    query = """
        SELECT
            COUNT(*) as total_jobs,
            COUNT(CASE WHEN status = 'successful' THEN 1 END)
                as jobs_succeeded,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as jobs_failed,
            COUNT(CASE WHEN status NOT IN ('successful', 'failed') THEN 1 END)
                as jobs_other_status,
            ROUND(
                COUNT(CASE WHEN status = 'successful' THEN 1 END) * 100.0 /
                NULLIF(COUNT(*), 0), 2
            ) as success_rate_percent,
            ROUND(
                COUNT(CASE WHEN status = 'failed' THEN 1 END) * 100.0 /
                NULLIF(COUNT(*), 0), 2
            ) as failure_rate_percent
        FROM main_unifiedjob
        WHERE created >= %s AND created < %s
    """

    result = _execute_query(query, [since, until])
    return {
        'job_stats': result[0] if result else {},
        'period_start': since.isoformat(),
        'period_end': until.isoformat(),
    }


@register(
    'task_execution_stats',
    '1.0',
    format='json',
    description=_('Task execution statistics'),
)
def task_execution_stats(since, until, **kwargs):
    """
    Task execution statistics from job events.
    """
    query = """
        SELECT
            COUNT(*) as total_tasks,
            COUNT(CASE WHEN event = 'runner_on_ok' THEN 1 END)
                as tasks_succeeded,
            COUNT(CASE WHEN event = 'runner_on_failed' THEN 1 END)
                as tasks_failed,
            COUNT(CASE WHEN event = 'runner_on_skipped' THEN 1 END)
                as tasks_skipped,
            ROUND(
                COUNT(CASE WHEN event = 'runner_on_ok' THEN 1 END) * 100.0 /
                NULLIF(COUNT(CASE WHEN event IN
                    ('runner_on_ok', 'runner_on_failed') THEN 1 END), 0), 2
            ) as success_ratio_percent
        FROM main_jobevent
        WHERE created >= %s AND created < %s
        AND event IN ('runner_on_ok', 'runner_on_failed', 'runner_on_skipped')
    """

    result = _execute_query(query, [since, until])
    return {
        'task_stats': result[0] if result else {},
        'period_start': since.isoformat(),
        'period_end': until.isoformat(),
    }


@register(
    'module_success_failure_rates',
    '1.0',
    format='json',
    description=_('Module success/failure rates'),
)
def module_success_failure_rates(since, until, **kwargs):
    """
    Success/failure rates for individual modules.
    """
    query = """
        WITH module_events AS (
            SELECT
                CASE
                    WHEN event_data::jsonb ? 'task_action'
                    THEN event_data::jsonb->>'task_action'
                    WHEN event_data::jsonb ? 'resolved_action'
                    THEN event_data::jsonb->>'resolved_action'
                    ELSE 'unknown'
                END as module_name,
                event
            FROM main_jobevent
            WHERE created >= %s AND created < %s
            AND event IN ('runner_on_ok', 'runner_on_failed')
            AND (
                (event_data::jsonb ? 'task_action' AND
                 event_data::jsonb->>'task_action' != '')
                OR (event_data::jsonb ? 'resolved_action' AND
                    event_data::jsonb->>'resolved_action' != '')
            )
        )
        SELECT
            module_name,
            COUNT(*) as total_executions,
            COUNT(CASE WHEN event = 'runner_on_ok' THEN 1 END) as successes,
            COUNT(CASE WHEN event = 'runner_on_failed' THEN 1 END) as failures,
            ROUND(
                COUNT(CASE WHEN event = 'runner_on_ok' THEN 1 END) * 100.0 /
                NULLIF(COUNT(*), 0), 2
            ) as success_rate_percent,
            ROUND(
                COUNT(CASE WHEN event = 'runner_on_failed' THEN 1 END) *
                100.0 / NULLIF(COUNT(*), 0), 2
            ) as failure_rate_percent
        FROM module_events
        WHERE module_name != 'unknown'
        GROUP BY module_name
        HAVING COUNT(*) >= 5
        ORDER BY total_executions DESC
    """

    result = _execute_query(query, [since, until])
    return {
        'module_success_failure_rates': result,
        'period_start': since.isoformat(),
        'period_end': until.isoformat(),
    }


@register(
    'modules_usage_by_job_kpi',
    '1.0',
    format='json',
    description=_('KPI - modules used across customers grouped by job'),
)
def modules_usage_by_job_kpi(since, until, **kwargs):
    """
    KPI showing count of modules used across all customers, grouped by job ID
    and modules.
    """
    query = """
        WITH job_modules AS (
            SELECT
                uj.id as job_id,
                uj.name as job_name,
                org.name as organization_name,
                org.id as organization_id,
                CASE
                    WHEN je.event_data::jsonb ? 'task_action'
                    THEN je.event_data::jsonb->>'task_action'
                    WHEN je.event_data::jsonb ? 'resolved_action'
                    THEN je.event_data::jsonb->>'resolved_action'
                    ELSE NULL
                END as module_name
            FROM main_unifiedjob uj
            LEFT JOIN main_organization org ON uj.organization_id = org.id
            LEFT JOIN main_jobevent je ON uj.id = je.job_id
            WHERE uj.created >= %s AND uj.created < %s
            AND je.event = 'runner_on_ok'
            AND (
                (je.event_data::jsonb ? 'task_action' AND
                 je.event_data::jsonb->>'task_action' != '')
                OR (je.event_data::jsonb ? 'resolved_action' AND
                    je.event_data::jsonb->>'resolved_action' != '')
            )
        )
        SELECT
            job_id,
            job_name,
            organization_name,
            organization_id,
            module_name,
            COUNT(*) as module_usage_count
        FROM job_modules
        WHERE module_name IS NOT NULL
        GROUP BY job_id, job_name, organization_name, organization_id,
                 module_name
        ORDER BY organization_name, job_id, module_usage_count DESC
    """

    result = _execute_query(query, [since, until])
    return {
        'modules_usage_by_job': result,
        'total_records': len(result),
        'period_start': since.isoformat(),
        'period_end': until.isoformat(),
    }


@register(
    'templates_executed_by_company',
    '1.0',
    format='json',
    description=_('Number of templates executed by company'),
)
def templates_executed_by_company(since, until, **kwargs):
    """
    Number of templates executed grouped by organization/company.
    """
    query = """
        SELECT
            org.name as organization_name,
            org.id as organization_id,
            COUNT(DISTINCT ujt.id) as unique_templates_executed,
            COUNT(*) as total_template_executions,
            array_agg(DISTINCT ujt.name) as template_names
        FROM main_unifiedjob uj
        JOIN main_unifiedjobtemplate ujt ON uj.unified_job_template_id = ujt.id
        LEFT JOIN main_organization org ON uj.organization_id = org.id
        WHERE uj.created >= %s AND uj.created < %s
        GROUP BY org.id, org.name
        ORDER BY total_template_executions DESC
    """

    result = _execute_query(query, [since, until])
    return {
        'templates_by_organization': result,
        'period_start': since.isoformat(),
        'period_end': until.isoformat(),
    }


@register(
    'total_hosts_automated_over_time',
    '1.0',
    format='json',
    description=_('Total number of hosts automated over time'),
)
def total_hosts_automated_over_time(since, until, **kwargs):
    """
    Total number of unique hosts automated over the time period.
    """
    query = """
        SELECT
            COUNT(DISTINCT jhs.host_id) as unique_hosts_automated,
            COUNT(*) as total_host_automations,
            MIN(jhs.created) as first_automation,
            MAX(jhs.created) as last_automation
        FROM main_jobhostsummary jhs
        WHERE jhs.created >= %s AND jhs.created < %s
    """

    # Also get daily breakdown
    daily_query = """
        SELECT
            DATE(jhs.created) as automation_date,
            COUNT(DISTINCT jhs.host_id) as unique_hosts_that_day,
            COUNT(*) as total_automations_that_day
        FROM main_jobhostsummary jhs
        WHERE jhs.created >= %s AND jhs.created < %s
        GROUP BY DATE(jhs.created)
        ORDER BY automation_date
    """

    overall_result = _execute_query(query, [since, until])
    daily_result = _execute_query(daily_query, [since, until])

    return {
        'overall_stats': overall_result[0] if overall_result else {},
        'daily_breakdown': daily_result,
        'period_start': since.isoformat(),
        'period_end': until.isoformat(),
    }


@register(
    'execution_environment_stats',
    '1.0',
    format='json',
    description=_('Execution environment statistics'),
)
def execution_environment_stats(since, until, **kwargs):
    """
    Statistics about execution environments configured in the controller.
    """
    # Current EE configuration
    ee_config_query = """
        SELECT
            COUNT(*) as total_execution_environments,
            COUNT(CASE WHEN name = 'Default execution environment'
                       OR name LIKE '%%default%%' THEN 1 END)
                as default_ee_count,
            COUNT(CASE WHEN name != 'Default execution environment'
                       AND name NOT LIKE '%%default%%' THEN 1 END)
                as custom_ee_count
        FROM main_executionenvironment
    """

    # EE usage in jobs
    ee_usage_query = """
        SELECT
            ee.name as execution_environment_name,
            ee.id as execution_environment_id,
            COUNT(*) as jobs_using_ee,
            COUNT(DISTINCT uj.unified_job_template_id) as templates_using_ee
        FROM main_unifiedjob uj
        LEFT JOIN main_executionenvironment ee
            ON uj.execution_environment_id = ee.id
        WHERE uj.created >= %s AND uj.created < %s
        GROUP BY ee.id, ee.name
        ORDER BY jobs_using_ee DESC
    """

    config_result = _execute_query(ee_config_query)
    usage_result = _execute_query(ee_usage_query, [since, until])

    # Calculate ratio
    config_data = config_result[0] if config_result else {}
    total_ee = config_data.get('total_execution_environments', 0)
    default_ee = config_data.get('default_ee_count', 0)
    custom_ee = config_data.get('custom_ee_count', 0)

    ratio_data = {}
    if total_ee > 0:
        ratio_data = {
            'default_ee_ratio_percent': round((default_ee / total_ee) * 100, 2),
            'custom_ee_ratio_percent': round((custom_ee / total_ee) * 100, 2),
        }

    return {
        'execution_environment_config': {**config_data, **ratio_data},
        'execution_environment_usage': usage_result,
        'period_start': since.isoformat(),
        'period_end': until.isoformat(),
    }


@register(
    'modules_used_to_automate',
    '1.0',
    format='json',
    description=_('Modules used to automate'),
)
def modules_used_to_automate(since, until, **kwargs):
    """
    List and count of all modules used for automation.
    """
    query = """
        SELECT
            CASE
                WHEN event_data::jsonb ? 'task_action'
                THEN event_data::jsonb->>'task_action'
                WHEN event_data::jsonb ? 'resolved_action'
                THEN event_data::jsonb->>'resolved_action'
                ELSE 'unknown'
            END as module_name,
            COUNT(*) as usage_count,
            COUNT(DISTINCT job_id) as unique_jobs_using_module,
            MIN(created) as first_used,
            MAX(created) as last_used
        FROM main_jobevent
        WHERE created >= %s AND created < %s
        AND event = 'runner_on_ok'
        AND (
            (event_data::jsonb ? 'task_action' AND
             event_data::jsonb->>'task_action' != '')
            OR (event_data::jsonb ? 'resolved_action' AND
                event_data::jsonb->>'resolved_action' != '')
        )
        GROUP BY module_name
        ORDER BY usage_count DESC
    """

    result = _execute_query(query, [since, until])

    # Remove 'unknown' modules and calculate summary stats
    filtered_result = [r for r in result if r['module_name'] != 'unknown']

    summary = {
        'total_unique_modules': len(filtered_result),
        'total_module_executions': sum(r['usage_count'] for r in filtered_result),
        'most_used_module': (filtered_result[0]['module_name'] if filtered_result else None),
        'most_used_module_count': (filtered_result[0]['usage_count'] if filtered_result else 0),
    }

    return {
        'modules_summary': summary,
        'modules_detail': filtered_result,
        'period_start': since.isoformat(),
        'period_end': until.isoformat(),
    }


@register(
    'avg_modules_per_playbook',
    '1.0',
    format='json',
    description=_('Average number of modules used in a playbook'),
)
def avg_modules_per_playbook(since, until, **kwargs):
    """
    Average number of modules used per playbook/job execution.
    """
    query = """
        WITH job_module_counts AS (
            SELECT
                uj.id as job_id,
                uj.name as job_name,
                j.playbook,
                COUNT(DISTINCT
                    CASE
                        WHEN je.event_data::jsonb ? 'task_action'
                        THEN je.event_data::jsonb->>'task_action'
                        WHEN je.event_data::jsonb ? 'resolved_action'
                        THEN je.event_data::jsonb->>'resolved_action'
                        ELSE NULL
                    END
                ) as unique_modules_count
            FROM main_unifiedjob uj
            LEFT JOIN main_job j ON uj.id = j.unifiedjob_ptr_id
            LEFT JOIN main_jobevent je ON uj.id = je.job_id
            WHERE uj.created >= %s AND uj.created < %s
            AND je.event = 'runner_on_ok'
            AND (
                (je.event_data::jsonb ? 'task_action' AND
                 je.event_data::jsonb->>'task_action' != '')
                OR (je.event_data::jsonb ? 'resolved_action' AND
                    je.event_data::jsonb->>'resolved_action' != '')
            )
            GROUP BY uj.id, uj.name, j.playbook
        )
        SELECT
            COUNT(*) as total_jobs_analyzed,
            AVG(unique_modules_count) as avg_modules_per_job,
            MIN(unique_modules_count) as min_modules_per_job,
            MAX(unique_modules_count) as max_modules_per_job,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY unique_modules_count)
                as median_modules_per_job
        FROM job_module_counts
        WHERE unique_modules_count > 0
    """

    # Also get breakdown by playbook
    playbook_query = """
        WITH job_module_counts AS (
            SELECT
                j.playbook,
                COUNT(DISTINCT
                    CASE
                        WHEN je.event_data::jsonb ? 'task_action'
                        THEN je.event_data::jsonb->>'task_action'
                        WHEN je.event_data::jsonb ? 'resolved_action'
                        THEN je.event_data::jsonb->>'resolved_action'
                        ELSE NULL
                    END
                ) as unique_modules_count,
                COUNT(DISTINCT uj.id) as job_count
            FROM main_unifiedjob uj
            LEFT JOIN main_job j ON uj.id = j.unifiedjob_ptr_id
            LEFT JOIN main_jobevent je ON uj.id = je.job_id
            WHERE uj.created >= %s AND uj.created < %s
            AND je.event = 'runner_on_ok'
            AND j.playbook IS NOT NULL
            AND j.playbook != ''
            AND (
                (je.event_data::jsonb ? 'task_action' AND
                 je.event_data::jsonb->>'task_action' != '')
                OR (je.event_data::jsonb ? 'resolved_action' AND
                    je.event_data::jsonb->>'resolved_action' != '')
            )
            GROUP BY j.playbook
        )
        SELECT
            playbook,
            unique_modules_count,
            job_count,
            ROUND(unique_modules_count::decimal / job_count, 2)
                as avg_modules_per_execution
        FROM job_module_counts
        WHERE unique_modules_count > 0
        ORDER BY unique_modules_count DESC
        LIMIT 20
    """

    overall_result = _execute_query(query, [since, until])
    playbook_result = _execute_query(playbook_query, [since, until])

    return {
        'overall_statistics': overall_result[0] if overall_result else {},
        'top_playbooks_by_module_usage': playbook_result,
        'period_start': since.isoformat(),
        'period_end': until.isoformat(),
    }
