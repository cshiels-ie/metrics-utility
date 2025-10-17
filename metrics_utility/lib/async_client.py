"""
Async client for metrics utility operations
"""

import asyncio
import time

from typing import Any, Dict, List

from .environment import EnvironmentManager
from .models import (
    CollectionConfig,
    CollectionResult,
    ConfigurationError,
    ReportConfig,
    ReportResult,
)
from .sync_wrapper import SyncWrapper


class AsyncMetricsClient:
    """
    Async client for metrics utility operations.

    This client provides async access to data collection and report generation
    functionality while preserving all existing CLI capabilities.
    """

    def __init__(self, environment_isolation: bool = True):
        """
        Initialize the async client.

        Args:
            environment_isolation: If True, each operation runs in isolated environment
        """
        self.environment_isolation = environment_isolation
        self.sync_wrapper = SyncWrapper()

    async def collect_data(self, config: CollectionConfig) -> CollectionResult:
        """
        Collect automation controller billing data asynchronously.

        Args:
            config: Collection configuration

        Returns:
            CollectionResult with operation details

        Raises:
            ConfigurationError: If configuration is invalid
            CollectionError: If collection fails
        """
        start_time = time.time()

        try:
            # Validate configuration
            self._validate_collection_config(config)

            # Prepare environment
            env_context = EnvironmentManager.create_environment_context(config)

            # Run collection in thread pool to avoid blocking
            result = await asyncio.get_event_loop().run_in_executor(None, self._run_collection_sync, config, env_context)

            execution_time = time.time() - start_time
            result.execution_time_seconds = execution_time

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            return CollectionResult(success=False, message=f'Collection failed: {str(e)}', errors=[str(e)], execution_time_seconds=execution_time)

    async def generate_report(self, config: ReportConfig) -> ReportResult:
        """
        Generate a report asynchronously.

        Args:
            config: Report configuration

        Returns:
            ReportResult with operation details

        Raises:
            ConfigurationError: If configuration is invalid
            ReportError: If report generation fails
        """
        start_time = time.time()

        try:
            # Validate configuration
            self._validate_report_config(config)

            # Prepare environment
            env_context = EnvironmentManager.create_environment_context(config)

            # Run report generation in thread pool to avoid blocking
            result = await asyncio.get_event_loop().run_in_executor(None, self._run_report_sync, config, env_context)

            execution_time = time.time() - start_time
            result.execution_time_seconds = execution_time

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            return ReportResult(success=False, message=f'Report generation failed: {str(e)}', errors=[str(e)], execution_time_seconds=execution_time)

    async def collect_and_report(self, collection_config: CollectionConfig, report_config: ReportConfig) -> tuple[CollectionResult, ReportResult]:
        """
        Convenience method to collect data and generate report in sequence.

        Args:
            collection_config: Configuration for data collection
            report_config: Configuration for report generation

        Returns:
            Tuple of (CollectionResult, ReportResult)
        """
        # Collect data first
        collection_result = await self.collect_data(collection_config)

        # Only generate report if collection succeeded
        if collection_result.success:
            report_result = await self.generate_report(report_config)
        else:
            report_result = ReportResult(success=False, message='Skipped report generation due to collection failure', errors=['Collection failed'])

        return collection_result, report_result

    async def get_collection_status(self, ship_path: str) -> Dict[str, Any]:
        """
        Get status of collected data in the specified path.

        Args:
            ship_path: Path to check for collected data

        Returns:
            Dictionary with collection status information
        """
        return await asyncio.get_event_loop().run_in_executor(None, self.sync_wrapper.get_collection_status, ship_path)

    async def list_available_reports(self, ship_path: str) -> List[Dict[str, Any]]:
        """
        List available reports in the specified path.

        Args:
            ship_path: Path to check for reports

        Returns:
            List of available reports with metadata
        """
        return await asyncio.get_event_loop().run_in_executor(None, self.sync_wrapper.list_available_reports, ship_path)

    def _validate_collection_config(self, config: CollectionConfig) -> None:
        """Validate collection configuration"""
        if not config.ship_path:
            raise ConfigurationError('ship_path is required')

        # Add more validation as needed

    def _validate_report_config(self, config: ReportConfig) -> None:
        """Validate report configuration"""
        if not config.ship_path:
            raise ConfigurationError('ship_path is required')

        # Validate time configuration
        time_configs = [config.month, config.since, config.until]
        if not any(time_configs):
            raise ConfigurationError('Either month or since/until must be specified')

        # Add more validation as needed

    def _run_collection_sync(self, config: CollectionConfig, env_context: Dict[str, str]) -> CollectionResult:
        """Run data collection synchronously"""
        try:
            with EnvironmentManager.apply_environment(env_context):
                return self.sync_wrapper.run_collection(config)
        except Exception as e:
            return CollectionResult(success=False, message=f'Collection failed: {str(e)}', errors=[str(e)])

    def _run_report_sync(self, config: ReportConfig, env_context: Dict[str, str]) -> ReportResult:
        """Run report generation synchronously"""
        try:
            with EnvironmentManager.apply_environment(env_context):
                return self.sync_wrapper.run_report(config)
        except Exception as e:
            return ReportResult(success=False, message=f'Report generation failed: {str(e)}', errors=[str(e)])
