"""
Collectors for AWX/Controller supporting entities for automation reports.

Collects inventories, projects, hosts, users, execution environments,
instance groups, and labels.
"""

from ..util import collector, copy_table, date_where


# ==================== Inventories ====================


def _inventories_query(where='TRUE'):
    """Query to extract inventory data."""
    return f"""
        SELECT
            inv.id AS external_id,
            inv.name,
            inv.description,
            inv.organization_id,
            inv.created,
            inv.modified
        FROM main_inventory inv
        WHERE {where}
        ORDER BY inv.id ASC
    """


@collector
def automation_reports_inventories(*, db=None, output_dir=None):
    """Collect all inventories."""
    query = _inventories_query()
    return copy_table(db=db, table='automation_reports_inventories', query=query, output_dir=output_dir)


@collector
def automation_reports_inventories_daily(*, db=None, since=None, until=None, output_dir=None):
    """Collect inventories created or modified within a date range."""
    where = f"""
        ({date_where('inv.created', since, until)}
        OR {date_where('inv.modified', since, until)})
    """
    query = _inventories_query(where)
    return copy_table(db=db, table='automation_reports_inventories_daily', query=query, output_dir=output_dir)


# ==================== Projects ====================


def _projects_query(where='TRUE'):
    """Query to extract project data."""
    return f"""
        SELECT
            proj.id AS external_id,
            proj.name,
            proj.description,
            proj.scm_type,
            proj.organization_id,
            proj.created,
            proj.modified
        FROM main_project proj
        WHERE {where}
        ORDER BY proj.id ASC
    """


@collector
def automation_reports_projects(*, db=None, output_dir=None):
    """Collect all projects."""
    query = _projects_query()
    return copy_table(db=db, table='automation_reports_projects', query=query, output_dir=output_dir)


@collector
def automation_reports_projects_daily(*, db=None, since=None, until=None, output_dir=None):
    """Collect projects created or modified within a date range."""
    where = f"""
        ({date_where('proj.created', since, until)}
        OR {date_where('proj.modified', since, until)})
    """
    query = _projects_query(where)
    return copy_table(db=db, table='automation_reports_projects_daily', query=query, output_dir=output_dir)


# ==================== Hosts ====================


def _hosts_query(where='TRUE'):
    """Query to extract host data."""
    return f"""
        SELECT
            h.id AS external_id,
            h.name,
            h.description,
            h.inventory_id,
            h.created,
            h.modified
        FROM main_host h
        WHERE {where}
        ORDER BY h.id ASC
    """


@collector
def automation_reports_hosts(*, db=None, output_dir=None):
    """Collect all enabled hosts."""
    query = _hosts_query('h.enabled = TRUE')
    return copy_table(db=db, table='automation_reports_hosts', query=query, output_dir=output_dir)


@collector
def automation_reports_hosts_daily(*, db=None, since=None, until=None, output_dir=None):
    """Collect hosts created or modified within a date range."""
    where = f"""
        h.enabled = TRUE AND
        ({date_where('h.created', since, until)}
        OR {date_where('h.modified', since, until)})
    """
    query = _hosts_query(where)
    return copy_table(db=db, table='automation_reports_hosts_daily', query=query, output_dir=output_dir)


# ==================== Users ====================


def _users_query(where='TRUE'):
    """Query to extract user data."""
    return f"""
        SELECT
            u.id AS external_id,
            u.username,
            u.first_name,
            u.last_name,
            u.email,
            CASE
                WHEN u.is_superuser THEN 'superuser'
                ELSE 'normal'
            END AS user_type,
            u.date_joined AS created,
            u.last_login AS modified
        FROM auth_user u
        WHERE {where}
        ORDER BY u.id ASC
    """


@collector
def automation_reports_users(*, db=None, output_dir=None):
    """Collect all active users."""
    query = _users_query('u.is_active = TRUE')
    return copy_table(db=db, table='automation_reports_users', query=query, output_dir=output_dir)


@collector
def automation_reports_users_daily(*, db=None, since=None, until=None, output_dir=None):
    """Collect users created or modified within a date range."""
    where = f"""
        u.is_active = TRUE AND
        ({date_where('u.date_joined', since, until)}
        OR {date_where('u.last_login', since, until)})
    """
    query = _users_query(where)
    return copy_table(db=db, table='automation_reports_users_daily', query=query, output_dir=output_dir)


# ==================== Execution Environments ====================


def _execution_environments_query(where='TRUE'):
    """Query to extract execution environment data."""
    return f"""
        SELECT
            ee.id AS external_id,
            ee.name,
            ee.description,
            ee.image,
            ee.created,
            ee.modified
        FROM main_executionenvironment ee
        WHERE {where}
        ORDER BY ee.id ASC
    """


@collector
def automation_reports_execution_environments(*, db=None, output_dir=None):
    """Collect all execution environments."""
    query = _execution_environments_query()
    return copy_table(db=db, table='automation_reports_execution_environments', query=query, output_dir=output_dir)


@collector
def automation_reports_execution_environments_daily(*, db=None, since=None, until=None, output_dir=None):
    """Collect execution environments created or modified within a date range."""
    where = f"""
        ({date_where('ee.created', since, until)}
        OR {date_where('ee.modified', since, until)})
    """
    query = _execution_environments_query(where)
    return copy_table(db=db, table='automation_reports_execution_environments_daily', query=query, output_dir=output_dir)


# ==================== Instance Groups ====================


def _instance_groups_query(where='TRUE'):
    """Query to extract instance group data."""
    return f"""
        SELECT
            ig.id AS external_id,
            ig.name,
            ig.is_container_group,
            ig.created,
            ig.modified
        FROM main_instancegroup ig
        WHERE {where}
        ORDER BY ig.id ASC
    """


@collector
def automation_reports_instance_groups(*, db=None, output_dir=None):
    """Collect all instance groups."""
    query = _instance_groups_query()
    return copy_table(db=db, table='automation_reports_instance_groups', query=query, output_dir=output_dir)


@collector
def automation_reports_instance_groups_daily(*, db=None, since=None, until=None, output_dir=None):
    """Collect instance groups created or modified within a date range."""
    where = f"""
        ({date_where('ig.created', since, until)}
        OR {date_where('ig.modified', since, until)})
    """
    query = _instance_groups_query(where)
    return copy_table(db=db, table='automation_reports_instance_groups_daily', query=query, output_dir=output_dir)


# ==================== Labels ====================


def _labels_query(where='TRUE'):
    """Query to extract label data."""
    return f"""
        SELECT
            l.id AS external_id,
            l.name,
            l.organization_id,
            l.created,
            l.modified
        FROM main_label l
        WHERE {where}
        ORDER BY l.id ASC
    """


@collector
def automation_reports_labels(*, db=None, output_dir=None):
    """Collect all labels."""
    query = _labels_query()
    return copy_table(db=db, table='automation_reports_labels', query=query, output_dir=output_dir)


@collector
def automation_reports_labels_daily(*, db=None, since=None, until=None, output_dir=None):
    """Collect labels created or modified within a date range."""
    where = f"""
        ({date_where('l.created', since, until)}
        OR {date_where('l.modified', since, until)})
    """
    query = _labels_query(where)
    return copy_table(db=db, table='automation_reports_labels_daily', query=query, output_dir=output_dir)
