#!/usr/bin/env python3
"""
Example: Using metrics_utility.library.migration for database migration

This example shows how to use the migration library directly without Django.
It can be used in any Python application that needs to migrate PostgreSQL tables.
"""

from metrics_utility.library import instants, migration


def example_full_migration():
    """Example: Full table migration using library API"""
    print('=== Example: Full Table Migration ===\n')

    # Database connection parameters
    source_host = 'controller.example.com'
    source_port = 5432
    source_db = 'awx'
    source_user = 'awx'
    source_pass = 'secret'

    dest_host = 'storage.example.com'
    dest_port = 5432
    dest_db = 'metrics_storage'
    dest_user = 'storage_user'
    dest_pass = 'storage_pass'

    # Step 1: Check PostgreSQL tools are installed
    print('Checking PostgreSQL client tools...')
    success, missing = migration.check_pg_tools()
    if not success:
        print(f'Error: Missing PostgreSQL tools: {", ".join(missing)}')
        print('Please install PostgreSQL client tools (pg_dump, pg_restore, psql)')
        return

    print('✓ All PostgreSQL tools found\n')

    # Step 2: Validate connections
    print('Validating database connections...')

    success, error = migration.validate_connection(source_host, source_port, source_db, source_user, source_pass)
    if not success:
        print(f'Error: Source database connection failed: {error}')
        return
    print(f'✓ Source database: {source_host}:{source_port}/{source_db}')

    success, error = migration.validate_connection(dest_host, dest_port, dest_db, dest_user, dest_pass)
    if not success:
        print(f'Error: Destination database connection failed: {error}')
        return
    print(f'✓ Destination database: {dest_host}:{dest_port}/{dest_db}\n')

    # Step 3: Connect and discover tables
    print('Discovering tables...')
    source_conn = migration.connect(source_host, source_port, source_db, source_user, source_pass)
    tables = migration.discover_tables(source_conn, pattern='main_%')
    source_conn.close()

    print(f'Found {len(tables)} tables to migrate')
    for table in tables[:5]:  # Show first 5
        print(f'  - {table}')
    if len(tables) > 5:
        print(f'  ... and {len(tables) - 5} more\n')

    # Step 4: Create custom functions in destination
    print('Creating custom PostgreSQL functions in destination...')
    dest_conn = migration.connect(dest_host, dest_port, dest_db, dest_user, dest_pass)
    success, error = migration.create_custom_functions(dest_conn)
    dest_conn.close()

    if not success:
        print(f'Error: Failed to create custom functions: {error}')
        return
    print('✓ Custom functions created\n')

    # Step 5: Build connection strings for pg_dump/pg_restore
    source_conn_str = migration.build_connection_string(source_host, source_port, source_db, source_user, source_pass)
    dest_conn_str = migration.build_connection_string(dest_host, dest_port, dest_db, dest_user, dest_pass)

    # Step 6: Migrate tables
    print('Migrating tables...')
    results = {}

    for table in tables[:3]:  # Migrate first 3 tables as example
        print(f'  Migrating {table}...', end=' ')

        success, message, row_count = migration.migrate_table_full(
            table,
            source_conn_str,
            dest_conn_str,
            force=False,  # Don't drop existing tables
        )

        results[table] = {'success': success, 'message': message, 'row_count': row_count}

        if success:
            print(f'✓ {row_count} rows')
        else:
            print(f'✗ {message}')

    # Step 7: Validate migrations
    print('\nValidating migrations...')
    source_conn = migration.connect(source_host, source_port, source_db, source_user, source_pass)
    dest_conn = migration.connect(dest_host, dest_port, dest_db, dest_user, dest_pass)

    for table in results.keys():
        if results[table]['success']:
            result = migration.validate_migration(source_conn, dest_conn, table)
            if result['match']:
                print(f'  {table}: ✓ {result["source_count"]} rows')
            else:
                print(f'  {table}: ✗ source={result["source_count"]}, dest={result["dest_count"]}')

    source_conn.close()
    dest_conn.close()

    print('\nFull migration complete!')


def example_incremental_sync():
    """Example: Incremental sync using library API"""
    print('\n=== Example: Incremental Sync (Last 30 Days) ===\n')

    # Database connection parameters
    source_host = 'controller.example.com'
    source_port = 5432
    source_db = 'awx'
    source_user = 'awx'
    source_pass = 'secret'

    dest_host = 'storage.example.com'
    dest_port = 5432
    dest_db = 'metrics_storage'
    dest_user = 'storage_user'
    dest_pass = 'storage_pass'

    # Connect to databases
    print('Connecting to databases...')
    source_conn = migration.connect(source_host, source_port, source_db, source_user, source_pass)
    dest_conn = migration.connect(dest_host, dest_port, dest_db, dest_user, dest_pass)
    print('✓ Connected\n')

    # Define time window (last 30 days)
    since = instants.days_ago(30)
    until = instants.now()
    print(f'Time window: {since.isoformat()} to {until.isoformat()}\n')

    # Tables to sync (only those with timestamp columns)
    tables_to_sync = ['main_host', 'main_inventory', 'main_jobevent', 'main_jobhostsummary']

    print('Syncing tables...')
    for table in tables_to_sync:
        # Get timestamp column for this table
        timestamp_col = migration.get_timestamp_column(table)

        if not timestamp_col:
            print(f'  {table}: Skipped (no timestamp column defined)')
            continue

        print(f'  {table} (filtering on {timestamp_col})...', end=' ')

        success, message, row_count = migration.migrate_table_incremental(table, source_conn, dest_conn, since, until, timestamp_column=timestamp_col)

        if success:
            if row_count == 0:
                print('No new data')
            else:
                print(f'✓ Synced {row_count} rows')
        else:
            print(f'✗ {message}')

    source_conn.close()
    dest_conn.close()

    print('\nIncremental sync complete!')


def example_custom_timestamp_mapping():
    """Example: Using custom timestamp column mapping"""
    print('\n=== Example: Custom Timestamp Mapping ===\n')

    # Define custom mapping for non-standard tables
    custom_mapping = {
        'my_custom_table': 'updated_at',
        'another_table': 'last_modified',
    }

    # Check timestamp columns
    tables = ['main_host', 'my_custom_table', 'another_table']

    for table in tables:
        timestamp_col = migration.get_timestamp_column(table, custom_mapping=custom_mapping)
        if timestamp_col:
            print(f'{table}: {timestamp_col}')
        else:
            print(f'{table}: No timestamp column defined')


if __name__ == '__main__':
    print('IMPORTANT: This is an example script with dummy connection parameters.')
    print('Update the connection details before running!\n')

    # Uncomment to run examples:
    # example_full_migration()
    # example_incremental_sync()
    # example_custom_timestamp_mapping()

    print('Update connection parameters and uncomment examples to run.')
