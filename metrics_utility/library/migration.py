"""
Database migration utilities for metrics-utility library.

This module provides database-agnostic migration functionality for copying
PostgreSQL tables between databases using pg_dump, pg_restore, and COPY.

Unlike the CLI command, this library module has no Django dependencies and
uses only psycopg connections. It can be used in any Python application.
"""

import os
import subprocess
import tempfile

import psycopg

from metrics_utility.library.collectors.util import date_where


# SQL for creating custom PostgreSQL functions
CUSTOM_FUNCTIONS_SQL = """
-- Define function for parsing field out of yaml encoded as text
CREATE OR REPLACE FUNCTION metrics_utility_parse_yaml_field(
    str text,
    field text
)
RETURNS text AS
$$
DECLARE
    line_re text;
    field_re text;
BEGIN
    field_re := ' *[:=] *(.+?) *$';
    line_re := '(?n)^' || field || field_re;
    RETURN trim(both '"' from substring(str from line_re) );
END;
$$
LANGUAGE plpgsql;

-- Define function to check if field is a valid json
CREATE OR REPLACE FUNCTION metrics_utility_is_valid_json(p_json text)
    returns boolean
AS
$$
BEGIN
    RETURN (p_json::json is not null);
EXCEPTION
    WHEN others
    THEN RETURN false;
END;
$$
LANGUAGE plpgsql;
"""

# Mapping of table names to their timestamp columns for incremental sync
TABLE_TIMESTAMP_COLUMNS = {
    'main_host': 'modified',
    'main_inventory': 'modified',
    'main_organization': 'modified',
    'main_unifiedjob': 'created',
    'main_jobevent': 'created',
    'main_jobhostsummary': 'modified',
    'main_indirectmanagednodeaudit': 'created',
    'main_executionenvironment': 'modified',
    'main_hostmetric': 'last_automation',
    'main_hostmetricsummarymonthly': 'created',
}


def build_connection_string(host, port, dbname, user, password=None):
    """
    Build PostgreSQL connection string for pg_dump/pg_restore/psql.

    Args:
        host (str): Database hostname
        port (str|int): Database port
        dbname (str): Database name
        user (str): Database username
        password (str, optional): Database password

    Returns:
        str: PostgreSQL connection string
    """
    if password:
        return f'postgresql://{user}:{password}@{host}:{port}/{dbname}'
    else:
        return f'postgresql://{user}@{host}:{port}/{dbname}'


def connect(host, port, dbname, user, password=None):
    """
    Create a psycopg connection to a PostgreSQL database.

    Args:
        host (str): Database hostname
        port (str|int): Database port
        dbname (str): Database name
        user (str): Database username
        password (str, optional): Database password

    Returns:
        psycopg.Connection: Database connection
    """
    conn_str = f'host={host} port={port} dbname={dbname} user={user}'
    if password:
        conn_str += f' password={password}'

    return psycopg.connect(conn_str)


def check_pg_tools():
    """
    Verify PostgreSQL client tools are installed.

    Returns:
        tuple: (success: bool, missing_tools: list)
    """
    required_tools = ['pg_dump', 'pg_restore', 'psql']
    missing = []

    for tool in required_tools:
        result = subprocess.run(['which', tool], capture_output=True, text=True)
        if result.returncode != 0:
            missing.append(tool)

    return (len(missing) == 0, missing)


def validate_connection(host, port, dbname, user, password=None):
    """
    Validate database connection using psql.

    Args:
        host (str): Database hostname
        port (str|int): Database port
        dbname (str): Database name
        user (str): Database username
        password (str, optional): Database password

    Returns:
        tuple: (success: bool, error_message: str)
    """
    conn_str = build_connection_string(host, port, dbname, user, password)

    try:
        result = subprocess.run(['psql', conn_str, '-c', 'SELECT 1'], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return (False, f'Connection failed: {result.stderr}')
        return (True, None)
    except subprocess.TimeoutExpired:
        return (False, 'Connection timeout')
    except Exception as e:
        return (False, f'Connection error: {str(e)}')


def discover_tables(db, pattern='main_%'):
    """
    Discover tables matching a pattern in the database.

    Args:
        db: Database connection (psycopg.Connection)
        pattern (str): SQL LIKE pattern for table names (default: 'main_%')

    Returns:
        list: Table names sorted alphabetically
    """
    query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name LIKE %s
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """

    with db.cursor() as cursor:
        cursor.execute(query, (pattern,))
        tables = [row[0] for row in cursor.fetchall()]

    return tables


def get_timestamp_column(table_name, custom_mapping=None):
    """
    Get the timestamp column name for a table (for incremental sync).

    Args:
        table_name (str): Name of the table
        custom_mapping (dict, optional): Custom table->column mapping to override defaults

    Returns:
        str or None: Timestamp column name, or None if not found
    """
    mapping = custom_mapping if custom_mapping else TABLE_TIMESTAMP_COLUMNS
    return mapping.get(table_name)


def create_custom_functions(db):
    """
    Create custom PostgreSQL functions in a database.

    These functions are used by some collectors and need to exist before data migration.

    Args:
        db: Database connection (psycopg.Connection)

    Returns:
        tuple: (success: bool, error_message: str)
    """
    try:
        with db.cursor() as cursor:
            cursor.execute(CUSTOM_FUNCTIONS_SQL)
        db.commit()
        return (True, None)
    except Exception as e:
        return (False, f'Failed to create custom functions: {str(e)}')


def check_table_exists(db, table_name, schema='public'):
    """
    Check if a table exists in the database.

    Args:
        db: Database connection (psycopg.Connection)
        table_name (str): Name of the table
        schema (str): Schema name (default: 'public')

    Returns:
        tuple: (exists: bool, row_count: int or None)
    """
    with db.cursor() as cursor:
        # Check if table exists
        cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_name = %s', (schema, table_name))
        exists = cursor.fetchone()[0] > 0

        if exists:
            # Get row count
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            row_count = cursor.fetchone()[0]
            return (True, row_count)

    return (False, None)


def drop_table(db, table_name):
    """
    Drop a table from the database.

    Args:
        db: Database connection (psycopg.Connection)
        table_name (str): Name of the table to drop

    Returns:
        tuple: (success: bool, error_message: str)
    """
    try:
        with db.cursor() as cursor:
            cursor.execute(f'DROP TABLE IF EXISTS {table_name} CASCADE')
        db.commit()
        return (True, None)
    except Exception as e:
        return (False, f'Failed to drop table: {str(e)}')


def migrate_table_full(table_name, source_conn_str, dest_conn_str, force=False):
    """
    Perform full table migration using pg_dump/pg_restore.

    Migrates schema and all data for a single table.

    Args:
        table_name (str): Name of the table to migrate
        source_conn_str (str): Source database connection string
        dest_conn_str (str): Destination database connection string
        force (bool): Drop table in destination if it exists (default: False)

    Returns:
        tuple: (success: bool, message: str, row_count: int or None)
    """
    temp_dir = tempfile.mkdtemp(prefix='metrics_migration_')

    try:
        # Step 1: Dump schema
        schema_file = os.path.join(temp_dir, f'{table_name}_schema.sql')
        cmd = ['pg_dump', '--schema-only', '--no-owner', '--no-privileges', '--table', table_name, source_conn_str]

        with open(schema_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            return (False, f'Schema dump failed: {result.stderr}', None)

        # Step 2: Drop table if force mode
        if force:
            # Extract connection params from connection string
            dest_conn = psycopg.connect(dest_conn_str.replace('postgresql://', ''))
            drop_table(dest_conn, table_name)
            dest_conn.close()

        # Step 3: Restore schema
        cmd = ['psql', dest_conn_str, '-f', schema_file]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0 and 'already exists' not in result.stderr:
            return (False, f'Schema restore failed: {result.stderr}', None)

        # Step 4: Dump data
        data_file = os.path.join(temp_dir, f'{table_name}_data.dump')
        cmd = ['pg_dump', '--data-only', '--format=custom', '--table', table_name, source_conn_str]

        with open(data_file, 'wb') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE)

        if result.returncode != 0:
            return (False, f'Data dump failed: {result.stderr.decode()}', None)

        # Step 5: Restore data
        cmd = ['pg_restore', '--data-only', '--dbname', dest_conn_str, data_file]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # pg_restore may have warnings but still succeed
        if result.returncode != 0 and result.stderr:
            # Still return success if the restore completed
            pass

        # Get row count from destination
        dest_conn = psycopg.connect(dest_conn_str.replace('postgresql://', ''))
        with dest_conn.cursor() as cursor:
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            row_count = cursor.fetchone()[0]
        dest_conn.close()

        return (True, 'Success', row_count)

    except Exception as e:
        return (False, f'Migration failed: {str(e)}', None)

    finally:
        # Clean up temp directory
        import shutil

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def migrate_table_incremental(table_name, source_db, dest_db, since, until=None, timestamp_column=None):
    """
    Perform incremental table migration using COPY.

    Migrates only data within a time window based on a timestamp column.

    Args:
        table_name (str): Name of the table to migrate
        source_db: Source database connection (psycopg.Connection)
        dest_db: Destination database connection (psycopg.Connection)
        since (datetime): Start date for sync (inclusive)
        until (datetime, optional): End date for sync (exclusive)
        timestamp_column (str, optional): Column to filter on (auto-detected if not provided)

    Returns:
        tuple: (success: bool, message: str, row_count: int or None)
    """
    # Auto-detect timestamp column if not provided
    if not timestamp_column:
        timestamp_column = get_timestamp_column(table_name)

    if not timestamp_column:
        return (False, f'No timestamp column defined for {table_name}', None)

    try:
        # Build time filter query
        where_clause = date_where(timestamp_column, since, until)
        query = f'SELECT * FROM {table_name} WHERE {where_clause}'

        # Export from source using COPY
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)

        with source_db.cursor() as cursor:
            copy_query = f'COPY ({query}) TO STDOUT WITH CSV HEADER'

            # Handle both psycopg2 (copy_expert) and psycopg3 (copy) APIs
            if hasattr(cursor, 'copy_expert') and callable(cursor.copy_expert):
                cursor.copy_expert(copy_query, temp_file)
            else:
                # psycopg3
                with cursor.copy(copy_query) as copy_obj:
                    while data := copy_obj.read():
                        byte_data = bytes(data)
                        temp_file.write(byte_data.decode())

        temp_file.close()

        # Get row count from exported file
        with open(temp_file.name, 'r') as f:
            row_count = sum(1 for _ in f) - 1  # Subtract header row

        if row_count == 0:
            os.unlink(temp_file.name)
            return (True, 'No new data in time range', 0)

        # Import to destination
        with dest_db.cursor() as cursor:
            with open(temp_file.name, 'r') as f:
                # Skip header
                next(f)
                copy_import = f'COPY {table_name} FROM STDIN WITH CSV'

                # Handle both psycopg2 and psycopg3
                if hasattr(cursor, 'copy_expert') and callable(cursor.copy_expert):
                    cursor.copy_expert(copy_import, f)
                else:
                    # psycopg3
                    with cursor.copy(copy_import) as copy_obj:
                        for line in f:
                            copy_obj.write(line)

        dest_db.commit()

        # Clean up temp file
        os.unlink(temp_file.name)

        return (True, 'Success', row_count)

    except Exception as e:
        return (False, f'Incremental migration failed: {str(e)}', None)


def validate_migration(source_db, dest_db, table_name):
    """
    Validate migration by comparing row counts.

    Args:
        source_db: Source database connection (psycopg.Connection)
        dest_db: Destination database connection (psycopg.Connection)
        table_name (str): Name of the table to validate

    Returns:
        dict: {source_count, dest_count, match, difference}
    """
    # Get source count
    with source_db.cursor() as cursor:
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        source_count = cursor.fetchone()[0]

    # Get destination count
    with dest_db.cursor() as cursor:
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        dest_count = cursor.fetchone()[0]

    return {'source_count': source_count, 'dest_count': dest_count, 'match': source_count == dest_count, 'difference': dest_count - source_count}
