## `metrics_utility.library.migration`

Database migration utilities for copying PostgreSQL tables between databases.

This module provides database-agnostic migration functionality using `pg_dump`, `pg_restore`, and `COPY`. Unlike the CLI command, this library module has no Django dependencies and uses only psycopg connections.

### Use Cases

- Migrating Controller metrics tables to long-term storage
- Creating database backups or replicas
- Moving specific tables between environments
- Incremental data synchronization based on timestamps

### Functions

#### Connection Management

```python
connect(host, port, dbname, user, password=None)
```
Create a psycopg connection to a PostgreSQL database.

```python
build_connection_string(host, port, dbname, user, password=None)
```
Build PostgreSQL connection string for pg_dump/pg_restore/psql tools.

```python
validate_connection(host, port, dbname, user, password=None)
```
Validate database connection using psql. Returns `(success: bool, error_message: str)`.

```python
check_pg_tools()
```
Verify PostgreSQL client tools (pg_dump, pg_restore, psql) are installed. Returns `(success: bool, missing_tools: list)`.

#### Table Discovery

```python
discover_tables(db, pattern='main_%')
```
Discover tables matching a pattern. Returns sorted list of table names.

```python
get_timestamp_column(table_name, custom_mapping=None)
```
Get the timestamp column name for a table (for incremental sync). Returns column name or `None`.

```python
check_table_exists(db, table_name, schema='public')
```
Check if a table exists. Returns `(exists: bool, row_count: int or None)`.

#### Schema Management

```python
create_custom_functions(db)
```
Create custom PostgreSQL functions (metrics_utility_parse_yaml_field, metrics_utility_is_valid_json). Returns `(success: bool, error_message: str)`.

```python
drop_table(db, table_name)
```
Drop a table from the database. Returns `(success: bool, error_message: str)`.

#### Migration

```python
migrate_table_full(table_name, source_conn_str, dest_conn_str, force=False)
```
Perform full table migration using pg_dump/pg_restore. Migrates schema and all data.

Returns: `(success: bool, message: str, row_count: int or None)`

```python
migrate_table_incremental(table_name, source_db, dest_db, since, until=None, timestamp_column=None)
```
Perform incremental table migration using COPY. Migrates only data within a time window.

Args:
- `source_db`: Source database connection (psycopg.Connection)
- `dest_db`: Destination database connection (psycopg.Connection)
- `since`: Start date for sync (inclusive, datetime)
- `until`: End date for sync (exclusive, datetime, optional)
- `timestamp_column`: Column to filter on (auto-detected if not provided)

Returns: `(success: bool, message: str, row_count: int or None)`

#### Validation

```python
validate_migration(source_db, dest_db, table_name)
```
Validate migration by comparing row counts. Returns dict with `source_count`, `dest_count`, `match`, and `difference`.

### Example Usage

#### Full Migration

```python
from metrics_utility.library import migration

# Check tools are installed
success, missing = migration.check_pg_tools()
if not success:
    print(f'Missing tools: {missing}')
    exit(1)

# Build connection strings
source_conn_str = migration.build_connection_string(
    host='controller.example.com',
    port=5432,
    dbname='awx',
    user='awx',
    password='secret'
)

dest_conn_str = migration.build_connection_string(
    host='storage.example.com',
    port=5432,
    dbname='metrics_storage',
    user='storage_user',
    password='storage_pass'
)

# Validate connections
success, error = migration.validate_connection('controller.example.com', 5432, 'awx', 'awx', 'secret')
if not success:
    print(f'Connection failed: {error}')
    exit(1)

# Connect to source to discover tables
source_db = migration.connect('controller.example.com', 5432, 'awx', 'awx', 'secret')
tables = migration.discover_tables(source_db, pattern='main_%')
source_db.close()

print(f'Found {len(tables)} tables to migrate')

# Create custom functions in destination
dest_db = migration.connect('storage.example.com', 5432, 'metrics_storage', 'storage_user', 'storage_pass')
success, error = migration.create_custom_functions(dest_db)
dest_db.close()

if not success:
    print(f'Failed to create functions: {error}')
    exit(1)

# Migrate each table
for table in tables:
    print(f'Migrating {table}...')
    success, message, row_count = migration.migrate_table_full(
        table,
        source_conn_str,
        dest_conn_str,
        force=False  # Don't drop existing tables
    )

    if success:
        print(f'  Success: {row_count} rows')
    else:
        print(f'  Failed: {message}')

# Validate migrations
source_db = migration.connect('controller.example.com', 5432, 'awx', 'awx', 'secret')
dest_db = migration.connect('storage.example.com', 5432, 'metrics_storage', 'storage_user', 'storage_pass')

for table in tables:
    result = migration.validate_migration(source_db, dest_db, table)
    if result['match']:
        print(f'{table}: ✓ {result["source_count"]} rows')
    else:
        print(f'{table}: ✗ source={result["source_count"]}, dest={result["dest_count"]}')

source_db.close()
dest_db.close()
```

#### Incremental Sync

```python
from metrics_utility.library import migration, instants

# Connect to databases
source_db = migration.connect('controller.example.com', 5432, 'awx', 'awx', 'secret')
dest_db = migration.connect('storage.example.com', 5432, 'metrics_storage', 'storage_user', 'storage_pass')

# Sync data from last 30 days
since = instants.days_ago(30)
until = instants.now()

tables_to_sync = ['main_host', 'main_inventory', 'main_jobevent']

for table in tables_to_sync:
    # Get timestamp column for this table
    timestamp_col = migration.get_timestamp_column(table)

    if not timestamp_col:
        print(f'Skipping {table} - no timestamp column defined')
        continue

    print(f'Syncing {table} (last 30 days on {timestamp_col})...')

    success, message, row_count = migration.migrate_table_incremental(
        table,
        source_db,
        dest_db,
        since,
        until,
        timestamp_column=timestamp_col
    )

    if success:
        if row_count == 0:
            print(f'  No new data')
        else:
            print(f'  Synced {row_count} rows')
    else:
        print(f'  Failed: {message}')

source_db.close()
dest_db.close()
```

### Timestamp Column Mapping

For incremental sync, these tables have predefined timestamp columns:

- `main_host`: `modified`
- `main_inventory`: `modified`
- `main_organization`: `modified`
- `main_unifiedjob`: `created`
- `main_jobevent`: `created`
- `main_jobhostsummary`: `modified`
- `main_indirectmanagednodeaudit`: `created`
- `main_executionenvironment`: `modified`
- `main_hostmetric`: `last_automation`
- `main_hostmetricsummarymonthly`: `created`

Custom mappings can be provided to `get_timestamp_column()`:

```python
custom_mapping = {
    'my_custom_table': 'updated_at',
}

timestamp_col = migration.get_timestamp_column('my_custom_table', custom_mapping=custom_mapping)
```

### Requirements

- PostgreSQL client tools: `pg_dump`, `pg_restore`, `psql`
- Python package: `psycopg` (psycopg3 or psycopg2)

### Notes

- Full migration creates both schema and data
- Incremental migration requires tables to already exist in destination
- Custom PostgreSQL functions are needed for some Controller data
- Source data is never deleted (copy operation only)
- Use `force=True` carefully in full migration - it drops existing tables
