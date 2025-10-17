"""
Complete examples showing all parameter translations
"""

import asyncio

from datetime import datetime, timedelta

from metrics_utility.lib import (
    AsyncMetricsClient,
    CollectionConfig,
    DeduplicatorType,
    ReportConfig,
    ReportType,
    ShipTarget,
)


async def comprehensive_collection_example():
    """Example showing ALL collection parameters"""

    config = CollectionConfig(
        # Core configuration
        ship_target=ShipTarget.DIRECTORY,
        ship_path='./comprehensive_output',
        since=datetime.now() - timedelta(days=30),
        until=datetime.now(),
        dry_run=False,
        ship=True,
        # Billing provider configuration
        billing_account_id='123456789',
        billing_provider='aws',
        red_hat_org_id='org-12345',
        # S3 configuration (if using S3 ship_target)
        bucket_name='metrics-bucket',
        bucket_endpoint='https://s3.amazonaws.com',
        bucket_access_key='AKIA...',
        bucket_secret_key='secret...',
        bucket_region='us-east-1',
        # CRC configuration (if using CRC ship_target)
        crc_ingress_url='https://console.redhat.com/api/ingress/v1/upload',
        crc_sso_url='https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token',
        proxy_url='http://proxy.company.com:8080',
        service_account_id='service-account-id',
        service_account_secret='service-account-secret',
        # Collection-specific configuration
        cluster_name='production-k8s-cluster',
        collector_lock_suffix='prod',
        disable_job_host_summary_collector=False,
        disable_save_last_gathered_entries=False,
        max_gather_period_days=28,
        # Optional collectors - THIS IS THE KEY PARAMETER YOU ASKED ABOUT
        optional_collectors=[
            'total_workers_vcpu',  # Kubernetes worker vCPU metrics
            'prometheus_metrics',  # Prometheus-based metrics
            'custom_analytics',  # Custom analytics collector
            'host_metrics',  # Additional host metrics
        ],
        usage_based_metering_enabled=True,  # Enable usage-based metering
    )

    client = AsyncMetricsClient()
    result = await client.collect_data(config)

    print('=== Collection with Optional Collectors ===')
    print(f'Success: {result.success}')
    print(f'Message: {result.message}')
    if result.success:
        print(f'Tarballs created: {len(result.tarballs)}')
        for tarball in result.tarballs:
            print(f'  - {tarball}')


async def comprehensive_report_example():
    """Example showing ALL report parameters"""

    config = ReportConfig(
        # Core configuration
        report_type=ReportType.CCSPV2,
        ship_target=ShipTarget.DIRECTORY,
        ship_path='./comprehensive_output',
        # Time configuration
        month='2024-04',  # Alternative: use since/until
        # since=datetime.now() - timedelta(days=30),
        # until=datetime.now(),
        # Report options
        ephemeral='3months',  # or "90days"
        force=True,
        # Optional configuration
        deduplicator=DeduplicatorType.CCSP,
        organization_filter=['Engineering Org', 'Operations Org', 'DevOps Team'],
        price_per_node=15.50,
        optional_ccsp_report_sheets=['detailed_usage', 'cost_breakdown', 'trend_analysis'],
        # S3 configuration (if needed)
        bucket_name='reports-bucket',
        bucket_access_key='AKIA...',
        bucket_secret_key='secret...',
        bucket_region='us-west-2',
        # Report customization - ALL AVAILABLE FIELDS
        report_sku='MCT3752MO',
        report_sku_description='Red Hat Ansible Automation Platform, Full Support (1 Managed Node, Dedicated, Monthly)',
        report_h1_heading='CCSP NA Direct Reporting Template',
        report_company_name='Example Corp',
        report_email='admin@example.com',
        report_rhn_login='rhn_admin',
        report_po_number='PO-2024-001',
        report_company_business_leader='Jane Smith, VP Engineering',
        report_company_procurement_leader='John Doe, Procurement Director',
        report_end_user_company_name='Customer Solutions Inc',
        report_end_user_city='San Francisco',
        report_end_user_state='CA',
        report_end_user_country='US',
    )

    client = AsyncMetricsClient()
    result = await client.generate_report(config)

    print('\n=== Report with All Parameters ===')
    print(f'Success: {result.success}')
    print(f'Message: {result.message}')
    if result.success:
        print(f'Report path: {result.report_path}')


async def environment_variable_mapping_demo():
    """Demonstrate how parameters map to environment variables"""

    from metrics_utility.lib.environment import EnvironmentManager

    config = CollectionConfig(
        ship_target=ShipTarget.S3,
        ship_path='s3://my-bucket/data',
        optional_collectors=['total_workers_vcpu', 'prometheus_metrics'],
        usage_based_metering_enabled=True,
        cluster_name='prod-cluster',
        max_gather_period_days=14,
        billing_account_id='987654321',
    )

    # Get the environment variables that would be set
    env_vars = EnvironmentManager.create_environment_context(config)

    print('\n=== Environment Variable Mapping ===')
    print('Python Config → Environment Variables:')

    mapping = {
        'optional_collectors=["total_workers_vcpu", "prometheus_metrics"]': env_vars.get('METRICS_UTILITY_OPTIONAL_COLLECTORS'),
        'usage_based_metering_enabled=True': env_vars.get('METRICS_UTILITY_USAGE_BASED_METERING_ENABLED'),
        'cluster_name="prod-cluster"': env_vars.get('METRICS_UTILITY_CLUSTER_NAME'),
        'max_gather_period_days=14': env_vars.get('METRICS_UTILITY_MAX_GATHER_PERIOD_DAYS'),
        'billing_account_id="987654321"': env_vars.get('METRICS_UTILITY_BILLING_ACCOUNT_ID'),
        'ship_target=ShipTarget.S3': env_vars.get('METRICS_UTILITY_SHIP_TARGET'),
    }

    for python_param, env_value in mapping.items():
        print(f'  {python_param}')
        print(f'    → {env_value}')


async def specialized_collector_examples():
    """Examples of different collector configurations"""

    print('\n=== Specialized Collector Examples ===')

    # Example 1: Kubernetes usage-based metering
    k8s_config = CollectionConfig(
        ship_target=ShipTarget.DIRECTORY,
        ship_path='./k8s_metrics',
        optional_collectors=['total_workers_vcpu'],
        usage_based_metering_enabled=True,
        cluster_name='production-k8s',
        collector_lock_suffix='k8s-prod',
    )
    print('1. Kubernetes Usage-Based Metering:')
    print(f'   Collectors: {k8s_config.optional_collectors}')
    print(f'   Cluster: {k8s_config.cluster_name}')

    # Example 2: Prometheus integration
    prometheus_config = CollectionConfig(
        ship_target=ShipTarget.DIRECTORY,
        ship_path='./prometheus_metrics',
        optional_collectors=['prometheus_metrics', 'host_metrics'],
        max_gather_period_days=7,  # Shorter period for detailed metrics
    )
    print('\n2. Prometheus Integration:')
    print(f'   Collectors: {prometheus_config.optional_collectors}')
    print(f'   Gather period: {prometheus_config.max_gather_period_days} days')

    # Example 3: Minimal collection (no optional collectors)
    minimal_config = CollectionConfig(
        ship_target=ShipTarget.DIRECTORY,
        ship_path='./minimal_metrics',
        disable_job_host_summary_collector=True,  # Disable if not needed
        optional_collectors=[],  # No optional collectors
    )
    print('\n3. Minimal Collection:')
    print(f'   Optional collectors: {minimal_config.optional_collectors}')
    print(f'   Job host summary disabled: {minimal_config.disable_job_host_summary_collector}')


if __name__ == '__main__':
    print('🔧 Parameter Translation Examples\n')

    asyncio.run(environment_variable_mapping_demo())
    asyncio.run(specialized_collector_examples())

    # Uncomment to run full examples (requires proper environment setup)
    # asyncio.run(comprehensive_collection_example())
    # asyncio.run(comprehensive_report_example())
