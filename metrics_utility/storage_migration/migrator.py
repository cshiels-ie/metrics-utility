import os
import tempfile

from django.db import connection

from metrics_utility.exceptions import MetricsException
from metrics_utility.library import migration
from metrics_utility.logger import logger
from metrics_utility.storage_migration.connection import build_pg_connection_string, get_psycopg_connection


class TableMigrator:
    """
    Migrates PostgreSQL tables from Controller to storage database.

    Supports both full migration (entire table) and incremental sync (time-windowed data).
    """

    def __init__(self, source_params, dest_params, mode='full', since=None, until=None, force=False):
        """
        Initialize TableMigrator.

        Args:
            source_params (dict): Source database parameters (host, port, name, user, password)
            dest_params (dict): Destination database parameters
            mode (str): Migration mode - 'full' or 'incremental'
            since (datetime): Start date for incremental sync (inclusive)
            until (datetime): End date for incremental sync (exclusive)
            force (bool): Drop and recreate tables if they exist
        """
        self.source_params = source_params
        self.dest_params = dest_params
        self.mode = mode
        self.since = since
        self.until = until
        self.force = force

        # Build connection strings
        self.source_conn_str = build_pg_connection_string(**source_params)
        self.dest_conn_str = build_pg_connection_string(**dest_params)

    def discover_tables(self):
        """
        Discover all main_* tables in the source database.

        Returns:
            list: Table names sorted alphabetically
        """
        # Use library function with Django connection
        tables = migration.discover_tables(connection, pattern='main_%')
        logger.info(f'Discovered {len(tables)} main_* tables in source database')
        return tables

    def get_timestamp_column(self, table_name):
        """
        Get the timestamp column name for a table (for incremental sync).

        Args:
            table_name (str): Name of the table

        Returns:
            str or None: Timestamp column name, or None if table doesn't support incremental sync
        """
        return migration.get_timestamp_column(table_name)

    def create_custom_functions(self):
        """
        Create custom PostgreSQL functions in the destination database.

        These functions are used by some collectors and need to exist before data migration.
        """
        logger.info('Creating custom PostgreSQL functions in destination database...')

        try:
            dest_conn = get_psycopg_connection(self.dest_params)
            success, error = migration.create_custom_functions(dest_conn)
            dest_conn.close()

            if not success:
                raise MetricsException(error)

            logger.info('Custom PostgreSQL functions created successfully')
        except Exception as e:
            raise MetricsException(f'Failed to create custom functions: {str(e)}')

    def check_existing_tables(self, tables):
        """
        Check which tables already exist in the destination database.

        Args:
            tables (list): List of table names to check

        Returns:
            dict: Map of table_name -> row_count for existing tables
        """
        existing = {}

        try:
            dest_conn = get_psycopg_connection(self.dest_params)

            for table in tables:
                exists, row_count = migration.check_table_exists(dest_conn, table, schema=self.dest_params.get('schema', 'public'))
                if exists:
                    existing[table] = row_count

            dest_conn.close()

        except Exception as e:
            logger.warning(f'Error checking existing tables: {str(e)}')

        return existing

    def migrate_table_full(self, table_name, temp_dir):
        """
        Perform full table migration using pg_dump/pg_restore.

        Args:
            table_name (str): Name of the table to migrate
            temp_dir (str): Temporary directory for intermediate files (not used - library handles temp)

        Returns:
            tuple: (success: bool, message: str)
        """
        logger.info(f'Starting full migration for table: {table_name}')

        # Use library function
        success, message, row_count = migration.migrate_table_full(table_name, self.source_conn_str, self.dest_conn_str, force=self.force)

        if success:
            logger.info(f'Completed full migration for table: {table_name} ({row_count} rows)')
        else:
            logger.error(f'Failed to migrate {table_name}: {message}')

        return (success, message)

    def migrate_table_incremental(self, table_name):
        """
        Perform incremental table migration using COPY.

        Args:
            table_name (str): Name of the table to migrate

        Returns:
            tuple: (success: bool, message: str)
        """
        timestamp_col = self.get_timestamp_column(table_name)

        if not timestamp_col:
            msg = f'Skipping {table_name} - no timestamp column defined for incremental sync'
            logger.warning(msg)
            return (False, msg)

        logger.info(f'Starting incremental migration for table: {table_name} (filtering on {timestamp_col})')

        # Get database connections
        source_db = connection  # Django connection
        dest_conn = get_psycopg_connection(self.dest_params)

        # Use library function
        success, message, row_count = migration.migrate_table_incremental(
            table_name, source_db, dest_conn, self.since, self.until, timestamp_column=timestamp_col
        )

        dest_conn.close()

        if success:
            if row_count == 0:
                logger.info(f'No new data to migrate for {table_name} in the specified time range')
            else:
                logger.info(f'Completed incremental migration for table: {table_name} ({row_count} rows)')
        else:
            logger.error(f'Failed incremental migration for {table_name}: {message}')

        return (success, f'{message} ({row_count} rows)' if row_count is not None else message)

    def migrate(self, tables):
        """
        Migrate all specified tables.

        Args:
            tables (list): List of table names to migrate

        Returns:
            dict: Migration results - table_name -> (success, message)
        """
        results = {}

        # Create temporary directory for full migrations
        temp_dir = None
        if self.mode == 'full':
            temp_dir = tempfile.mkdtemp(prefix='metrics_migration_')
            logger.info(f'Using temporary directory: {temp_dir}')

        try:
            # Create custom functions first
            if self.mode == 'full':
                self.create_custom_functions()

            # Check existing tables
            existing = self.check_existing_tables(tables)

            if existing and self.mode == 'full' and not self.force:
                raise MetricsException(f'Tables already exist in destination: {", ".join(existing.keys())}\nUse --force to drop and recreate them')

            # Migrate each table
            for table in tables:
                if self.mode == 'full':
                    success, message = self.migrate_table_full(table, temp_dir)
                else:
                    success, message = self.migrate_table_incremental(table)

                results[table] = {'success': success, 'message': message}

        finally:
            # Clean up temp directory
            if temp_dir and os.path.exists(temp_dir):
                import shutil

                shutil.rmtree(temp_dir)
                logger.info(f'Cleaned up temporary directory: {temp_dir}')

        return results

    def validate_migration(self, tables):
        """
        Validate migration by comparing row counts between source and destination.

        Args:
            tables (list): List of table names to validate

        Returns:
            dict: Validation results - table_name -> {source_count, dest_count, match}
        """
        logger.info('Validating migration...')
        validation_results = {}

        try:
            dest_conn = get_psycopg_connection(self.dest_params)

            for table in tables:
                # Use library function
                result = migration.validate_migration(connection, dest_conn, table)
                validation_results[table] = result

                if not result['match']:
                    logger.warning(
                        f'Row count mismatch for {table}: source={result["source_count"]}, dest={result["dest_count"]} (diff={result["difference"]})'
                    )
                else:
                    logger.info(f'Validation passed for {table}: {result["source_count"]} rows')

            dest_conn.close()

        except Exception as e:
            logger.error(f'Validation error: {str(e)}')

        return validation_results
