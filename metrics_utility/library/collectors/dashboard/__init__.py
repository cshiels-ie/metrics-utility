"""Dashboard reports collectors for automation-reports integration.

This module provides SQL-based collectors that query the AWX/Automation Controller
database directly to gather dashboard metrics for the automation-reports frontend.

The collectors are designed to be used by metrics-service to periodically collect
and cache dashboard data, replacing the need for direct AWX API calls from the frontend.
"""

from .collectors import dashboard_job_templates, dashboard_top_projects, dashboard_top_users


__all__ = [
    'dashboard_job_templates',
    'dashboard_top_projects',
    'dashboard_top_users',
]
