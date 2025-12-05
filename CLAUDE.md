# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup

```bash
# Install uv package manager (if not installed)
pip install uv

# Synchronize dependencies from pyproject.toml and uv.lock
uv sync

# Verify installation
ruff --version
pytest --version
```

### Testing

```bash
# Run all tests (standalone mode, some require database)
uv run pytest -s -v

# Run specific test file
uv run pytest -s -v metrics_utility/test/gather/test_jobhostsummary_gather.py

# Run specific test function
uv run pytest -s -v metrics_utility/test/gather/test_jobhostsummary_gather.py::test_command

# Run with coverage report
uv run pytest -s -v --cov=. --cov-report=html

# Using Makefile shortcuts
make test           # Run all tests
make coverage       # Run tests with HTML coverage report
```

### Docker/Podman Testing (CI mode - all tests)

Start required services (PostgreSQL and Minio):

```bash
# Start services
docker compose -f tools/docker/docker-compose.yaml up

# Start with environment container for running tests inside
docker compose -f tools/docker/docker-compose.yaml --profile=env up -d

# Load SQL test data (only needed once after starting containers)
docker compose -f tools/docker/docker-compose.yaml exec postgres bash -c \
  'cat /docker-entrypoint-initdb.d/init-*.sql | psql -U awx -d postgres'

# Run all gather tests (inside container)
docker compose -f tools/docker/docker-compose.yaml exec metrics-utility-env bash -c \
  'sed -i "/NAME/s/awx/postgres/" mock_awx/settings/__init__.py && \
   sed -i "/USER/s/myuser/awx/" mock_awx/settings/__init__.py && \
   sed -i "/PASSWORD/s/mypassword/awx/" mock_awx/settings/__init__.py && \
   sed -i "/HOST.*localhost/s/localhost/postgres/" mock_awx/settings/__init__.py && \
   uv run pytest -s -v metrics_utility/test/gather/'

# Run all tests
docker compose -f tools/docker/docker-compose.yaml exec metrics-utility-env bash -c \
  'sed -i "/NAME/s/awx/postgres/" mock_awx/settings/__init__.py && \
   sed -i "/USER/s/myuser/awx/" mock_awx/settings/__init__.py && \
   sed -i "/PASSWORD/s/mypassword/awx/" mock_awx/settings/__init__.py && \
   sed -i "/HOST.*localhost/s/localhost/postgres/" mock_awx/settings/__init__.py && \
   uv run pytest -s -v'

# Interactive container shell (wait for services to start)
docker exec -it metrics-utility-env /bin/sh

# Clean up containers and volumes
make clean
# OR
docker compose -f tools/docker/docker-compose.yaml down -v
```

Replace `docker` with `podman` for Podman users. Use `CONTAINER_ENGINE=podman make compose` to override.

### Code Quality

```bash
# Lint code (check for issues)
ruff check
uv run ruff check

# Check formatting without changes
ruff format --check
uv run ruff format --check

# Auto-fix linting issues
ruff check --fix
uv run ruff check --fix

# Auto-format code
ruff format
uv run ruff format

# Using Makefile shortcuts
make lint           # Check linting and formatting
make fix            # Auto-fix linting and formatting issues
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks (runs ruff on every commit)
pre-commit install

# Manually run hooks on all files
pre-commit run --all-files
```

### Django Management Commands

The project uses Django management commands via `manage.py`. Run commands using:

```bash
# Standalone mode (development/testing)
uv run python manage.py <command> [options]

# Controller mode (inside AAP Controller container)
# Activate virtual environment first:
# source /var/lib/awx/venv/awx/bin/activate
python manage.py <command> [options]

# RPM installation mode
metrics-utility <command> [options]
```

#### Primary Commands

**`gather_automation_controller_billing_data`** - Collect metrics from Controller database and save as daily tarballs:

```bash
# Collect and ship data for last 12 months
uv run python manage.py gather_automation_controller_billing_data --ship --since=12m

# Collect data until 10 months ago (with --until)
uv run python manage.py gather_automation_controller_billing_data --ship --until=10m

# Dry run (no actual data collection)
uv run python manage.py gather_automation_controller_billing_data --dry-run --since=12m

# Force overwrite existing data
uv run python manage.py gather_automation_controller_billing_data --ship --since=12m --force
```

**`build_report`** - Generate XLSX reports from collected data or Controller database:

```bash
# Build CCSPv2 report for specific month
export METRICS_UTILITY_REPORT_TYPE="CCSPv2"
uv run python manage.py build_report --month=2024-04 --force

# Build RENEWAL_GUIDANCE report from database
export METRICS_UTILITY_REPORT_TYPE="RENEWAL_GUIDANCE"
uv run python manage.py build_report --since=12months --ephemeral=1month --force

# Additional options
# --force: Overwrite existing reports
# --verbose: Detailed logging
# --ephemeral=<period>: Use ephemeral data for specific period
```

### Environment Variables

Key configuration environment variables (prefix with `METRICS_UTILITY_`):

**Report Configuration:**
- `METRICS_UTILITY_REPORT_TYPE` - Report type: `CCSPv2`, `CCSP`, `RENEWAL_GUIDANCE`
- `METRICS_UTILITY_SHIP_TARGET` - Storage target: `directory`, `s3`, `controller_db`
- `METRICS_UTILITY_SHIP_PATH` - Path for storing data/reports

**S3 Storage (when SHIP_TARGET=s3):**
- `METRICS_UTILITY_BUCKET_NAME` - S3 bucket name
- `METRICS_UTILITY_BUCKET_ENDPOINT` - S3 endpoint URL
- `METRICS_UTILITY_BUCKET_REGION` - S3 region (optional for AWS)
- `METRICS_UTILITY_BUCKET_ACCESS_KEY` - S3 access key
- `METRICS_UTILITY_BUCKET_SECRET_KEY` - S3 secret key

**Report Metadata:**
- `METRICS_UTILITY_PRICE_PER_NODE` - Price per managed node (USD)
- `METRICS_UTILITY_REPORT_COMPANY_NAME` - Partner company name
- `METRICS_UTILITY_REPORT_EMAIL` - Contact email
- `METRICS_UTILITY_REPORT_SKU` - Product SKU
- `METRICS_UTILITY_REPORT_PO_NUMBER` - Purchase order number

For complete list, see README.md.

### Makefile Shortcuts

```bash
make help           # Show available commands
make sync           # Sync dependencies with uv
make test           # Run all tests
make coverage       # Run tests with HTML coverage
make lint           # Check code quality
make fix            # Auto-fix linting and formatting
make compose        # Start Docker services
make clean          # Stop and remove Docker services
make psql           # Access PostgreSQL shell in container
```

## Architecture Overview

### Project Structure

This is a Django-based CLI utility for collecting and reporting metrics from Ansible Automation Platform (AAP) Controller instances.

**Key directories:**
- **`metrics_utility/library/`** - Core Python library with abstractions for collectors, storage, dataframes, and reports
- **`metrics_utility/automation_controller_billing/`** - Controller-specific data collection and report generation
- **`metrics_utility/anonymized_rollups/`** - Anonymized data aggregation
- **`metrics_utility/management/commands/`** - Django management commands (gather_automation_controller_billing_data, build_report)
- **`metrics_utility/test/`** - Comprehensive test suite organized by feature
- **`mock_awx/`** - Mock AWX settings for standalone testing
- **`tools/docker/`** - Docker Compose configuration for testing environment
- **`docs/`** - Documentation including developer setup and old README

### Operating Modes

1. **Controller Mode**: Runs inside AAP Controller containers, connects to live Controller database
2. **Standalone Mode**: Development/testing mode, uses PostgreSQL with imported test data, mocks AWX values

### Core Abstractions (`metrics_utility/library/`)

The library provides a modular architecture with clear separation of concerns:

**Collectors** (`library/collectors/`):
- Python functions that gather data from Controller database or other sources
- Accept parameters (db connection, time boundaries, output directory)
- Return either Python dicts (serialized to JSON) or filenames of temporary CSV files
- Time boundaries use `since` (inclusive start) and `until` (exclusive end) convention
- Controller collectors: `config`, `execution_environments`, `job_host_summary`, `unified_jobs`, etc.
- Other collectors: `total_workers_vcpu` (Prometheus-based)

**Package** (`library/package.py`):
- Groups multiple collector outputs into `.tar.gz` archives
- Each tarball contains: `config.json`, `manifest.json`, `data_collection_status.csv`, and collector CSV/JSON files
- Handles size constraints and file naming
- Manages cleanup of temporary files

**Storage** (`library/storage/`):
- Unified interface for different storage backends
- Common API: `put(name, dict=... | filename=... | fileobj=...)`, `get(name)`, `exists(name)`, `remove(name)`, `glob(pattern)`
- Implementations: `StorageDirectory` (local filesystem), `StorageS3` (S3/Minio), `StorageSegment` (analytics), `StorageCRC` (console.redhat.com)

**Extractors** (`library/extractors.py`):
- Opposite of Package - reads tarballs and extracts dataframes
- Supports filtering to load subset of data

**Dataframes** (`library/dataframes/`):
- Pandas DataFrames with additional metadata and methods
- Always knows fields/indexes even when empty
- Methods: `add_csv()`, `group()`, `add_parquet()`, `regroup()`, `to_csv()`, `to_parquet()`, `to_json()`
- Supports rollup process: build from raw CSV, aggregate, save as Parquet

**Reports** (`library/reports.py`):
- Predefined classes that generate XLSX reports from dataframes
- Implementations: `ReportCCSP`, `ReportCCSPv2`, `ReportRenewalGuidance`
- Take dataframes and configuration, produce XLSX files for storage

**Helpers**:
- **`library/instants.py`**: Datetime utilities returning UTC-aware datetime objects (`now()`, `days_ago(n)`, `this_month()`, `last_month()`, `iso(dt)`)
- **`library/lock.py`**: File locking for concurrent operations
- **`library/csv_file_splitter.py`**: Split large CSV files by size constraints

### Report Types

**CCSPv2** - Cloud Customer Success Program v2 report:
- Uses collected metrics tarballs to produce usage reports
- Aggregates managed node usage over time
- Requires pre-collected data via `gather_automation_controller_billing_data`

**CCSP** - Legacy Cloud Customer Success Program report:
- Similar to v2 with different aggregation logic
- Uses collected tarballs

**RENEWAL_GUIDANCE** - Renewal guidance report:
- Uses Controller database directly (no pre-collection needed)
- Analyzes usage patterns for license renewal planning
- Supports ephemeral data analysis

### Data Collection Workflow

1. **Gather Phase**: `gather_automation_controller_billing_data` runs collectors, packages results into dated tarballs, stores in configured storage
2. **Build Phase**: `build_report` extracts tarballs (or queries database), loads into dataframes, generates XLSX report, saves to storage
3. **Storage**: Data organized by date and instance UUID: `data/YYYY/MM/uuid/metrics_*.tar.gz`, reports: `reports/YYYY/MM/report.xlsx`

### Testing Strategy

**Test organization:**
- `test/gather/` - Data collection tests (require PostgreSQL)
- `test/ccspv_reports/` - CCSPv2 report generation tests
- `test/renewal_guidance/` - Renewal guidance report tests
- `test/library/` - Unit tests for library abstractions (collectors, storage, dataframes)
- `test/base/` - Base test utilities
- `test/conftest.py` - Shared pytest fixtures

**Test dependencies:**
- PostgreSQL database (via Docker Compose)
- Minio for S3 storage testing
- Mock AWX settings in `mock_awx/settings/__init__.py`

**Running tests:**
- Standalone: `uv run pytest -s -v` (limited tests without database)
- Docker CI mode: Full test suite with database and services
- Use `sed` commands in Docker to configure mock_awx database connection

## Code Style Standards

- **Line length**: 150 characters (configured in pyproject.toml)
- **Quote style**: Single quotes for strings (ruff format)
- **Indentation**: 4 spaces, no tabs
- **Import organization**: Sorted with ruff, separated by type with blank lines
- **Linting**: Comprehensive ruff rules (PEP 8 errors, warnings, naming, import sorting)

## Development Patterns

### Package Management
- **UV**: Use `uv` for fast dependency management (`uv sync` to install)
- **Dependencies**: Managed in `pyproject.toml` with locked versions in `uv.lock`
- **Virtual environment**: `.venv/` created by uv, use `uv run` prefix or activate manually

### Version Management
- Version defined in `setup.cfg` (`version = 0.7.0dev`)
- Dynamic versioning via setuptools_scm (disabled in current config)
- Version mapping to AAP releases documented in README.md

### Django Settings
- Mock AWX settings in `mock_awx/settings/__init__.py` for standalone mode
- Database connection configured via environment or direct settings modification

### Datetime Handling
- All collectors use UTC-aware datetime objects
- `since` is inclusive (first moment of interval), `until` is exclusive (first moment outside interval)
- Use helpers from `library/instants.py` for consistent datetime operations

### Example Workflows

**Collect and build CCSPv2 report:**
```bash
export METRICS_UTILITY_REPORT_TYPE="CCSPv2"
export METRICS_UTILITY_SHIP_TARGET="directory"
export METRICS_UTILITY_SHIP_PATH="./test/test_data/"
export METRICS_UTILITY_PRICE_PER_NODE=11.55
export METRICS_UTILITY_REPORT_COMPANY_NAME="Partner A"
# ... set other report metadata env vars ...

# Collect data
uv run python manage.py gather_automation_controller_billing_data --ship --until=10m --force

# Build report
uv run python manage.py build_report --month=2024-04 --force
```

**Generate renewal guidance from database:**
```bash
export METRICS_UTILITY_REPORT_TYPE="RENEWAL_GUIDANCE"
export METRICS_UTILITY_SHIP_TARGET="controller_db"
export METRICS_UTILITY_SHIP_PATH="./out"

uv run python manage.py build_report --since=12months --ephemeral=1month --force
```
