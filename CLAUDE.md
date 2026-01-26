# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

metrics-utility is a tool for collecting, analyzing and reporting metrics from Ansible Automation Platform (AAP) Controller instances. It provides both a CLI tool and a Python library (`metrics_utility.library`).

The CLI collects Controller usage data from databases, settings, and prometheus, then generates Excel reports or pushes data to console.redhat.com. It can run standalone (against a specified postgres instance) or inside Controller's python virtual environment (controller mode).

## Common Commands

### Development Setup
```bash
# Install dependencies
uv sync

# Start docker compose environment (postgres + minio)
make compose

# Clean docker environment
make clean
```

### Running the CLI
```bash
# Show help
uv run ./manage.py --help
uv run ./manage.py gather_automation_controller_billing_data --help
uv run ./manage.py build_report --help
uv run ./manage.py migrate_to_storage --help

# Gather data (collect metrics and save to tarballs)
uv run ./manage.py gather_automation_controller_billing_data --ship --until=10m

# Build report (generate .xlsx from collected data)
uv run ./manage.py build_report --month=2024-04

# Migrate tables to long-term storage (full migration)
uv run ./manage.py migrate_to_storage --mode=full --verbose

# Migrate tables to long-term storage (incremental sync of last year)
uv run ./manage.py migrate_to_storage --since=1year --verbose
```

### Testing
```bash
# Run full test suite (requires make compose to be running)
make test

# Run with verbose output
uv run pytest -s -v

# Run specific test file
uv run pytest -s -v metrics_utility/test/path/to/test_file.py

# Generate coverage report
make coverage
```

### Linting & Formatting
```bash
# Check linting
make lint

# Auto-fix linting issues
make fix

# Install pre-commit hooks (optional)
uvx pre-commit install
```

### Database Access
```bash
# Access postgres in docker compose
make psql
```

## Architecture

### Dual Interface Design

The codebase has two main interfaces:

1. **CLI** (`metrics_utility.management.commands.*`)
   - Uses environment variables for configuration
   - Depends on Django and optionally AWX/Controller modules
   - Three main commands: `gather_automation_controller_billing_data`, `build_report`, and `migrate_to_storage`

2. **Python Library** (`metrics_utility.library`)
   - No environment variables - all configuration via parameters
   - No Controller environment dependency
   - Provides low-level building blocks that the CLI is built on top of

### Library Architecture

The library uses a pipeline architecture with these key abstractions:

- **Collectors** (`library.collectors.*`) - Gather specific data from database or APIs, return dicts (JSON) or temporary CSV files
- **Package** (`library.package`) - Groups multiple collector outputs into daily `.tar.gz` tarballs with manifests
- **Storage** (`library.storage.*`) - Unified interface for filesystem, S3, Segment, and CRC (console.redhat.com)
- **Extractors** (`library.extractors`) - Reads tarballs back into dataframes
- **Dataframes** (`library.dataframes.*`) - Pandas dataframes with schema awareness and grouping/aggregation methods
- **Reports** (`library.reports`) - Generate XLSX files from dataframes (ReportCCSP, ReportCCSPv2, ReportRenewalGuidance)
- **Migration** (`library.migration`) - Database-agnostic PostgreSQL table migration utilities (no Django dependency)

### Collector Timestamp Convention

All collectors accepting time boundaries use `since` and `until` parameters with timezone-aware datetime objects:
- `since` is INCLUSIVE - the first moment of the collected interval
- `until` is EXCLUSIVE - the first moment outside the collected interval
- This ensures no data is lost between boundary periods (e.g., 23:59:59 to 00:00:00)

### Helper Modules

- **instants** (`library.instants`) - Datetime helpers that follow the `since`/`until` convention (`now()`, `this_day()`, `last_month()`, `days_ago(n)`, etc.)
- **lock** (`library.lock`) - Database locking to prevent concurrent collection runs
- **tempdir** (`library.utils.tempdir`) - Context manager for temporary directories that auto-cleanup
- **CsvFileSplitter** (`library.csv_file_splitter`) - Splits large CSVs into smaller chunks

### Storage Migration

Database migration functionality exists at two levels:

#### 1. Library API (`library.migration`)

**Database-agnostic, no Django dependency** - Can be used in any Python application:

```python
from metrics_utility.library import migration, instants

# Connect to databases
source_db = migration.connect('controller.example.com', 5432, 'awx', 'awx', 'secret')
dest_db = migration.connect('storage.example.com', 5432, 'metrics_storage', 'user', 'pass')

# Full migration
success, message, row_count = migration.migrate_table_full(
    'main_host',
    migration.build_connection_string('controller.example.com', 5432, 'awx', 'awx', 'secret'),
    migration.build_connection_string('storage.example.com', 5432, 'metrics_storage', 'user', 'pass')
)

# Incremental sync (last 30 days)
success, message, row_count = migration.migrate_table_incremental(
    'main_host',
    source_db,
    dest_db,
    since=instants.days_ago(30),
    until=instants.now()
)
```

See `metrics_utility/library/MIGRATION.md` for full API documentation.

#### 2. CLI Command (`migrate_to_storage`)

Django management command built on the library:

- **Full migration mode**: Migrates entire tables including schema and all data
- **Incremental mode**: Migrates only time-windowed data based on timestamp columns
- **Table discovery**: Automatically finds all `main_*` tables or accepts specific table list
- **Schema creation**: Auto-creates schemas and custom PostgreSQL functions in destination
- **Validation**: Compares row counts between source and destination
- **Safety**: Never deletes source data (copy operation only)

Environment variables:
- `METRICS_UTILITY_STORAGE_DB_HOST` - Required
- `METRICS_UTILITY_STORAGE_DB_NAME` - Required
- `METRICS_UTILITY_STORAGE_DB_USER` - Required
- `METRICS_UTILITY_STORAGE_DB_PASSWORD` - Required
- `METRICS_UTILITY_STORAGE_DB_PORT` - Optional (default: 5432)
- `METRICS_UTILITY_STORAGE_DB_SCHEMA` - Optional (default: public)

### Key Directories

- `metrics_utility/library/` - Core library code (collectors, storage, dataframes, reports)
- `metrics_utility/management/commands/` - Django management commands (CLI entrypoints)
- `metrics_utility/storage_migration/` - Database migration utilities for long-term storage
- `metrics_utility/automation_controller_billing/` - Legacy CLI implementation (being migrated to library)
- `metrics_utility/test/` - Test suite
- `mock_awx/` - Mock AWX modules for standalone development
- `tools/docker/` - Docker compose environment with postgres & minio
- `workers/` - Example scripts showing library usage patterns

### Report Types

Three report types are supported (set via `METRICS_UTILITY_REPORT_TYPE`):
- **CCSPv2** - Uses collected tarballs, produces usage report with modern aggregation
- **CCSP** - Similar to CCSPv2 with slightly different aggregation (legacy)
- **RENEWAL_GUIDANCE** - Reads directly from Controller DB, produces renewal guidance report

## Code Style

The project uses `ruff` for linting and formatting with these key settings:
- Line length: 150 characters (not 88)
- Quote style: single quotes
- Import sorting: separate direct imports from `from` imports with blank line after imports

## Working with Controllers/Collectors

When adding or modifying collectors:
1. Controllers live in `metrics_utility/library/collectors/controller/` or `metrics_utility/library/collectors/others/`
2. Use the `@collector` decorator pattern (see existing collectors)
3. Return either a dict (for JSON) or a list of temporary CSV filenames
4. Accept `db` parameter for database connection (psycopg 3 or django.db.connection)
5. Accept `since` and `until` for time-bounded collections (both timezone-aware datetime)
6. Use `output_dir` parameter for specifying where to write temporary CSV files
7. Return `None` or empty list/dict when no data is present (don't raise exceptions)
8. Raise exceptions only for invalid parameters or connection failures

## Testing

Tests depend on docker compose environment (postgres + minio). Always run `make compose` before `make test`.

The test suite includes:
- Unit tests for individual components
- Integration tests for full gather/report workflows
- Snapshot tests for report consistency
- Performance tests using anonymized data

## Documentation

See the `docs/` directory for detailed documentation:
- `docs/cli.md` - CLI usage and examples
- `docs/environment.md` - All environment variables
- `docs/CONTRIBUTING.md` - Contribution workflow
- `docs/awx.md` - Running against AWX dev environment
- `metrics_utility/library/README.md` - Library API documentation

## Branch and PR Workflow

- Main development branch: `devel`
- Create feature branches off `devel`
- PRs target `devel`
- All PRs must pass linting and tests
- Internal contributors must sign commits
- Use forking workflow (fork → clone → branch → PR)
