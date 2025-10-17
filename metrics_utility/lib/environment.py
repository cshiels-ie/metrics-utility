"""
Environment management for metrics operations
"""

import contextlib
import os

from typing import Dict, Union

from .models import CollectionConfig, ReportConfig


class EnvironmentManager:
    """Manages environment variables for metrics operations"""

    @staticmethod
    def create_environment_context(config: Union[CollectionConfig, ReportConfig]) -> Dict[str, str]:
        """
        Create environment variable context from configuration.

        Args:
            config: Collection or Report configuration

        Returns:
            Dictionary of environment variables
        """
        env_vars = {}

        if isinstance(config, CollectionConfig):
            env_vars.update(EnvironmentManager._collection_config_to_env(config))
        elif isinstance(config, ReportConfig):
            env_vars.update(EnvironmentManager._report_config_to_env(config))

        return env_vars

    @staticmethod
    def _collection_config_to_env(config: CollectionConfig) -> Dict[str, str]:
        """Convert collection config to environment variables"""
        env_vars = {
            'METRICS_UTILITY_SHIP_TARGET': config.ship_target.value,
            'METRICS_UTILITY_SHIP_PATH': config.ship_path,
        }

        # Optional billing provider configuration
        if config.billing_account_id:
            env_vars['METRICS_UTILITY_BILLING_ACCOUNT_ID'] = config.billing_account_id
        if config.billing_provider:
            env_vars['METRICS_UTILITY_BILLING_PROVIDER'] = config.billing_provider
        if config.red_hat_org_id:
            env_vars['METRICS_UTILITY_RED_HAT_ORG_ID'] = config.red_hat_org_id

        # S3 configuration
        if config.bucket_name:
            env_vars['METRICS_UTILITY_BUCKET_NAME'] = config.bucket_name
        if config.bucket_endpoint:
            env_vars['METRICS_UTILITY_BUCKET_ENDPOINT'] = config.bucket_endpoint
        if config.bucket_access_key:
            env_vars['METRICS_UTILITY_BUCKET_ACCESS_KEY'] = config.bucket_access_key
        if config.bucket_secret_key:
            env_vars['METRICS_UTILITY_BUCKET_SECRET_KEY'] = config.bucket_secret_key
        if config.bucket_region:
            env_vars['METRICS_UTILITY_BUCKET_REGION'] = config.bucket_region

        # CRC configuration
        if config.crc_ingress_url:
            env_vars['METRICS_UTILITY_CRC_INGRESS_URL'] = config.crc_ingress_url
        if config.crc_sso_url:
            env_vars['METRICS_UTILITY_CRC_SSO_URL'] = config.crc_sso_url
        if config.proxy_url:
            env_vars['METRICS_UTILITY_PROXY_URL'] = config.proxy_url
        if config.service_account_id:
            env_vars['METRICS_UTILITY_SERVICE_ACCOUNT_ID'] = config.service_account_id
        if config.service_account_secret:
            env_vars['METRICS_UTILITY_SERVICE_ACCOUNT_SECRET'] = config.service_account_secret

        # Collection configuration
        if config.cluster_name:
            env_vars['METRICS_UTILITY_CLUSTER_NAME'] = config.cluster_name
        if config.collector_lock_suffix:
            env_vars['METRICS_UTILITY_COLLECTOR_LOCK_SUFFIX'] = config.collector_lock_suffix
        if config.disable_job_host_summary_collector:
            env_vars['METRICS_UTILITY_DISABLE_JOB_HOST_SUMMARY_COLLECTOR'] = 'true'
        if config.disable_save_last_gathered_entries:
            env_vars['METRICS_UTILITY_DISABLE_SAVE_LAST_GATHERED_ENTRIES'] = 'true'
        if config.max_gather_period_days != 28:
            env_vars['METRICS_UTILITY_MAX_GATHER_PERIOD_DAYS'] = str(config.max_gather_period_days)
        if config.optional_collectors:
            env_vars['METRICS_UTILITY_OPTIONAL_COLLECTORS'] = ','.join(config.optional_collectors)
        if config.usage_based_metering_enabled:
            env_vars['METRICS_UTILITY_USAGE_BASED_METERING_ENABLED'] = 'true'

        return env_vars

    @staticmethod
    def _report_config_to_env(config: ReportConfig) -> Dict[str, str]:
        """Convert report config to environment variables"""
        env_vars = {
            'METRICS_UTILITY_REPORT_TYPE': config.report_type.value,
            'METRICS_UTILITY_SHIP_TARGET': config.ship_target.value,
            'METRICS_UTILITY_SHIP_PATH': config.ship_path,
        }

        # Optional configuration
        if config.deduplicator:
            env_vars['METRICS_UTILITY_DEDUPLICATOR'] = config.deduplicator.value
        if config.organization_filter:
            env_vars['METRICS_UTILITY_ORGANIZATION_FILTER'] = ';'.join(config.organization_filter)
        if config.price_per_node:
            env_vars['METRICS_UTILITY_PRICE_PER_NODE'] = str(config.price_per_node)
        if config.optional_ccsp_report_sheets:
            env_vars['METRICS_UTILITY_OPTIONAL_CCSP_REPORT_SHEETS'] = ','.join(config.optional_ccsp_report_sheets)

        # S3 configuration
        if config.bucket_name:
            env_vars['METRICS_UTILITY_BUCKET_NAME'] = config.bucket_name
        if config.bucket_endpoint:
            env_vars['METRICS_UTILITY_BUCKET_ENDPOINT'] = config.bucket_endpoint
        if config.bucket_access_key:
            env_vars['METRICS_UTILITY_BUCKET_ACCESS_KEY'] = config.bucket_access_key
        if config.bucket_secret_key:
            env_vars['METRICS_UTILITY_BUCKET_SECRET_KEY'] = config.bucket_secret_key
        if config.bucket_region:
            env_vars['METRICS_UTILITY_BUCKET_REGION'] = config.bucket_region

        # Report customization
        if config.report_sku:
            env_vars['METRICS_UTILITY_REPORT_SKU'] = config.report_sku
        if config.report_sku_description:
            env_vars['METRICS_UTILITY_REPORT_SKU_DESCRIPTION'] = config.report_sku_description
        if config.report_h1_heading:
            env_vars['METRICS_UTILITY_REPORT_H1_HEADING'] = config.report_h1_heading
        if config.report_company_name:
            env_vars['METRICS_UTILITY_REPORT_COMPANY_NAME'] = config.report_company_name
        if config.report_email:
            env_vars['METRICS_UTILITY_REPORT_EMAIL'] = config.report_email
        if config.report_rhn_login:
            env_vars['METRICS_UTILITY_REPORT_RHN_LOGIN'] = config.report_rhn_login
        if config.report_po_number:
            env_vars['METRICS_UTILITY_REPORT_PO_NUMBER'] = config.report_po_number
        if config.report_company_business_leader:
            env_vars['METRICS_UTILITY_REPORT_COMPANY_BUSINESS_LEADER'] = config.report_company_business_leader
        if config.report_company_procurement_leader:
            env_vars['METRICS_UTILITY_REPORT_COMPANY_PROCUREMENT_LEADER'] = config.report_company_procurement_leader
        if config.report_end_user_company_name:
            env_vars['METRICS_UTILITY_REPORT_END_USER_COMPANY_NAME'] = config.report_end_user_company_name
        if config.report_end_user_city:
            env_vars['METRICS_UTILITY_REPORT_END_USER_CITY'] = config.report_end_user_city
        if config.report_end_user_state:
            env_vars['METRICS_UTILITY_REPORT_END_USER_STATE'] = config.report_end_user_state
        if config.report_end_user_country:
            env_vars['METRICS_UTILITY_REPORT_END_USER_COUNTRY'] = config.report_end_user_country

        return env_vars

    @staticmethod
    @contextlib.contextmanager
    def apply_environment(env_vars: Dict[str, str]):
        """
        Context manager to temporarily apply environment variables.

        Args:
            env_vars: Dictionary of environment variables to set
        """
        original_values = {}

        try:
            # Save original values and set new ones
            for key, value in env_vars.items():
                original_values[key] = os.environ.get(key)
                os.environ[key] = value

            yield

        finally:
            # Restore original values
            for key, original_value in original_values.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
