import os

from argparse import RawDescriptionHelpFormatter

from django.core.management.base import BaseCommand

from metrics_utility.automation_controller_billing import reports_collectors
from metrics_utility.automation_controller_billing.collector import Collector
from metrics_utility.exceptions import (
    BadShipTarget,
    NoAnalyticsCollected,
)
from metrics_utility.logger import debug, logger
from metrics_utility.management.validation import (
    date_format_text,
    handle_crc_ship_target,
    handle_directory_ship_target,
    handle_env_validation,
    handle_not_crc,
    handle_not_s3,
    handle_s3_ship_target,
    parse_date_param,
)


class Command(BaseCommand):
    """
    Gather Automation Controller reports data - JSON output for comprehensive
    reporting
    """

    help = 'Gather Automation Controller reports data (JSON format)'
    help_texts = {
        'since': (f'Start date for collection, including. {date_format_text.format(name="since")}'),
        'until': (f'End date for collection, excluding. {date_format_text.format(name="until")}'),
        'dry-run': ('Gather reports metrics without shipping.'),
        'ship': ('Enable shipping of reports metrics to console.redhat.com'),
        'verbose': ('Print debug information to console.'),
    }

    def create_parser(self, prog_name, subcommand, **kwargs):
        epilog_lines = [
            'REPORTS COLLECTOR - JSON OUTPUT',
            '',
            'This command generates comprehensive JSON-based reports:',
            '• Active number of clusters',
            '• Active clusters by controller version',
            '• Total number of modules automated',
            '• Job duration statistics by template (avg/min/max/total)',
            '• Average tasks by template',
            '• Job execution statistics (success/failure/total)',
            '• Task execution statistics and success ratios',
            '• Module success/failure rates',
            '• KPI - modules used across customers grouped by job ID',
            '• Number of templates executed by organization',
            '• Total number of hosts automated over time',
            '• Execution environment statistics and ratios',
            '• Modules used to automate analysis',
            '• Average number of modules used in playbooks',
            '',
            'OUTPUT: JSON files instead of CSV for easier integration',
            'with dashboards and reporting tools.',
            '',
            'ENVIRONMENT',
            '',
            '  Core Configuration:',
            "    METRICS_UTILITY_SHIP_TARGET (required): 'crc', 'directory'",
            '    METRICS_UTILITY_SHIP_PATH (required): directory path',
            '',
            '  Collection Configuration:',
            '    METRICS_UTILITY_CLUSTER_NAME (optional): cluster name',
            '    METRICS_UTILITY_COLLECTOR_LOCK_SUFFIX (optional): custom lock',
            '    METRICS_UTILITY_MAX_GATHER_PERIOD_DAYS (optional): max days',
            '',
            '  Billing Provider Configuration:',
            '    METRICS_UTILITY_BILLING_ACCOUNT_ID (optional): AWS account ID',
            '    METRICS_UTILITY_BILLING_PROVIDER (optional): billing provider',
            '    METRICS_UTILITY_RED_HAT_ORG_ID (optional): Red Hat org ID',
            '',
            '  S3 Configuration:',
            '    METRICS_UTILITY_BUCKET_NAME (optional): S3 bucket name',
            '    METRICS_UTILITY_BUCKET_ENDPOINT (optional): S3 endpoint URL',
            '    METRICS_UTILITY_BUCKET_ACCESS_KEY (optional): S3 access key',
            '    METRICS_UTILITY_BUCKET_SECRET_KEY (optional): S3 secret key',
            '    METRICS_UTILITY_BUCKET_REGION (optional): S3 region',
            '',
            '  CRC Configuration:',
            '    METRICS_UTILITY_CRC_INGRESS_URL (optional): CRC upload URL',
            '    METRICS_UTILITY_CRC_SSO_URL (optional): CRC login URL',
            '    METRICS_UTILITY_PROXY_URL (optional): upload proxy URL',
            '    METRICS_UTILITY_SERVICE_ACCOUNT_ID (optional): service account',
            '    METRICS_UTILITY_SERVICE_ACCOUNT_SECRET (optional): secret',
        ]

        return super().create_parser(
            prog_name,
            subcommand,
            # ensure newlines are preserved in descriptions and epilog
            formatter_class=RawDescriptionHelpFormatter,
            epilog='\n'.join(epilog_lines),
            **kwargs,
        )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            dest='dry-run',
            action='store_true',
            help=self.help_texts.get('dry-run'),
        )
        parser.add_argument('--ship', dest='ship', action='store_true', help=self.help_texts.get('ship'))
        parser.add_argument(
            '--since',
            dest='since',
            action='store',
            help=self.help_texts.get('since'),
        )
        parser.add_argument(
            '--until',
            dest='until',
            action='store',
            help=self.help_texts.get('until'),
        )
        parser.add_argument(
            '--verbose',
            dest='verbose',
            action='store_true',
            help=self.help_texts.get('verbose'),
        )

    def handle(self, *args, **options):
        if options.get('verbose'):
            debug()

        logger.info('Starting Automation Controller Reports Data Collection (JSON)')
        logger.info('This collector provides comprehensive reporting metrics in JSON format')

        handle_env_validation('gather')

        opt_since = options.get('since')
        opt_until = options.get('until')
        opt_ship = options.get('ship')
        opt_dry_run = options.get('dry-run')

        since = parse_date_param(opt_since, self.help_texts, 'since')
        until = parse_date_param(opt_until, self.help_texts, 'until')

        ship_target = os.getenv('METRICS_UTILITY_SHIP_TARGET')
        extra_params = self._handle_ship_target(ship_target)

        if opt_ship and opt_dry_run:
            logger.error('Arguments --ship and --dry-run cannot be processed at the same time, set only one of these.')
            return

        # Create collector with reports_collectors module
        collector = Collector(
            collection_type=(Collector.MANUAL_COLLECTION if opt_ship else Collector.DRY_RUN),
            collector_module=reports_collectors,
            ship_target=ship_target,
            billing_provider_params=extra_params,
        )

        logger.info('Collection period: %s to %s', since, until)
        logger.info('Collecting comprehensive reporting metrics...')

        # List available collectors
        self._log_available_collectors()

        tgzfiles = collector.gather(since=since, until=until, billing_provider_params=extra_params)

        if not tgzfiles:
            logger.error('No analytics collected')
            raise NoAnalyticsCollected('No analytics collected')

        if tgzfiles:
            logger.info('Reports analytics collected successfully')
            logger.info('Output format: JSON files for easy integration with reporting tools')
            if opt_dry_run:
                logger.info('DRY RUN: Files available in temporary directory (not shipped)')
            if opt_ship:
                logger.info('Reports data shipped to configured target')

    def _log_available_collectors(self):
        """Log information about available collectors in the reports module."""
        import inspect

        functions = []
        for name, obj in inspect.getmembers(reports_collectors):
            if inspect.isfunction(obj) and hasattr(obj, '__insights_analytics_key__'):
                functions.append(
                    {
                        'name': name,
                        'key': obj.__insights_analytics_key__,
                        'description': obj.__insights_analytics_description__ or 'No description',
                        'format': obj.__insights_analytics_type__,
                    }
                )

        logger.info('Available collectors (%s total):', len(functions))
        for func in functions:
            logger.info('  • %s (%s)', func['key'], func['format'])

    def _handle_ship_target(self, ship_target):
        ship_target = 'directory'
        if ship_target == 'crc':
            handle_not_s3()
            return handle_crc_ship_target()
        elif ship_target == 'directory':
            handle_not_crc()
            handle_not_s3()
            return handle_directory_ship_target()
        elif ship_target == 's3':
            handle_not_crc()
            return handle_s3_ship_target()
        else:
            allowed = ', '.join(['crc', 'directory', 's3'])
            raise BadShipTarget(f'Unexpected value for METRICS_UTILITY_SHIP_TARGET env var ({ship_target}), allowed values: {allowed}')
