import json
import os
import tarfile
import tempfile

from argparse import RawDescriptionHelpFormatter
from datetime import datetime

import requests

from django.core.management.base import BaseCommand

from metrics_utility.exceptions import BadShipTarget, MissingRequiredEnvVar
from metrics_utility.logger import debug, logger
from metrics_utility.management.validation import (
    date_format_text,
    handle_directory_ship_target,
    handle_not_crc,
    handle_not_s3,
    handle_s3_ship_target,
    parse_date_param,
)


class Command(BaseCommand):
    """
    Build Unified JSON Report from collected reports data
    """

    help = 'Build unified JSON report from collected reports data'
    help_texts = {
        'since': (f'Start date for report period, including. {date_format_text.format(name="since")}'),
        'until': (f'End date for report period, including. {date_format_text.format(name="until")}'),
        'endpoint': 'HTTP endpoint URL to send the unified JSON report to',
        'output': 'Output file path to save the unified JSON report',
        'dry-run': 'Generate report without sending to endpoint',
        'verbose': 'Print debug information to console',
    }

    def create_parser(self, prog_name, subcommand, **kwargs):
        return super().create_parser(
            prog_name,
            subcommand,
            formatter_class=RawDescriptionHelpFormatter,
            epilog='\n'.join(
                [
                    'UNIFIED JSON REPORT BUILDER',
                    '',
                    'This command aggregates collected JSON reports into a unified',
                    'JSON structure that can be sent to an HTTP endpoint or saved',
                    'to a file for further processing.',
                    '',
                    'The unified report includes all collected metrics:',
                    '• Cluster metrics (active clusters, versions)',
                    '• Job metrics (duration, success rates, counts)',
                    '• Module metrics (usage, success rates)',
                    '• Template metrics (execution statistics)',
                    '• Host metrics (automation counts)',
                    '• Execution environment metrics',
                    '',
                    'ENVIRONMENT',
                    '',
                    '  Core Configuration:',
                    "    METRICS_UTILITY_SHIP_TARGET (required): 'directory' or 's3'",
                    '    METRICS_UTILITY_SHIP_PATH (required): path to collected data',
                    '',
                    '  Endpoint Configuration:',
                    '    METRICS_UTILITY_ENDPOINT_URL (optional): default endpoint URL',
                    '    METRICS_UTILITY_ENDPOINT_TOKEN (optional): auth token',
                    '    METRICS_UTILITY_ENDPOINT_HEADERS (optional): JSON headers',
                    '',
                    '  Report Configuration:',
                    '    METRICS_UTILITY_REPORT_CUSTOMER_ID (optional): customer ID',
                    '    METRICS_UTILITY_REPORT_CLUSTER_ID (optional): cluster ID',
                    '    METRICS_UTILITY_REPORT_ENVIRONMENT (optional): environment',
                    '',
                    '  S3 Configuration:',
                    '    METRICS_UTILITY_BUCKET_NAME (optional): S3 bucket name',
                    '    METRICS_UTILITY_BUCKET_ENDPOINT (optional): S3 endpoint URL',
                    '    METRICS_UTILITY_BUCKET_ACCESS_KEY (optional): S3 access key',
                    '    METRICS_UTILITY_BUCKET_SECRET_KEY (optional): S3 secret key',
                    '    METRICS_UTILITY_BUCKET_REGION (optional): S3 region',
                ]
            ),
            **kwargs,
        )

    def add_arguments(self, parser):
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
            '--endpoint',
            dest='endpoint',
            action='store',
            help=self.help_texts.get('endpoint'),
        )
        parser.add_argument(
            '--output',
            dest='output',
            action='store',
            help=self.help_texts.get('output'),
        )
        parser.add_argument(
            '--dry-run',
            dest='dry-run',
            action='store_true',
            help=self.help_texts.get('dry-run'),
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

        logger.info('Starting Unified JSON Report Builder')

        # Custom validation for JSON reports (don't need REPORT_TYPE)
        ship_target = os.getenv('METRICS_UTILITY_SHIP_TARGET')
        if not ship_target:
            raise MissingRequiredEnvVar('Missing required env variable METRICS_UTILITY_SHIP_TARGET')

        ship_path = os.getenv('METRICS_UTILITY_SHIP_PATH')
        if not ship_path:
            raise MissingRequiredEnvVar('Missing required env variable METRICS_UTILITY_SHIP_PATH')

        opt_since = options.get('since')
        opt_until = options.get('until')
        opt_endpoint = options.get('endpoint')
        opt_output = options.get('output')
        opt_dry_run = options.get('dry-run')

        # Parse dates
        since = parse_date_param(opt_since, self.help_texts, 'since') if opt_since else None
        until = parse_date_param(opt_until, self.help_texts, 'until') if opt_until else None

        # Handle ship target
        extra_params = self._handle_ship_target(ship_target)

        # Find and extract JSON reports
        logger.info('Searching for collected reports data...')
        json_data = self._find_and_extract_reports(extra_params, since, until)

        if not json_data:
            logger.error('No reports data found')
            return

        # Build unified report
        logger.info('Building unified JSON report...')
        unified_report = self._build_unified_report(json_data, since, until)

        # Save to file if requested
        if opt_output:
            logger.info(f'Saving unified report to: {opt_output}')
            os.makedirs(os.path.dirname(opt_output), exist_ok=True)
            with open(opt_output, 'w') as f:
                json.dump(unified_report, f, indent=2, default=str)
            logger.info(f'Report saved to: {opt_output}')

        # Send to endpoint if requested and not dry-run
        endpoint_url = opt_endpoint or os.getenv('METRICS_UTILITY_ENDPOINT_URL')

        if endpoint_url:
            if opt_dry_run:
                logger.info(f'DRY RUN: Would send report to endpoint: {endpoint_url}')
                logger.info(f'Report size: {len(json.dumps(unified_report, default=str))} bytes')
            else:
                logger.info(f'Sending unified report to endpoint: {endpoint_url}')
                self._send_to_endpoint(unified_report, endpoint_url)
        else:
            logger.info('No endpoint specified, report generated locally only')

        # Show summary
        self._show_report_summary(unified_report)

    def _find_and_extract_reports(self, extra_params, since=None, until=None):
        """Find and extract JSON reports from collected data."""
        ship_path = extra_params['ship_path']
        data_path = os.path.join(ship_path, 'data')

        if not os.path.exists(data_path):
            logger.error(f'Data path does not exist: {data_path}')
            return None

        # Find tar.gz files
        tar_files = []
        for root, dirs, files in os.walk(data_path):
            for file in files:
                if file.endswith('.tar.gz'):
                    tar_files.append(os.path.join(root, file))

        if not tar_files:
            logger.error(f'No tar.gz files found in: {data_path}')
            return None

        logger.info(f'Found {len(tar_files)} tar.gz files')

        # Filter by date if specified
        if since or until:
            from django.utils import timezone

            filtered_files = []
            for tar_file in tar_files:
                file_time = datetime.fromtimestamp(os.path.getmtime(tar_file))
                # Make file_time timezone aware
                file_time = timezone.make_aware(file_time)
                if since and file_time < since:
                    continue
                if until and file_time > until:
                    continue
                filtered_files.append(tar_file)
            tar_files = filtered_files
            logger.info(f'Filtered to {len(tar_files)} files by date range')

        # Extract JSON from tar files
        all_json_data = {}

        with tempfile.TemporaryDirectory() as temp_dir:
            for tar_file in tar_files:
                logger.info(f'Processing: {os.path.basename(tar_file)}')

                try:
                    with tarfile.open(tar_file, 'r:gz') as tar:
                        # Extract all files
                        tar.extractall(temp_dir)

                        # Find JSON files (skip macOS metadata files)
                        for member in tar.getmembers():
                            if member.name.endswith('.json') and member.isfile() and not member.name.startswith('._'):
                                json_file_path = os.path.join(temp_dir, member.name)
                                if os.path.exists(json_file_path):
                                    try:
                                        with open(json_file_path, 'r') as f:
                                            data = json.load(f)

                                        # Use filename (without .json) as key
                                        key = os.path.splitext(member.name)[0]

                                        # If we already have data for this key, append or merge
                                        if key in all_json_data:
                                            # For lists, extend; for dicts, update
                                            if isinstance(data, dict) and isinstance(all_json_data[key], dict):
                                                all_json_data[key].update(data)
                                            elif isinstance(data, list) and isinstance(all_json_data[key], list):
                                                all_json_data[key].extend(data)
                                            else:
                                                # Use the newer data
                                                all_json_data[key] = data
                                        else:
                                            all_json_data[key] = data

                                    except json.JSONDecodeError as e:
                                        logger.warning(f'Invalid JSON in {member.name}: {e}')
                                    except Exception as e:
                                        logger.warning(f'Error reading {member.name}: {e}')

                except Exception as e:
                    logger.error(f'Error processing {tar_file}: {e}')
                    continue

        logger.info(f'Extracted data from {len(all_json_data)} JSON files')
        return all_json_data

    def _build_unified_report(self, json_data, since=None, until=None):
        """Build unified report from extracted JSON data."""

        # Get metadata from config if available
        config_data = json_data.get('config', {})

        # Build the unified report structure
        unified_report = {
            'report_metadata': {
                'report_type': 'awx_unified_json_report',
                'report_version': '1.0',
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'collector_version': config_data.get('version', 'unknown'),
                'collector_module': config_data.get('module', 'reports_collectors'),
                'period_start': since.isoformat() if since else None,
                'period_end': until.isoformat() if until else None,
                'customer_id': os.getenv('METRICS_UTILITY_REPORT_CUSTOMER_ID'),
                'cluster_id': os.getenv('METRICS_UTILITY_REPORT_CLUSTER_ID'),
                'environment': os.getenv('METRICS_UTILITY_REPORT_ENVIRONMENT'),
                'total_json_files': len(json_data),
            },
            'cluster_metrics': {
                'active_clusters': json_data.get('active_clusters_count', {}),
                'clusters_by_version': json_data.get('active_clusters_by_controller_version', {}),
            },
            'job_metrics': {
                'execution_stats': json_data.get('job_execution_stats', {}),
                'duration_stats_by_template': json_data.get('job_duration_stats_by_template', {}),
                'avg_tasks_by_template': json_data.get('avg_tasks_by_template', {}),
            },
            'task_metrics': {
                'execution_stats': json_data.get('task_execution_stats', {}),
            },
            'module_metrics': {
                'total_automated': json_data.get('total_modules_automated', {}),
                'success_failure_rates': json_data.get('module_success_failure_rates', {}),
                'usage_by_job': json_data.get('modules_usage_by_job_kpi', {}),
                'modules_used': json_data.get('modules_used_to_automate', {}),
                'avg_per_playbook': json_data.get('avg_modules_per_playbook', {}),
            },
            'template_metrics': {
                'executed_by_company': json_data.get('templates_executed_by_company', {}),
            },
            'host_metrics': {
                'automated_over_time': json_data.get('total_hosts_automated_over_time', {}),
            },
            'execution_environment_metrics': {
                'stats': json_data.get('execution_environment_stats', {}),
            },
            'raw_data': {
                'manifest': json_data.get('manifest', {}),
                'config': config_data,
            },
        }

        return unified_report

    def _send_to_endpoint(self, unified_report, endpoint_url):
        """Send unified report to HTTP endpoint."""
        try:
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'AWX-Reports-Collector/1.0',
            }

            # Add auth token if available
            auth_token = os.getenv('METRICS_UTILITY_ENDPOINT_TOKEN')
            if auth_token:
                headers['Authorization'] = f'Bearer {auth_token}'

            # Add custom headers if specified
            custom_headers = os.getenv('METRICS_UTILITY_ENDPOINT_HEADERS')
            if custom_headers:
                try:
                    custom_headers_dict = json.loads(custom_headers)
                    headers.update(custom_headers_dict)
                except json.JSONDecodeError:
                    logger.warning('Invalid JSON in METRICS_UTILITY_ENDPOINT_HEADERS')

            # Send the request
            logger.info('Sending POST request to endpoint...')
            response = requests.post(
                endpoint_url,
                json=unified_report,
                headers=headers,
                timeout=60,
            )

            if response.status_code == 200:
                logger.info('✅ Successfully sent report to endpoint')
                logger.info(f'Response: {response.text[:200]}...')
            else:
                logger.error(f'❌ Endpoint returned status {response.status_code}')
                logger.error(f'Response: {response.text[:500]}...')

        except requests.exceptions.RequestException as e:
            logger.error(f'❌ Failed to send report to endpoint: {e}')
        except Exception as e:
            logger.error(f'❌ Unexpected error sending report: {e}')

    def _show_report_summary(self, unified_report):
        """Show summary of the unified report."""
        logger.info('📊 Unified Report Summary:')
        logger.info(f'   Report Type: {unified_report["report_metadata"]["report_type"]}')
        logger.info(f'   Generated At: {unified_report["report_metadata"]["generated_at"]}')

        period_start = unified_report['report_metadata']['period_start']
        period_end = unified_report['report_metadata']['period_end']
        if period_start and period_end:
            logger.info(f'   Period: {period_start} to {period_end}')

        logger.info(f'   Total JSON Files: {unified_report["report_metadata"]["total_json_files"]}')

        # Show metrics summary
        logger.info('📋 Metrics Included:')
        metrics_sections = [
            'cluster_metrics',
            'job_metrics',
            'task_metrics',
            'module_metrics',
            'template_metrics',
            'host_metrics',
            'execution_environment_metrics',
        ]

        for section in metrics_sections:
            if section in unified_report:
                section_data = unified_report[section]
                non_empty_keys = [k for k, v in section_data.items() if v]
                if non_empty_keys:
                    logger.info(f'   • {section}: {len(non_empty_keys)} datasets')

        total_size = len(json.dumps(unified_report, default=str))
        logger.info(f'📏 Total Report Size: {total_size:,} bytes')

    def _handle_ship_target(self, ship_target):
        """Handle ship target configuration."""
        if ship_target == 'directory':
            handle_not_crc()
            handle_not_s3()
            return handle_directory_ship_target()
        elif ship_target == 's3':
            handle_not_crc()
            return handle_s3_ship_target()
        else:
            allowed = ', '.join(['directory', 's3'])
            raise BadShipTarget(f'Unexpected value for METRICS_UTILITY_SHIP_TARGET env var ({ship_target}), allowed values: {allowed}')
