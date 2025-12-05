from .automation_reports_entities import (
    automation_reports_execution_environments,
    automation_reports_execution_environments_daily,
    automation_reports_hosts,
    automation_reports_hosts_daily,
    automation_reports_instance_groups,
    automation_reports_instance_groups_daily,
    automation_reports_inventories,
    automation_reports_inventories_daily,
    automation_reports_labels,
    automation_reports_labels_daily,
    automation_reports_projects,
    automation_reports_projects_daily,
    automation_reports_users,
    automation_reports_users_daily,
)
from .automation_reports_job_host_summaries import (
    automation_reports_job_host_summaries,
    automation_reports_job_host_summaries_daily,
)
from .automation_reports_job_templates import (
    automation_reports_job_templates,
    automation_reports_job_templates_daily,
)
from .automation_reports_jobs import (
    automation_reports_jobs,
    automation_reports_jobs_daily,
)

# Automation Reports collectors
from .automation_reports_organizations import (
    automation_reports_organizations,
    automation_reports_organizations_daily,
)
from .config import config
from .execution_environments import execution_environments
from .job_host_summary import job_host_summary
from .job_host_summary_service import job_host_summary_service
from .main_host import main_host, main_host_daily
from .main_indirectmanagednodeaudit import main_indirectmanagednodeaudit
from .main_jobevent import main_jobevent
from .main_jobevent_service import main_jobevent_service
from .unified_jobs import unified_jobs


__all__ = [
    'config',
    'execution_environments',
    'job_host_summary',
    'job_host_summary_service',
    'main_host',
    'main_host_daily',
    'main_indirectmanagednodeaudit',
    'main_jobevent',
    'main_jobevent_service',
    'unified_jobs',
    # Automation Reports
    'automation_reports_organizations',
    'automation_reports_organizations_daily',
    'automation_reports_job_templates',
    'automation_reports_job_templates_daily',
    'automation_reports_jobs',
    'automation_reports_jobs_daily',
    'automation_reports_job_host_summaries',
    'automation_reports_job_host_summaries_daily',
    'automation_reports_inventories',
    'automation_reports_inventories_daily',
    'automation_reports_projects',
    'automation_reports_projects_daily',
    'automation_reports_hosts',
    'automation_reports_hosts_daily',
    'automation_reports_users',
    'automation_reports_users_daily',
    'automation_reports_execution_environments',
    'automation_reports_execution_environments_daily',
    'automation_reports_instance_groups',
    'automation_reports_instance_groups_daily',
    'automation_reports_labels',
    'automation_reports_labels_daily',
]
