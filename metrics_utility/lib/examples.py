"""
Usage examples for the async metrics library
"""

import asyncio

from datetime import datetime, timedelta

from metrics_utility.lib import (
    AsyncMetricsClient,
    CollectionConfig,
    ReportConfig,
    ReportType,
    ShipTarget,
)


async def basic_collection_example():
    """Basic data collection example"""
    client = AsyncMetricsClient()

    # Configure data collection
    config = CollectionConfig(
        ship_target=ShipTarget.DIRECTORY,
        ship_path='./test_data',
        since=datetime.now() - timedelta(days=7),
        until=datetime.now(),
        ship=True,
        dry_run=False,
    )

    # Collect data
    result = await client.collect_data(config)

    if result.success:
        print(f'Collection successful: {result.message}')
        print(f'Tarballs created: {result.tarballs}')
    else:
        print(f'Collection failed: {result.message}')
        print(f'Errors: {result.errors}')


async def basic_report_example():
    """Basic report generation example"""
    client = AsyncMetricsClient()

    # Configure report generation
    config = ReportConfig(
        report_type=ReportType.CCSPV2,
        ship_target=ShipTarget.DIRECTORY,
        ship_path='./test_data',
        month='2024-04',  # Generate report for April 2024
        force=True,
        price_per_node=11.55,
        report_company_name='Example Company',
        report_email='admin@example.com',
    )

    # Generate report
    result = await client.generate_report(config)

    if result.success:
        print(f'Report generated: {result.message}')
        print(f'Report path: {result.report_path}')
    else:
        print(f'Report generation failed: {result.message}')
        print(f'Errors: {result.errors}')


async def collect_and_report_example():
    """Example of collecting data and then generating a report"""
    client = AsyncMetricsClient()

    # Collection configuration
    collection_config = CollectionConfig(
        ship_target=ShipTarget.DIRECTORY, ship_path='./output', since=datetime.now() - timedelta(days=30), until=datetime.now(), ship=True
    )

    # Report configuration
    report_config = ReportConfig(
        report_type=ReportType.CCSPV2,
        ship_target=ShipTarget.DIRECTORY,
        ship_path='./output',
        since=datetime.now() - timedelta(days=30),
        until=datetime.now(),
        force=True,
        price_per_node=15.00,
        report_company_name='My Company',
        report_email='contact@mycompany.com',
        report_end_user_company_name='Customer Corp',
        report_end_user_city='Springfield',
        report_end_user_state='IL',
        report_end_user_country='US',
    )

    # Run both operations
    collection_result, report_result = await client.collect_and_report(collection_config, report_config)

    print(f'Collection: {"✓" if collection_result.success else "✗"} {collection_result.message}')
    print(f'Report: {"✓" if report_result.success else "✗"} {report_result.message}')


async def s3_example():
    """Example using S3 storage"""
    client = AsyncMetricsClient()

    # S3 collection configuration
    config = CollectionConfig(
        ship_target=ShipTarget.S3,
        ship_path='my-metrics-bucket/data',
        since=datetime.now() - timedelta(days=7),
        bucket_name='my-metrics-bucket',
        bucket_region='us-east-1',
        bucket_access_key='your-access-key',
        bucket_secret_key='your-secret-key',
        ship=True,
    )

    result = await client.collect_data(config)
    print(f'S3 Collection: {"✓" if result.success else "✗"} {result.message}')


async def concurrent_operations_example():
    """Example of running multiple operations concurrently"""
    client = AsyncMetricsClient()

    # Create multiple collection configurations
    configs = [
        CollectionConfig(
            ship_target=ShipTarget.DIRECTORY,
            ship_path=f'./output_env_{i}',
            since=datetime.now() - timedelta(days=30),
            until=datetime.now(),
            ship=True,
        )
        for i in range(3)
    ]

    # Run collections concurrently
    tasks = [client.collect_data(config) for config in configs]
    results = await asyncio.gather(*tasks)

    for i, result in enumerate(results):
        print(f'Environment {i}: {"✓" if result.success else "✗"} {result.message}')


async def status_monitoring_example():
    """Example of monitoring collection status"""
    client = AsyncMetricsClient()

    # Check status of existing data
    status = await client.get_collection_status('./test_data')
    print(f'Has data: {status.get("has_data", False)}')
    print(f'Tarball count: {status.get("tarball_count", 0)}')

    # List available reports
    reports = await client.list_available_reports('./test_data')
    print(f'Available reports: {len(reports)}')
    for report in reports[:3]:  # Show first 3 reports
        print(f'  - {report["filename"]} ({report["year"]}-{report["month"]})')


async def renewal_guidance_example():
    """Example generating a renewal guidance report"""
    client = AsyncMetricsClient()

    config = ReportConfig(
        report_type=ReportType.RENEWAL_GUIDANCE,
        ship_target=ShipTarget.CONTROLLER_DB,
        ship_path='./renewal_output',
        since=datetime.now() - timedelta(days=365),  # 1 year of data
        ephemeral='1month',
        force=True,
    )

    result = await client.generate_report(config)
    print(f'Renewal Guidance: {"✓" if result.success else "✗"} {result.message}')


if __name__ == '__main__':
    # Run basic examples
    print('=== Basic Collection Example ===')
    asyncio.run(basic_collection_example())

    print('\n=== Basic Report Example ===')
    asyncio.run(basic_report_example())

    print('\n=== Status Monitoring Example ===')
    asyncio.run(status_monitoring_example())
