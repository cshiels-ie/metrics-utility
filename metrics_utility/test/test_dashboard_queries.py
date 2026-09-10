from datetime import datetime

from metrics_utility.library.collectors.dashboard.queries import get_where_clause


def test_dashboard_queries_exclude_sync_and_workflow_by_default():
    where_clause, params = get_where_clause(datetime(2026, 1, 1), datetime(2026, 1, 2))

    assert 'launch_type NOT IN' in where_clause
    assert params[:2] == ['sync', 'workflow']


def test_dashboard_queries_can_include_sync_and_workflow():
    where_clause, params = get_where_clause(datetime(2026, 1, 1), datetime(2026, 1, 2), include_sync_workflow_jobs=True)

    assert 'launch_type NOT IN' not in where_clause
    assert params == ['failed', 'successful', '2026-01-01T00:00:00', '2026-01-02T00:00:00']
