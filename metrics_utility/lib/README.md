# Metrics Utility Async Library

This library provides async access to the AAP metrics-utility functionality, allowing integration into other applications with concurrent operations and non-blocking I/O.

## Features

- **Async/Await Support**: All operations are async for better performance
- **Thread-Safe**: Safe for concurrent use across multiple coroutines
- **Environment Isolation**: Each operation can run with isolated environment variables
- **Preserves CLI Functionality**: All existing CLI features are available through the library
- **Type Safety**: Full type hints and dataclass-based configuration
- **Error Handling**: Comprehensive error handling with detailed error information

## Quick Start

```python
import asyncio
from datetime import datetime, timedelta
from metrics_utility import (
    AsyncMetricsClient,
    CollectionConfig,
    ReportConfig,
    ShipTarget,
    ReportType,
)

async def main():
    client = AsyncMetricsClient()
    
    # Collect data
    collection_config = CollectionConfig(
        ship_target=ShipTarget.DIRECTORY,
        ship_path="./data",
        since=datetime.now() - timedelta(days=7),
        ship=True
    )
    
    result = await client.collect_data(collection_config)
    if result.success:
        print(f"Collected: {result.tarballs}")
    
    # Generate report
    report_config = ReportConfig(
        report_type=ReportType.CCSPV2,
        ship_target=ShipTarget.DIRECTORY,
        ship_path="./data",
        month="2024-04",
        force=True
    )
    
    report_result = await client.generate_report(report_config)
    if report_result.success:
        print(f"Report: {report_result.report_path}")

asyncio.run(main())
```

## Core Classes

### AsyncMetricsClient

The main client class for all operations:

```python
client = AsyncMetricsClient(environment_isolation=True)

# Data collection
result = await client.collect_data(collection_config)

# Report generation
result = await client.generate_report(report_config)

# Combined operation
collection_result, report_result = await client.collect_and_report(
    collection_config, 
    report_config
)

# Status monitoring
status = await client.get_collection_status("./data")
reports = await client.list_available_reports("./data")
```

### Configuration Classes

#### CollectionConfig

Configure data collection operations:

```python
config = CollectionConfig(
    ship_target=ShipTarget.DIRECTORY,  # or S3, CRC, CONTROLLER_DB
    ship_path="./output",
    since=datetime.now() - timedelta(days=30),
    until=datetime.now(),
    dry_run=False,
    ship=True,
    
    # S3 configuration (if using S3)
    bucket_name="my-bucket",
    bucket_access_key="key",
    bucket_secret_key="secret",
    
    # Optional collection settings
    optional_collectors=["collector1", "collector2"],
    max_gather_period_days=28,
)
```

#### ReportConfig

Configure report generation:

```python
config = ReportConfig(
    report_type=ReportType.CCSPV2,  # or CCSP, RENEWAL_GUIDANCE
    ship_target=ShipTarget.DIRECTORY,
    ship_path="./output",
    
    # Time specification (choose one)
    month="2024-04",  # YYYY-MM format
    # OR
    since=datetime.now() - timedelta(days=30),
    until=datetime.now(),
    
    # Report options
    force=True,
    price_per_node=15.50,
    
    # Report customization
    report_company_name="My Company",
    report_email="admin@company.com",
    report_end_user_company_name="Customer Corp",
)
```

### Result Classes

#### CollectionResult

```python
result = await client.collect_data(config)

if result.success:
    print(f"Message: {result.message}")
    print(f"Tarballs: {result.tarballs}")
    print(f"Execution time: {result.execution_time_seconds}s")
    print(f"Info: {result.collected_data_info}")
else:
    print(f"Errors: {result.errors}")
```

#### ReportResult

```python
result = await client.generate_report(config)

if result.success:
    print(f"Report path: {result.report_path}")
    print(f"Report info: {result.report_info}")
else:
    print(f"Errors: {result.errors}")
```

## Ship Targets

The library supports all CLI ship targets:

- **DIRECTORY**: Local filesystem storage
- **S3**: Amazon S3 storage
- **CRC**: Console.redhat.com upload
- **CONTROLLER_DB**: Direct controller database access

## Report Types

- **CCSP**: CCSP usage report
- **CCSPV2**: CCSPv2 usage report  
- **RENEWAL_GUIDANCE**: Renewal guidance report

## Concurrent Operations

Run multiple operations concurrently:

```python
async def concurrent_collections():
    client = AsyncMetricsClient()
    
    configs = [
        CollectionConfig(ship_target=ShipTarget.DIRECTORY, ship_path=f"./env_{i}")
        for i in range(5)
    ]
    
    # Run all collections concurrently
    tasks = [client.collect_data(config) for config in configs]
    results = await asyncio.gather(*tasks)
    
    for result in results:
        print(f"Success: {result.success}")
```

## Environment Isolation

Each operation runs with isolated environment variables:

```python
# These will not interfere with each other
task1 = client.collect_data(config1)  # Uses config1's env vars
task2 = client.collect_data(config2)  # Uses config2's env vars

results = await asyncio.gather(task1, task2)
```

## Error Handling

The library provides detailed error information:

```python
try:
    result = await client.collect_data(config)
    if not result.success:
        print(f"Operation failed: {result.message}")
        for error in result.errors:
            print(f"  - {error}")
except MetricsError as e:
    print(f"Library error: {e.message}")
    print(f"Details: {e.details}")
```

## Integration with Existing CLI

The library preserves all CLI functionality and can be used alongside the existing CLI commands. Environment variables and configuration work the same way.

For a complete working example, see `examples.py` in this directory.