from argparse import RawDescriptionHelpFormatter

from django.core.management.base import BaseCommand

from metrics_utility.exceptions import MetricsException
from metrics_utility.logger import debug, logger
from metrics_utility.management.validation import date_format_text, handle_storage_db_params, parse_date_param
from metrics_utility.storage_migration import (
    TableMigrator,
    check_pg_tools,
    get_controller_db_params,
    validate_connections,
)


class Command(BaseCommand):
    """
    Migrate PostgreSQL tables from Controller to long-term storage database
    """

    help = 'Migrate Controller database tables to long-term storage database'

    help_texts = {
        'since': (f'Start date for incremental sync (inclusive). Triggers incremental mode. {date_format_text.format(name="since")}'),
        'until': (f'End date for incremental sync (exclusive). {date_format_text.format(name="until")} Defaults to now if not specified.'),
        'tables': (
            'Comma-separated list of specific tables to migrate. '
            'If not specified, all main_* tables will be discovered and migrated. '
            'Example: --tables=main_host,main_inventory,main_organization'
        ),
        'mode': (
            'Migration mode: "full" or "incremental". '
            'If not specified, mode is auto-detected based on --since parameter. '
            'Full mode migrates entire tables. Incremental mode migrates only time-windowed data.'
        ),
        'dry-run': (
            'Validate connections and display migration plan without executing the migration. '
            'Use this to verify setup before running actual migration.'
        ),
        'force': (
            'Drop and recreate tables in destination database if they already exist. '
            'USE WITH CAUTION - This will delete existing data in destination tables. '
            'Only applies to full migration mode.'
        ),
        'verbose': 'Print debug information to console.',
    }

    def create_parser(self, prog_name, subcommand, **kwargs):
        return super().create_parser(
            prog_name,
            subcommand,
            formatter_class=RawDescriptionHelpFormatter,
            epilog='\n'.join(
                [
                    'DESCRIPTION',
                    '',
                    '  This command migrates PostgreSQL tables from the Controller database to a',
                    '  long-term storage database using pg_dump and pg_restore.',
                    '',
                    '  Two migration modes are supported:',
                    '    - Full mode: Migrates entire tables with schema and all data',
                    '    - Incremental mode: Migrates only data within a time window',
                    '',
                    'ENVIRONMENT',
                    '',
                    '  Storage Database Configuration (Required):',
                    '    METRICS_UTILITY_STORAGE_DB_HOST - Storage database hostname',
                    '    METRICS_UTILITY_STORAGE_DB_NAME - Storage database name',
                    '    METRICS_UTILITY_STORAGE_DB_USER - Storage database username',
                    '    METRICS_UTILITY_STORAGE_DB_PASSWORD - Storage database password',
                    '',
                    '  Storage Database Configuration (Optional):',
                    '    METRICS_UTILITY_STORAGE_DB_PORT - Storage database port (default: 5432)',
                    '    METRICS_UTILITY_STORAGE_DB_SCHEMA - Target schema name (default: public)',
                    '',
                    '  Source Database Configuration (Optional):',
                    '    These override Django database settings if needed:',
                    '    METRICS_UTILITY_DB_HOST - Controller database hostname',
                    '    METRICS_UTILITY_DB_PORT - Controller database port',
                    '    METRICS_UTILITY_DB_NAME - Controller database name',
                    '    METRICS_UTILITY_DB_USER - Controller database username',
                    '    METRICS_UTILITY_DB_PASSWORD - Controller database password',
                    '',
                    'EXAMPLES',
                    '',
                    '  Initial full load (all tables):',
                    '    export METRICS_UTILITY_STORAGE_DB_HOST=storage.example.com',
                    '    export METRICS_UTILITY_STORAGE_DB_NAME=metrics_storage',
                    '    export METRICS_UTILITY_STORAGE_DB_USER=storage_user',
                    '    export METRICS_UTILITY_STORAGE_DB_PASSWORD=secret',
                    '    python manage.py migrate_to_storage --mode=full --verbose',
                    '',
                    '  Incremental sync (last year):',
                    '    python manage.py migrate_to_storage --since=1year --verbose',
                    '',
                    '  Sync specific tables (last 30 days):',
                    '    python manage.py migrate_to_storage --since=30d \\',
                    '      --tables=main_host,main_inventory --verbose',
                    '',
                    '  Dry run (test without migrating):',
                    '    python manage.py migrate_to_storage --since=30d --dry-run --verbose',
                    '',
                    'REQUIREMENTS',
                    '',
                    '  PostgreSQL client tools must be installed:',
                    '    - pg_dump',
                    '    - pg_restore',
                    '    - psql',
                    '',
                    'NOTES',
                    '',
                    '  - Full mode creates schema and migrates all data',
                    '  - Incremental mode only works for tables with timestamp columns',
                    '  - Custom PostgreSQL functions are created in full mode',
                    '  - Source data is never deleted (copy operation, not move)',
                    '  - Use --force carefully as it will drop existing destination tables',
                ]
            ),
            **kwargs,
        )

    def add_arguments(self, parser):
        parser.add_argument('--since', dest='since', action='store', help=self.help_texts.get('since'))
        parser.add_argument('--until', dest='until', action='store', help=self.help_texts.get('until'))
        parser.add_argument('--tables', dest='tables', action='store', help=self.help_texts.get('tables'))
        parser.add_argument('--mode', dest='mode', action='store', choices=['full', 'incremental'], help=self.help_texts.get('mode'))
        parser.add_argument('--dry-run', dest='dry-run', action='store_true', help=self.help_texts.get('dry-run'))
        parser.add_argument('--force', dest='force', action='store_true', help=self.help_texts.get('force'))
        parser.add_argument('--verbose', dest='verbose', action='store_true', help=self.help_texts.get('verbose'))

    def handle(self, *args, **options):
        # Enable debug logging if requested
        if options.get('verbose'):
            debug()

        logger.info('=== PostgreSQL Table Migration to Storage ===')

        # Parse command-line options
        opt_since = options.get('since')
        opt_until = options.get('until')
        opt_tables = options.get('tables')
        opt_mode = options.get('mode')
        opt_dry_run = options.get('dry-run')
        opt_force = options.get('force')

        # Parse dates
        since = parse_date_param(opt_since, self.help_texts, 'since')
        until = parse_date_param(opt_until, self.help_texts, 'until')

        # Determine mode
        if opt_mode:
            mode = opt_mode
        else:
            # Auto-detect mode based on --since
            mode = 'incremental' if since else 'full'

        logger.info(f'Migration mode: {mode}')

        # Validate mode and parameters
        if mode == 'incremental' and not since:
            raise MetricsException('Incremental mode requires --since parameter')

        if mode == 'full' and since and not opt_mode:
            logger.warning('Using incremental mode because --since was provided. Use --mode=full to force full migration.')

        # Parse table list
        if opt_tables:
            tables = [t.strip() for t in opt_tables.split(',')]
            logger.info(f'Migrating specific tables: {", ".join(tables)}')
        else:
            tables = None
            logger.info('Will discover all main_* tables automatically')

        # Check for PostgreSQL client tools
        logger.info('Checking PostgreSQL client tools...')
        check_pg_tools()

        # Get database parameters
        logger.info('Loading database configuration...')
        source_params = get_controller_db_params()
        dest_params = handle_storage_db_params()  # This validates required env vars

        logger.info(f'Source database: {source_params["host"]}:{source_params["port"]}/{source_params["name"]}')
        logger.info(f'Destination database: {dest_params["host"]}:{dest_params["port"]}/{dest_params["name"]}')

        # Validate database connections
        logger.info('Validating database connections...')
        validate_connections(source_params, dest_params)

        # Create migrator
        migrator = TableMigrator(source_params=source_params, dest_params=dest_params, mode=mode, since=since, until=until, force=opt_force)

        # Discover tables if not specified
        if not tables:
            tables = migrator.discover_tables()

        if not tables:
            logger.error('No tables to migrate')
            return

        logger.info(f'Tables to migrate: {len(tables)}')

        # Check existing tables in destination
        if mode == 'full':
            existing = migrator.check_existing_tables(tables)
            if existing:
                logger.warning(f'Found {len(existing)} existing tables in destination:')
                for table, count in existing.items():
                    logger.warning(f'  {table}: {count} rows')

                if not opt_force:
                    logger.error(
                        'Tables already exist in destination. Use --force to drop and recreate them, or use incremental mode to append data.'
                    )
                    raise MetricsException('Destination tables already exist')

        # Display migration plan
        self._display_migration_plan(mode, tables, since, until, opt_force)

        # Exit if dry run
        if opt_dry_run:
            logger.info('=== Dry run complete - no migration performed ===')
            return

        # Execute migration
        logger.info('=== Starting migration ===')
        results = migrator.migrate(tables)

        # Display results
        logger.info('=== Migration Results ===')
        success_count = sum(1 for r in results.values() if r['success'])
        failed_count = len(results) - success_count

        for table, result in results.items():
            status = 'SUCCESS' if result['success'] else 'FAILED'
            logger.info(f'{table}: {status} - {result["message"]}')

        logger.info(f'Successful: {success_count}/{len(results)}')
        if failed_count > 0:
            logger.warning(f'Failed: {failed_count}/{len(results)}')

        # Validate migration (for successful tables only)
        if mode == 'full' and success_count > 0:
            successful_tables = [t for t, r in results.items() if r['success']]
            logger.info('=== Validating Migration ===')
            validation = migrator.validate_migration(successful_tables)

            mismatches = [t for t, v in validation.items() if not v['match']]
            if mismatches:
                logger.warning(f'Row count mismatches found in {len(mismatches)} tables')
            else:
                logger.info('All row counts match between source and destination')

        logger.info('=== Migration Complete ===')

        if failed_count > 0:
            raise MetricsException(f'Migration completed with {failed_count} failures')

    def _display_migration_plan(self, mode, tables, since, until, force):
        """Display the migration plan to the user."""
        logger.info('=== Migration Plan ===')
        logger.info(f'Mode: {mode}')
        logger.info(f'Tables: {len(tables)}')

        if mode == 'incremental':
            logger.info(f'Time window: {since.isoformat() if since else "beginning"} to {until.isoformat() if until else "now"}')
            logger.info('Note: Only tables with timestamp columns will be migrated')
            logger.info('Tables without timestamp columns will be skipped')
        else:
            logger.info('Full table migration (schema + all data)')
            if force:
                logger.warning('FORCE MODE: Existing tables will be dropped and recreated')

        # Show first few tables
        display_count = 10
        if len(tables) <= display_count:
            for table in tables:
                logger.info(f'  - {table}')
        else:
            for table in tables[:display_count]:
                logger.info(f'  - {table}')
            logger.info(f'  ... and {len(tables) - display_count} more tables')
