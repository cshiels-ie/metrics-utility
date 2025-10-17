"""
Synchronous wrapper for existing CLI functionality
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Import existing functionality
from metrics_utility.automation_controller_billing.collector import Collector
from metrics_utility.automation_controller_billing.dataframe_engine.factory import Factory as DataframeFactory
from metrics_utility.automation_controller_billing.dedup.factory import Factory as DedupFactory
from metrics_utility.automation_controller_billing.extract.factory import Factory as ExtractorFactory
from metrics_utility.automation_controller_billing.report.factory import Factory as ReportFactory
from metrics_utility.automation_controller_billing.report_saver.factory import Factory as ReportSaverFactory
from metrics_utility.exceptions import (
    BadRequiredEnvVar,
    BadShipTarget,
    MissingRequiredEnvVar,
    NoAnalyticsCollected,
)
from metrics_utility.logger import logger

from .models import (
    CollectionConfig,
    CollectionResult,
    ReportConfig,
    ReportResult,
)


class SyncWrapper:
    """
    Wrapper for existing synchronous CLI functionality.

    This class adapts the existing CLI commands to work with the async library
    while preserving all functionality.
    """

    def run_collection(self, config: CollectionConfig) -> CollectionResult:
        """
        Run data collection using existing Collector class.

        Args:
            config: Collection configuration

        Returns:
            CollectionResult with operation details
        """
        try:
            # Create collector instance
            collector = Collector(ship_target=config.ship_target.value, billing_provider_params=self._get_billing_provider_params(config))

            # Prepare parameters
            since = config.since
            until = config.until

            # Run collection
            if config.dry_run:
                # For dry run, don't actually ship
                tarballs = collector.gather(since=since, until=until)
                message = 'Data collection completed (dry run - no shipping)'
            else:
                tarballs = collector.gather(since=since, until=until)
                message = 'Data collection and shipping completed successfully'

            # Handle results
            if tarballs is None:
                return CollectionResult(
                    success=False, message='Collection disabled or no data collected', errors=['Collector is disabled or returned no data']
                )

            return CollectionResult(
                success=True,
                message=message,
                tarballs=tarballs if isinstance(tarballs, list) else [tarballs],
                collected_data_info={
                    'since': since.isoformat() if since else None,
                    'until': until.isoformat() if until else None,
                    'ship_target': config.ship_target.value,
                    'ship_path': config.ship_path,
                    'dry_run': config.dry_run,
                },
            )

        except NoAnalyticsCollected as e:
            return CollectionResult(success=False, message='No analytics data collected', errors=[str(e)])
        except (BadShipTarget, BadRequiredEnvVar, MissingRequiredEnvVar) as e:
            return CollectionResult(success=False, message=f'Configuration error: {str(e)}', errors=[str(e)])
        except Exception as e:
            logger.exception('Collection failed with unexpected error')
            return CollectionResult(success=False, message=f'Collection failed: {str(e)}', errors=[str(e)])

    def run_report(self, config: ReportConfig) -> ReportResult:
        """
        Run report generation using existing factory classes.

        Args:
            config: Report configuration

        Returns:
            ReportResult with operation details
        """
        try:
            # Prepare extra parameters
            extra_params = self._get_report_extra_params(config)

            # Create extractor
            extractor_factory = ExtractorFactory(config.ship_target.value, extra_params)
            extractor = extractor_factory.create()

            # Extract data
            raw_data = extractor.extract()

            # Create dataframe engine
            dataframe_factory = DataframeFactory(raw_data, extra_params)
            dataframes = dataframe_factory.create()

            # Apply deduplication if configured
            if config.deduplicator:
                dedup_factory = DedupFactory(dataframes, extra_params)
                dataframes = dedup_factory.create()

            # Generate report
            report_factory = ReportFactory(dataframes, extra_params)
            report = report_factory.create()
            report_data = report.build()

            # Save report
            report_saver_factory = ReportSaverFactory(report_data, extra_params)
            report_saver = report_saver_factory.create()
            report_path = report_saver.save()

            return ReportResult(
                success=True,
                message='Report generated successfully',
                report_path=report_path,
                report_info={
                    'report_type': config.report_type.value,
                    'ship_target': config.ship_target.value,
                    'ship_path': config.ship_path,
                    'month': config.month,
                    'since': config.since.isoformat() if config.since else None,
                    'until': config.until.isoformat() if config.until else None,
                },
            )

        except (BadShipTarget, BadRequiredEnvVar, MissingRequiredEnvVar) as e:
            return ReportResult(success=False, message=f'Configuration error: {str(e)}', errors=[str(e)])
        except Exception as e:
            logger.exception('Report generation failed with unexpected error')
            return ReportResult(success=False, message=f'Report generation failed: {str(e)}', errors=[str(e)])

    def get_collection_status(self, ship_path: str) -> Dict[str, Any]:
        """
        Get status of collected data in the specified path.

        Args:
            ship_path: Path to check for collected data

        Returns:
            Dictionary with collection status information
        """
        try:
            data_path = Path(ship_path) / 'data'
            if not data_path.exists():
                return {'has_data': False, 'message': 'No data directory found'}

            # Count tarballs by year/month
            tarballs = []
            for year_dir in data_path.iterdir():
                if year_dir.is_dir() and year_dir.name.isdigit():
                    for month_dir in year_dir.iterdir():
                        if month_dir.is_dir() and month_dir.name.isdigit():
                            for day_dir in month_dir.iterdir():
                                if day_dir.is_dir() and day_dir.name.isdigit():
                                    for tarball in day_dir.glob('*.tar.gz'):
                                        tarballs.append(
                                            {
                                                'path': str(tarball),
                                                'year': year_dir.name,
                                                'month': month_dir.name,
                                                'day': day_dir.name,
                                                'size': tarball.stat().st_size,
                                                'modified': datetime.fromtimestamp(tarball.stat().st_mtime).isoformat(),
                                            }
                                        )

            return {'has_data': len(tarballs) > 0, 'tarball_count': len(tarballs), 'tarballs': tarballs, 'data_path': str(data_path)}

        except Exception as e:
            return {'has_data': False, 'error': str(e)}

    def list_available_reports(self, ship_path: str) -> List[Dict[str, Any]]:
        """
        List available reports in the specified path.

        Args:
            ship_path: Path to check for reports

        Returns:
            List of available reports with metadata
        """
        try:
            reports_path = Path(ship_path) / 'reports'
            if not reports_path.exists():
                return []

            reports = []
            for year_dir in reports_path.iterdir():
                if year_dir.is_dir() and year_dir.name.isdigit():
                    for month_dir in year_dir.iterdir():
                        if month_dir.is_dir() and month_dir.name.isdigit():
                            for report_file in month_dir.glob('*.xlsx'):
                                reports.append(
                                    {
                                        'path': str(report_file),
                                        'year': year_dir.name,
                                        'month': month_dir.name,
                                        'filename': report_file.name,
                                        'size': report_file.stat().st_size,
                                        'created': datetime.fromtimestamp(report_file.stat().st_ctime).isoformat(),
                                        'modified': datetime.fromtimestamp(report_file.stat().st_mtime).isoformat(),
                                    }
                                )

            return sorted(reports, key=lambda x: x['modified'], reverse=True)

        except Exception as e:
            logger.exception(f'Error listing reports: {e}')
            return []

    def _get_billing_provider_params(self, config: CollectionConfig) -> Dict[str, Any]:
        """Extract billing provider parameters from collection config"""
        params = {}

        if config.billing_account_id:
            params['billing_account_id'] = config.billing_account_id
        if config.billing_provider:
            params['billing_provider'] = config.billing_provider
        if config.red_hat_org_id:
            params['red_hat_org_id'] = config.red_hat_org_id

        return params

    def _get_report_extra_params(self, config: ReportConfig) -> Dict[str, Any]:
        """Extract extra parameters for report generation"""
        params = {
            'report_type': config.report_type.value,
            'ship_target': config.ship_target.value,
            'ship_path': config.ship_path,
        }

        # Time configuration
        if config.month:
            params['month'] = config.month
        if config.since:
            params['since'] = config.since
        if config.until:
            params['until'] = config.until
        if config.ephemeral:
            params['ephemeral'] = config.ephemeral

        # Report options
        params['force'] = config.force

        # Optional configuration
        if config.deduplicator:
            params['deduplicator'] = config.deduplicator.value
        if config.organization_filter:
            params['organization_filter'] = config.organization_filter
        if config.price_per_node:
            params['price_per_node'] = config.price_per_node
        if config.optional_ccsp_report_sheets:
            params['optional_ccsp_report_sheets'] = config.optional_ccsp_report_sheets

        return params
