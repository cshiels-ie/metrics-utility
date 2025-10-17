"""
Async library interface for metrics-utility

This module provides async access to the metrics utility functionality
for integration into other applications.
"""

from .async_client import AsyncMetricsClient
from .models import (
    CollectionConfig,
    CollectionResult,
    DeduplicatorType,
    MetricsError,
    ReportConfig,
    ReportResult,
    ReportType,
    ShipTarget,
)


__all__ = [
    'AsyncMetricsClient',
    'CollectionConfig',
    'ReportConfig',
    'CollectionResult',
    'ReportResult',
    'MetricsError',
    'ShipTarget',
    'ReportType',
    'DeduplicatorType',
]
