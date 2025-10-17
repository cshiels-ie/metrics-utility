"""
Data models for the async metrics library
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ShipTarget(Enum):
    """Supported shipping targets"""

    DIRECTORY = 'directory'
    S3 = 's3'
    CRC = 'crc'
    CONTROLLER_DB = 'controller_db'


class ReportType(Enum):
    """Supported report types"""

    CCSP = 'CCSP'
    CCSPV2 = 'CCSPv2'
    RENEWAL_GUIDANCE = 'RENEWAL_GUIDANCE'


class DeduplicatorType(Enum):
    """Supported deduplication algorithms"""

    CCSP = 'ccsp'
    RENEWAL = 'renewal'
    CCSP_EXPERIMENTAL = 'ccsp-experimental'


@dataclass
class CollectionConfig:
    """Configuration for data collection operations"""

    ship_target: ShipTarget
    ship_path: str
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    dry_run: bool = False
    ship: bool = True

    # Optional billing provider configuration
    billing_account_id: Optional[str] = None
    billing_provider: Optional[str] = None
    red_hat_org_id: Optional[str] = None

    # S3 configuration
    bucket_name: Optional[str] = None
    bucket_endpoint: Optional[str] = None
    bucket_access_key: Optional[str] = None
    bucket_secret_key: Optional[str] = None
    bucket_region: Optional[str] = None

    # CRC configuration
    crc_ingress_url: Optional[str] = None
    crc_sso_url: Optional[str] = None
    proxy_url: Optional[str] = None
    service_account_id: Optional[str] = None
    service_account_secret: Optional[str] = None

    # Collection configuration
    cluster_name: Optional[str] = None
    collector_lock_suffix: Optional[str] = None
    disable_job_host_summary_collector: bool = False
    disable_save_last_gathered_entries: bool = False
    max_gather_period_days: int = 28
    optional_collectors: List[str] = field(default_factory=list)
    usage_based_metering_enabled: bool = False


@dataclass
class ReportConfig:
    """Configuration for report generation operations"""

    report_type: ReportType
    ship_target: ShipTarget
    ship_path: str

    # Time configuration - one of these should be specified
    month: Optional[str] = None  # Format: YYYY-MM
    since: Optional[datetime] = None
    until: Optional[datetime] = None

    # Report options
    ephemeral: Optional[str] = None  # e.g., "3months", "30days"
    force: bool = False

    # Optional configuration
    deduplicator: Optional[DeduplicatorType] = None
    organization_filter: List[str] = field(default_factory=list)
    price_per_node: Optional[float] = None
    optional_ccsp_report_sheets: List[str] = field(default_factory=list)

    # S3 configuration (if ship_target is S3)
    bucket_name: Optional[str] = None
    bucket_endpoint: Optional[str] = None
    bucket_access_key: Optional[str] = None
    bucket_secret_key: Optional[str] = None
    bucket_region: Optional[str] = None

    # Report customization
    report_sku: Optional[str] = None
    report_sku_description: Optional[str] = None
    report_h1_heading: Optional[str] = None
    report_company_name: Optional[str] = None
    report_email: Optional[str] = None
    report_rhn_login: Optional[str] = None
    report_po_number: Optional[str] = None
    report_company_business_leader: Optional[str] = None
    report_company_procurement_leader: Optional[str] = None
    report_end_user_company_name: Optional[str] = None
    report_end_user_city: Optional[str] = None
    report_end_user_state: Optional[str] = None
    report_end_user_country: Optional[str] = None


@dataclass
class CollectionResult:
    """Result of a data collection operation"""

    success: bool
    message: str
    tarballs: List[str] = field(default_factory=list)
    collected_data_info: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    execution_time_seconds: Optional[float] = None


@dataclass
class ReportResult:
    """Result of a report generation operation"""

    success: bool
    message: str
    report_path: Optional[str] = None
    report_info: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    execution_time_seconds: Optional[float] = None


class MetricsError(Exception):
    """Base exception for metrics library operations"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(MetricsError):
    """Raised when there's a configuration issue"""

    pass


class CollectionError(MetricsError):
    """Raised when data collection fails"""

    pass


class ReportError(MetricsError):
    """Raised when report generation fails"""

    pass
