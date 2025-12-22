"""
Configuration schema for metrics-utility TUI.

Defines all configuration fields with their types, descriptions, validation rules,
and grouping for the user interface.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

from metrics_utility.management.validation import (
    MAX_GATHER_PERIOD_DAYS,
    VALID_COLLECTORS,
    VALID_REPORT_TYPES,
    VALID_SHIP_TARGET_BUILD,
    VALID_SHIP_TARGET_GATHER,
)


class FieldType(Enum):
    """Types of configuration fields"""

    STRING = 'string'
    INTEGER = 'integer'
    FLOAT = 'float'
    BOOLEAN = 'boolean'
    SELECT = 'select'  # Single selection from options
    MULTISELECT = 'multiselect'  # Multiple selections from options
    PASSWORD = 'password'  # Masked input


class FieldCategory(Enum):
    """Categories for organizing fields in the UI"""

    CORE = 'Core Configuration'
    S3 = 'S3 Configuration'
    CRC = 'CRC Configuration'
    BILLING = 'Billing Configuration'
    COLLECTION = 'Collection Configuration'
    REPORT = 'Report Configuration'
    PROMETHEUS = 'Prometheus Configuration'


@dataclass
class ConfigField:
    """Metadata for a single configuration field"""

    key: str  # Environment variable name (without METRICS_UTILITY_ prefix for most)
    display_name: str  # Human-readable name for UI
    description: str  # Help text
    field_type: FieldType
    category: FieldCategory
    default: Any = None
    required: bool = False
    options: Optional[list] = None  # For SELECT and MULTISELECT types
    validator: Optional[Callable] = None  # Custom validation function
    depends_on: Optional[dict] = None  # Conditional visibility {field_key: required_value}
    env_var_name: Optional[str] = None  # Override env var name if different from pattern

    def __post_init__(self):
        """Set env_var_name if not provided"""
        if self.env_var_name is None:
            # Most fields follow METRICS_UTILITY_{key} pattern
            self.env_var_name = f'METRICS_UTILITY_{self.key}'


def _validate_url(value: str) -> bool:
    """Validate URL format"""
    import re

    url_pattern = r'^https?://[^\s]+$'
    return bool(re.match(url_pattern, value))


def _validate_positive_integer(value: Any) -> bool:
    """Validate positive integer"""
    try:
        return int(value) >= 0
    except (ValueError, TypeError):
        return False


def _validate_max_gather_days(value: Any) -> bool:
    """Validate max gather period days"""
    try:
        days = int(value)
        return 0 <= days <= MAX_GATHER_PERIOD_DAYS
    except (ValueError, TypeError):
        return False


# Complete schema of all configuration fields
CONFIG_SCHEMA = [
    # Core Configuration
    ConfigField(
        key='SHIP_TARGET',
        display_name='Ship Target',
        description='Storage backend for data and reports (directory, s3, crc for gather; directory, s3, controller_db for build)',
        field_type=FieldType.SELECT,
        category=FieldCategory.CORE,
        required=True,
        options=list(VALID_SHIP_TARGET_GATHER | VALID_SHIP_TARGET_BUILD),
    ),
    ConfigField(
        key='SHIP_PATH',
        display_name='Ship Path',
        description='Base path for collected data and built reports',
        field_type=FieldType.STRING,
        category=FieldCategory.CORE,
        default='./out',
        required=False,  # Not required for CRC target
        depends_on={'SHIP_TARGET': ['directory', 's3', 'controller_db']},
    ),
    ConfigField(
        key='REPORT_TYPE',
        display_name='Report Type',
        description='Type of report to generate',
        field_type=FieldType.SELECT,
        category=FieldCategory.CORE,
        required=False,  # Only required for build command
        options=list(VALID_REPORT_TYPES),
    ),
    # S3 Configuration
    ConfigField(
        key='BUCKET_NAME',
        display_name='S3 Bucket Name',
        description='Name of S3 bucket for storage',
        field_type=FieldType.STRING,
        category=FieldCategory.S3,
        required=False,
        depends_on={'SHIP_TARGET': ['s3']},
    ),
    ConfigField(
        key='BUCKET_ENDPOINT',
        display_name='S3 Endpoint URL',
        description='S3 endpoint URL (e.g., https://s3.us-east.example.com)',
        field_type=FieldType.STRING,
        category=FieldCategory.S3,
        required=False,
        depends_on={'SHIP_TARGET': ['s3']},
        validator=_validate_url,
    ),
    ConfigField(
        key='BUCKET_REGION',
        display_name='S3 Region',
        description='AWS region for S3 bucket (optional)',
        field_type=FieldType.STRING,
        category=FieldCategory.S3,
        required=False,
        depends_on={'SHIP_TARGET': ['s3']},
    ),
    ConfigField(
        key='BUCKET_ACCESS_KEY',
        display_name='S3 Access Key',
        description='AWS access key for S3',
        field_type=FieldType.STRING,
        category=FieldCategory.S3,
        required=False,
        depends_on={'SHIP_TARGET': ['s3']},
    ),
    ConfigField(
        key='BUCKET_SECRET_KEY',
        display_name='S3 Secret Key',
        description='AWS secret key for S3',
        field_type=FieldType.PASSWORD,
        category=FieldCategory.S3,
        required=False,
        depends_on={'SHIP_TARGET': ['s3']},
    ),
    # CRC Configuration
    ConfigField(
        key='CRC_INGRESS_URL',
        display_name='CRC Ingress URL',
        description='Upload URL for console.redhat.com',
        field_type=FieldType.STRING,
        category=FieldCategory.CRC,
        default='https://console.redhat.com/api/ingress/v1/upload',
        required=False,
        depends_on={'SHIP_TARGET': ['crc']},
        validator=_validate_url,
    ),
    ConfigField(
        key='CRC_SSO_URL',
        display_name='CRC SSO URL',
        description='SSO/login URL for console.redhat.com',
        field_type=FieldType.STRING,
        category=FieldCategory.CRC,
        default='https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token',
        required=False,
        depends_on={'SHIP_TARGET': ['crc']},
        validator=_validate_url,
    ),
    ConfigField(
        key='SERVICE_ACCOUNT_ID',
        display_name='Service Account ID',
        description='Service account ID for CRC authentication',
        field_type=FieldType.STRING,
        category=FieldCategory.CRC,
        required=False,
        depends_on={'SHIP_TARGET': ['crc']},
    ),
    ConfigField(
        key='SERVICE_ACCOUNT_SECRET',
        display_name='Service Account Secret',
        description='Service account secret for CRC authentication',
        field_type=FieldType.PASSWORD,
        category=FieldCategory.CRC,
        required=False,
        depends_on={'SHIP_TARGET': ['crc']},
    ),
    ConfigField(
        key='PROXY_URL',
        display_name='Proxy URL',
        description='HTTP proxy URL for CRC uploads (optional)',
        field_type=FieldType.STRING,
        category=FieldCategory.CRC,
        required=False,
        depends_on={'SHIP_TARGET': ['crc']},
    ),
    # Billing Configuration
    ConfigField(
        key='BILLING_ACCOUNT_ID',
        display_name='Billing Account ID',
        description='AWS 12-digit customer ID for billing',
        field_type=FieldType.STRING,
        category=FieldCategory.BILLING,
        required=False,
    ),
    ConfigField(
        key='BILLING_PROVIDER',
        display_name='Billing Provider',
        description='Billing provider type (currently only "aws" supported)',
        field_type=FieldType.SELECT,
        category=FieldCategory.BILLING,
        required=False,
        options=['aws'],
    ),
    ConfigField(
        key='RED_HAT_ORG_ID',
        display_name='Red Hat Organization ID',
        description='Red Hat organization ID',
        field_type=FieldType.STRING,
        category=FieldCategory.BILLING,
        required=False,
    ),
    # Collection Configuration
    ConfigField(
        key='CLUSTER_NAME',
        display_name='Cluster Name',
        description='Kubernetes cluster name (required for total_workers_vcpu collector)',
        field_type=FieldType.STRING,
        category=FieldCategory.COLLECTION,
        required=False,
    ),
    ConfigField(
        key='OPTIONAL_COLLECTORS',
        display_name='Optional Collectors',
        description='Comma-separated list of optional collectors to enable',
        field_type=FieldType.MULTISELECT,
        category=FieldCategory.COLLECTION,
        default='main_jobevent',
        required=False,
        options=list(VALID_COLLECTORS),
    ),
    ConfigField(
        key='MAX_GATHER_PERIOD_DAYS',
        display_name='Max Gather Period (Days)',
        description=f'Maximum length of collection interval in days (0-{MAX_GATHER_PERIOD_DAYS})',
        field_type=FieldType.INTEGER,
        category=FieldCategory.COLLECTION,
        default=28,
        required=False,
        validator=_validate_max_gather_days,
    ),
    ConfigField(
        key='DISABLE_JOB_HOST_SUMMARY_COLLECTOR',
        display_name='Disable Job Host Summary Collector',
        description='Disable the job_host_summary collector',
        field_type=FieldType.BOOLEAN,
        category=FieldCategory.COLLECTION,
        default=False,
        required=False,
    ),
    ConfigField(
        key='DISABLE_SAVE_LAST_GATHERED_ENTRIES',
        display_name='Disable Save Last Gathered Entries',
        description='Skip updating last gather info in controller settings',
        field_type=FieldType.BOOLEAN,
        category=FieldCategory.COLLECTION,
        default=False,
        required=False,
    ),
    ConfigField(
        key='COLLECTOR_LOCK_SUFFIX',
        display_name='Collector Lock Suffix',
        description='Custom lock name suffix for total_workers_vcpu collector',
        field_type=FieldType.STRING,
        category=FieldCategory.COLLECTION,
        required=False,
    ),
    # Prometheus Configuration
    ConfigField(
        key='PROMETHEUS_URL',
        display_name='Prometheus URL',
        description='Base URL for Prometheus metrics',
        field_type=FieldType.STRING,
        category=FieldCategory.PROMETHEUS,
        required=False,
        validator=_validate_url,
    ),
    ConfigField(
        key='USAGE_BASED_METERING_ENABLED',
        display_name='Usage-Based Metering Enabled',
        description='Enable total_workers_vcpu collector for usage-based metering',
        field_type=FieldType.BOOLEAN,
        category=FieldCategory.PROMETHEUS,
        default=False,
        required=False,
    ),
    # Report Configuration
    ConfigField(
        key='PRICE_PER_NODE',
        display_name='Price Per Node',
        description='Price per managed node for cost calculations (USD)',
        field_type=FieldType.FLOAT,
        category=FieldCategory.REPORT,
        default=0.0,
        required=False,
        validator=lambda v: float(v) >= 0,
    ),
    ConfigField(
        key='REPORT_SKU',
        display_name='Report SKU',
        description='SKU identifier for the report',
        field_type=FieldType.STRING,
        category=FieldCategory.REPORT,
        required=False,
    ),
    ConfigField(
        key='REPORT_SKU_DESCRIPTION',
        display_name='Report SKU Description',
        description='Description of the SKU',
        field_type=FieldType.STRING,
        category=FieldCategory.REPORT,
        required=False,
    ),
    ConfigField(
        key='REPORT_H1_HEADING',
        display_name='Report Main Heading',
        description='Main heading for the report (H1)',
        field_type=FieldType.STRING,
        category=FieldCategory.REPORT,
        required=False,
    ),
    ConfigField(
        key='REPORT_COMPANY_NAME',
        display_name='Report Company Name',
        description='Company name for the report',
        field_type=FieldType.STRING,
        category=FieldCategory.REPORT,
        required=False,
    ),
    ConfigField(
        key='REPORT_EMAIL',
        display_name='Report Contact Email',
        description='Contact email for the report',
        field_type=FieldType.STRING,
        category=FieldCategory.REPORT,
        required=False,
    ),
    ConfigField(
        key='REPORT_RHN_LOGIN',
        display_name='Red Hat Network Login',
        description='Red Hat Network login for the report',
        field_type=FieldType.STRING,
        category=FieldCategory.REPORT,
        required=False,
    ),
    ConfigField(
        key='REPORT_PO_NUMBER',
        display_name='Purchase Order Number',
        description='PO number for the report',
        field_type=FieldType.STRING,
        category=FieldCategory.REPORT,
        required=False,
    ),
    ConfigField(
        key='REPORT_COMPANY_BUSINESS_LEADER',
        display_name='Business Leader Name',
        description='Business leader name for the report',
        field_type=FieldType.STRING,
        category=FieldCategory.REPORT,
        required=False,
    ),
    ConfigField(
        key='REPORT_COMPANY_PROCUREMENT_LEADER',
        display_name='Procurement Leader Name',
        description='Procurement leader name for the report',
        field_type=FieldType.STRING,
        category=FieldCategory.REPORT,
        required=False,
    ),
    ConfigField(
        key='REPORT_END_USER_COMPANY_NAME',
        display_name='End User Company Name',
        description='End user company name for the report',
        field_type=FieldType.STRING,
        category=FieldCategory.REPORT,
        required=False,
    ),
    ConfigField(
        key='REPORT_END_USER_CITY',
        display_name='End User City',
        description='End user company city for the report',
        field_type=FieldType.STRING,
        category=FieldCategory.REPORT,
        required=False,
    ),
    ConfigField(
        key='REPORT_END_USER_STATE',
        display_name='End User State',
        description='End user company state for the report',
        field_type=FieldType.STRING,
        category=FieldCategory.REPORT,
        required=False,
    ),
    ConfigField(
        key='REPORT_END_USER_COUNTRY',
        display_name='End User Country',
        description='End user company country for the report',
        field_type=FieldType.STRING,
        category=FieldCategory.REPORT,
        required=False,
    ),
    ConfigField(
        key='OPTIONAL_CCSP_REPORT_SHEETS',
        display_name='Optional Report Sheets',
        description='Comma-separated list of optional sheets to include in CCSP reports',
        field_type=FieldType.STRING,
        category=FieldCategory.REPORT,
        default='ccsp_summary,managed_nodes,usage_by_organizations,usage_by_collections,usage_by_roles,usage_by_modules',
        required=False,
    ),
    ConfigField(
        key='ORGANIZATION_FILTER',
        display_name='Organization Filter',
        description='Semicolon-separated list of organization names to filter (CCSPv2 only)',
        field_type=FieldType.STRING,
        category=FieldCategory.REPORT,
        required=False,
    ),
    ConfigField(
        key='DEDUPLICATOR',
        display_name='Deduplicator Strategy',
        description='Choice of deduplication algorithm',
        field_type=FieldType.SELECT,
        category=FieldCategory.REPORT,
        required=False,
        options=['ccsp', 'renewal', 'ccsp-experimental'],
    ),
    ConfigField(
        key='REPORT_RENEWAL_GUIDANCE_DEDUP_ITERATIONS',
        display_name='Renewal Guidance Dedup Iterations',
        description='Maximum number of dedup iterations for renewal guidance report',
        field_type=FieldType.INTEGER,
        category=FieldCategory.REPORT,
        default=3,
        required=False,
        validator=_validate_positive_integer,
        env_var_name='REPORT_RENEWAL_GUIDANCE_DEDUP_ITERATIONS',  # No METRICS_UTILITY_ prefix
    ),
    # Database Configuration (for development)
    ConfigField(
        key='DB_HOST',
        display_name='Database Host',
        description='PostgreSQL host for standalone mode (development only)',
        field_type=FieldType.STRING,
        category=FieldCategory.CORE,
        required=False,
    ),
]


def get_schema_by_category():
    """Group fields by category"""
    categories = {}
    for field_config in CONFIG_SCHEMA:
        cat = field_config.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(field_config)
    return categories


def get_field_by_key(key: str) -> Optional[ConfigField]:
    """Get field configuration by key"""
    for field_config in CONFIG_SCHEMA:
        if field_config.key == key:
            return field_config
    return None


def get_field_by_env_var(env_var: str) -> Optional[ConfigField]:
    """Get field configuration by environment variable name"""
    for field_config in CONFIG_SCHEMA:
        if field_config.env_var_name == env_var:
            return field_config
    return None
