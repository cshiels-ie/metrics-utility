# AWX Unified JSON Reports System

## Overview

This system provides a complete end-to-end solution for collecting, aggregating, and submitting AWX Automation Controller metrics as unified JSON reports to HTTP endpoints.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data          │    │   Unified        │    │   HTTP          │
│   Collection    │───▶│   JSON Report    │───▶│   Endpoint      │
│                 │    │   Builder        │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
      Step 1                   Step 2                 Step 3
```

## Step 1: Data Collection

### Command: `gather_automation_controller_reports_data`

Collects 15 different JSON metrics covering all specified use cases.

```bash
# Basic collection
python manage.py gather_automation_controller_reports_data --since=7d --ship

# With custom output
export METRICS_UTILITY_SHIP_TARGET=directory
export METRICS_UTILITY_SHIP_PATH=/path/to/output
python manage.py gather_automation_controller_reports_data --since=7d --ship
```

### Collected Metrics (15 JSON files):

1. **Cluster Metrics**

   - `active_clusters_count.json` - Active number of clusters
   - `active_clusters_by_controller_version.json` - Active clusters by controller version

2. **Job Metrics**

   - `job_duration_stats_by_template.json` - Job duration statistics (avg/min/max/total)
   - `job_execution_stats.json` - Job success/failure counts and ratios
   - `avg_tasks_by_template.json` - Average tasks by template

3. **Task Metrics**

   - `task_execution_stats.json` - Task execution statistics and success ratios

4. **Module Metrics**

   - `total_modules_automated.json` - Total number of modules automated
   - `module_success_failure_rates.json` - Module success/failure rates
   - `modules_usage_by_job_kpi.json` - KPI - modules used across customers by job ID
   - `modules_used_to_automate.json` - Modules used to automate analysis
   - `avg_modules_per_playbook.json` - Average modules used in playbooks

5. **Template Metrics**

   - `templates_executed_by_company.json` - Templates executed by organization

6. **Host Metrics**

   - `total_hosts_automated_over_time.json` - Hosts automated over time

7. **Execution Environment Metrics**

   - `execution_environment_stats.json` - EE configuration and ratios

8. **System Metadata**
   - `config.json` - Configuration metadata
   - `manifest.json` - Collection manifest

## Step 2: Unified JSON Report Building

### Command: `build_reports_json`

Aggregates collected JSON files into a unified report structure.

```bash
# Basic build and save to file
python manage.py build_reports_json --output=/path/to/unified_report.json

# Build and send to endpoint
python manage.py build_reports_json --endpoint=https://api.example.com/reports

# Build with date filtering
python manage.py build_reports_json --since=7d --until=1d --endpoint=https://api.example.com/reports

# Dry run (generate but don't send)
python manage.py build_reports_json --endpoint=https://api.example.com/reports --dry-run
```

### Unified Report Structure

```json
{
  "report_metadata": {
    "report_type": "awx_unified_json_report",
    "report_version": "1.0",
    "generated_at": "2025-09-01T13:12:25.022984Z",
    "collector_version": "1.0",
    "collector_module": "reports_collectors",
    "period_start": "2025-08-25T00:00:00Z",
    "period_end": "2025-09-01T00:00:00Z",
    "customer_id": "CUST001",
    "cluster_id": "CLUSTER001",
    "environment": "production",
    "total_json_files": 16
  },
  "cluster_metrics": {
    "active_clusters": {...},
    "clusters_by_version": {...}
  },
  "job_metrics": {
    "execution_stats": {...},
    "duration_stats_by_template": {...},
    "avg_tasks_by_template": {...}
  },
  "task_metrics": {
    "execution_stats": {...}
  },
  "module_metrics": {
    "total_automated": {...},
    "success_failure_rates": {...},
    "usage_by_job": {...},
    "modules_used": {...},
    "avg_per_playbook": {...}
  },
  "template_metrics": {
    "executed_by_company": {...}
  },
  "host_metrics": {
    "automated_over_time": {...}
  },
  "execution_environment_metrics": {
    "stats": {...}
  },
  "raw_data": {
    "manifest": {...},
    "config": {...}
  }
}
```

## Step 3: HTTP Endpoint Submission

### Configuration

Set environment variables for endpoint submission:

```bash
# Core configuration
export METRICS_UTILITY_SHIP_TARGET=directory
export METRICS_UTILITY_SHIP_PATH=/path/to/collected/data

# Endpoint configuration
export METRICS_UTILITY_ENDPOINT_URL=https://api.example.com/reports
export METRICS_UTILITY_ENDPOINT_TOKEN=your-auth-token
export METRICS_UTILITY_ENDPOINT_HEADERS='{"X-Customer-ID": "123", "X-Source": "AWX"}'

# Report metadata
export METRICS_UTILITY_REPORT_CUSTOMER_ID=CUST001
export METRICS_UTILITY_REPORT_CLUSTER_ID=CLUSTER001
export METRICS_UTILITY_REPORT_ENVIRONMENT=production
```

### HTTP Request Details

The system sends a POST request with:

- **Content-Type**: `application/json`
- **User-Agent**: `AWX-Reports-Collector/1.0`
- **Authorization**: `Bearer {token}` (if token provided)
- **Custom Headers**: Any additional headers from `METRICS_UTILITY_ENDPOINT_HEADERS`

### Response Handling

- **200 OK**: Report successfully received
- **400 Bad Request**: Invalid JSON or request format
- **401 Unauthorized**: Authentication failed
- **500 Server Error**: Server-side processing error

## Complete Workflow Example

### 1. Collect Data

```bash
source .venv/bin/activate

# Set collection configuration
export METRICS_UTILITY_SHIP_TARGET=directory
export METRICS_UTILITY_SHIP_PATH=/tmp/awx_reports

# Collect data for the last 7 days
python manage.py gather_automation_controller_reports_data --since=7d --ship --verbose
```

### 2. Build and Submit Unified Report

```bash
# Set endpoint configuration
export METRICS_UTILITY_ENDPOINT_URL=https://your-api.com/awx-reports
export METRICS_UTILITY_ENDPOINT_TOKEN=your-secure-token
export METRICS_UTILITY_REPORT_CUSTOMER_ID=CUSTOMER123
export METRICS_UTILITY_REPORT_CLUSTER_ID=AWX-PROD-01

# Build and submit report
python manage.py build_reports_json --since=7d --verbose

# Or save locally and submit separately
python manage.py build_reports_json --output=/tmp/report.json --since=7d
python manage.py build_reports_json --endpoint=https://your-api.com/awx-reports
```

## Environment Variables Reference

### Collection Variables

- `METRICS_UTILITY_SHIP_TARGET` (required): `directory`, `s3`
- `METRICS_UTILITY_SHIP_PATH` (required): Path for data storage
- `METRICS_UTILITY_CLUSTER_NAME` (optional): Cluster name for metrics

### Endpoint Variables

- `METRICS_UTILITY_ENDPOINT_URL` (optional): Default endpoint URL
- `METRICS_UTILITY_ENDPOINT_TOKEN` (optional): Authentication token
- `METRICS_UTILITY_ENDPOINT_HEADERS` (optional): JSON string of custom headers

### Report Metadata Variables

- `METRICS_UTILITY_REPORT_CUSTOMER_ID` (optional): Customer identifier
- `METRICS_UTILITY_REPORT_CLUSTER_ID` (optional): Cluster identifier
- `METRICS_UTILITY_REPORT_ENVIRONMENT` (optional): Environment name

### S3 Variables (if using S3)

- `METRICS_UTILITY_BUCKET_NAME`: S3 bucket name
- `METRICS_UTILITY_BUCKET_ENDPOINT`: S3 endpoint URL
- `METRICS_UTILITY_BUCKET_ACCESS_KEY`: S3 access key
- `METRICS_UTILITY_BUCKET_SECRET_KEY`: S3 secret key
- `METRICS_UTILITY_BUCKET_REGION`: S3 region

## Testing

### Test Endpoint Server

Use the provided test server to verify functionality:

```bash
# Start test server
python test_endpoint_server.py &

# Test submission
python manage.py build_reports_json --endpoint=http://localhost:8080/reports --verbose

# Stop test server
pkill -f test_endpoint_server.py
```

### Validation

Verify your setup with dry runs:

```bash
# Test collection
python manage.py gather_automation_controller_reports_data --dry-run --since=1d --verbose

# Test report building
python manage.py build_reports_json --dry-run --endpoint=https://your-api.com/reports --verbose
```

## Benefits

✅ **Complete Solution**: End-to-end data collection to endpoint submission  
✅ **Structured Data**: Well-organized JSON format for easy parsing  
✅ **Comprehensive Metrics**: All 21 requested use cases covered  
✅ **Flexible Endpoints**: Support for any HTTP endpoint with authentication  
✅ **Production Ready**: Error handling, logging, and configuration management  
✅ **Backward Compatible**: Works alongside existing metrics utility

## Files Structure

```
metrics_utility/
├── automation_controller_billing/
│   ├── reports_collectors.py          # JSON data collectors
│   └── collector.py                   # Base collector (unchanged)
├── management/commands/
│   ├── gather_automation_controller_reports_data.py  # Collection command
│   └── build_reports_json.py          # Unified report builder
├── test_endpoint_server.py            # Test HTTP server
├── UNIFIED_JSON_REPORTS_GUIDE.md      # This documentation
└── REPORTS_COLLECTOR_USAGE.md         # Collection-specific docs
```

## Support

The system provides comprehensive logging and error handling. Use `--verbose` flag for detailed debugging information.

For issues:

1. Check environment variables are set correctly
2. Verify network connectivity to endpoints
3. Review logs for specific error messages
4. Test with `--dry-run` first

**Your AWX Unified JSON Reports System is ready for production use!** 🚀

