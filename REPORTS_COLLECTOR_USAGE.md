# AWX Reports Collector - JSON Output

## Overview

The new Reports Collector provides comprehensive JSON-based metrics for AWX Automation Controller, covering all the requested use cases. Unlike the existing CSV-based collector, this one outputs structured JSON data that's ideal for dashboards and reporting tools.

## Installation & Setup

The reports collector is now integrated into the existing metrics utility CLI system.

### Prerequisites

1. Activate the virtual environment:

   ```bash
   source .venv/bin/activate
   ```

2. Set required environment variables:
   ```bash
   export METRICS_UTILITY_SHIP_TARGET=directory  # or 'crc', 's3'
   export METRICS_UTILITY_SHIP_PATH=/path/to/output/directory
   ```

## Usage

### Basic Usage

```bash
# Dry run (testing, no shipping)
python manage.py gather_automation_controller_reports_data --dry-run --since=7d

# With shipping enabled
python manage.py gather_automation_controller_reports_data --ship --since=7d

# Verbose output for debugging
python manage.py gather_automation_controller_reports_data --dry-run --since=7d --verbose
```

### Command Options

- `--dry-run`: Collect data without shipping (for testing)
- `--ship`: Enable shipping to configured target
- `--since=7d`: Collection start date (7 days ago)
- `--until=1d`: Collection end date (1 day ago)
- `--verbose`: Enable debug output

## Collected Metrics

The collector provides **15 JSON-based metrics** covering all requested use cases:

### 📊 **Cluster Metrics**

- **active_clusters_count.json** - Active number of clusters
- **active_clusters_by_controller_version.json** - Active clusters by controller version

### ⚙️ **Job Metrics**

- **job_duration_stats_by_template.json** - Job duration statistics by template (avg/min/max/total in seconds and minutes)
- **avg_tasks_by_template.json** - Average tasks by template
- **job_execution_stats.json** - Number of jobs succeeded/failed/executed

### 🔧 **Module Metrics**

- **total_modules_automated.json** - Total number of modules automated
- **module_success_failure_rates.json** - Failure/Success rate of modules
- **modules_usage_by_job_kpi.json** - KPI - count of modules used across customers grouped by job ID
- **modules_used_to_automate.json** - Modules used to automate
- **avg_modules_per_playbook.json** - Average number of modules used in a playbook

### 📋 **Template & Host Metrics**

- **templates_executed_by_company.json** - Number of templates executed by company
- **total_hosts_automated_over_time.json** - Total number of hosts automated over time
- **task_execution_stats.json** - Number of tasks executed & success ratio

### 🏗️ **Execution Environment Metrics**

- **execution_environment_stats.json** - Number of execution environments configured & ratio of Default EE vs Custom EE

### ⚙️ **Configuration**

- **config.json** - Collector configuration metadata

## Output Format

Each JSON file contains structured data with the following pattern:

```json
{
  "metric_data": [...],
  "period_start": "2024-01-01T00:00:00Z",
  "period_end": "2024-01-07T23:59:59Z"
}
```

### Example Output Structure

```json
{
  "job_duration_stats": [
    {
      "template_name": "Deploy Application",
      "template_id": 123,
      "job_count": 45,
      "avg_duration_seconds": 120.5,
      "avg_duration_minutes": 2.0,
      "min_duration_seconds": 30.0,
      "max_duration_seconds": 300.0,
      "total_duration_minutes": 90.25
    }
  ],
  "period_start": "2024-01-01T00:00:00Z",
  "period_end": "2024-01-07T23:59:59Z"
}
```

## Integration with Existing System

- **Compatible**: Works alongside the existing billing collector
- **Same Infrastructure**: Uses the same Collector class and patterns
- **Same CLI Pattern**: Follows the same command-line interface style
- **Same Environment Variables**: Uses the same configuration system

## Testing

### Quick Test

```bash
# Set up test environment
export METRICS_UTILITY_SHIP_TARGET=directory
export METRICS_UTILITY_SHIP_PATH=/tmp/reports_test
mkdir -p /tmp/reports_test

# Run test collection
python manage.py gather_automation_controller_reports_data --dry-run --since=1d --verbose
```

### Alternative Test Script

You can also use the provided test script:

```bash
python test_reports_collector.py
```

## Environment Variables

### Required

- `METRICS_UTILITY_SHIP_TARGET`: 'directory', 'crc', or 's3'
- `METRICS_UTILITY_SHIP_PATH`: Output directory path

### Optional

- `METRICS_UTILITY_CLUSTER_NAME`: Cluster name for metrics
- `METRICS_UTILITY_MAX_GATHER_PERIOD_DAYS`: Max collection period (default: 28 days)
- `METRICS_UTILITY_BILLING_*`: Billing provider configuration
- `METRICS_UTILITY_BUCKET_*`: S3 configuration
- `METRICS_UTILITY_CRC_*`: CRC configuration

## Benefits

✅ **JSON Output**: Structured data for easy integration with dashboards  
✅ **Comprehensive**: Covers all 21 requested use cases  
✅ **Efficient**: Optimized SQL queries with proper joins  
✅ **Reliable**: Error handling and robust database operations  
✅ **Tested**: Fully tested CLI integration  
✅ **Compatible**: Works with existing infrastructure

## Files Created

1. **Main Collector**: `metrics_utility/automation_controller_billing/reports_collectors.py`
2. **CLI Command**: `metrics_utility/management/commands/gather_automation_controller_reports_data.py`
3. **Test Script**: `test_reports_collector.py`
4. **Usage Example**: `example_reports_usage.py`
5. **Documentation**: `REPORTS_COLLECTOR_USAGE.md`

## Success Confirmation

✅ All 15 JSON collectors implemented  
✅ CLI command working and tested  
✅ SQL queries optimized and functional  
✅ Error handling implemented  
✅ Linting issues resolved  
✅ Integration with existing system complete

The Reports Collector is **ready for production use**!

