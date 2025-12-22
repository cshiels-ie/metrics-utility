# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

metrics-utility is a Python tool for collecting, analyzing, and reporting metrics from Ansible Automation Platform (AAP) Controller instances. It provides both a CLI and a Python library interface.

**Key capabilities:**
- Collect usage data from Controller databases, settings, and Prometheus
- Package data into daily tarballs (CSV/JSON format)
- Generate Excel reports (CCSP, CCSPv2, RENEWAL_GUIDANCE)
- Support multiple storage backends (local directory, S3, console.redhat.com)

**Operational modes:**
- **Standalone mode**: Development/testing against a postgres instance with imported data
- **Controller mode**: Inside Controller's Python virtualenv with direct access to settings
- **RPM mode**: Installed via RPM package

## Development Commands

### Setup and Dependencies
```bash
# Install dependencies
uv sync

# Start docker compose environment (postgres + minio on ports 5432, 9000/9001)
make compose

# Clean docker environment
make clean
```

### Testing
```bash
# Run all tests (requires docker compose to be running)
make test

# Run tests with verbose output
uv run pytest -s -v

# Run specific test file
uv run pytest -s -v metrics_utility/test/ccspv_reports/test_CCSP.py

# Generate coverage report
make coverage
```

### Code Quality
```bash
# Check linting and formatting
make lint

# Auto-fix linting and formatting issues
make fix
```

### Database Access
```bash
# Access postgres shell in docker container
make psql
```

### Running the CLI
```bash
# Launch the interactive TUI (recommended for configuration)
uv run ./manage.py tui

# Launch TUI with specific profile
uv run ./manage.py tui --profile=production

# Gather data from controller (traditional CLI)
uv run ./manage.py gather_automation_controller_billing_data --ship --until=10m

# Build a report (traditional CLI)
uv run ./manage.py build_report --month=2024-06 --force

# Get help for commands
uv run ./manage.py --help
uv run ./manage.py gather_automation_controller_billing_data --help
uv run ./manage.py build_report --help
uv run ./manage.py tui --help
```

## Architecture Overview

### High-Level Structure

The codebase is organized into two main layers:

1. **Library Layer** (`metrics_utility/library/`): Pure Python abstractions with no environment dependencies
2. **CLI Layer** (`metrics_utility/automation_controller_billing/`, `metrics_utility/management/`): Django-based CLI that wraps the library and handles environment configuration

### Library Abstractions (`metrics_utility/library/`)

The library provides reusable components that work independently:

**Collectors** (`library/collectors/`):
- Functions that gather data from databases or other sources
- Return either Python dicts (serialized to JSON) or lists of temporary CSV filenames
- Controller collectors: `config`, `execution_environments`, `job_host_summary`, `main_host`, `main_jobevent`, `unified_jobs`, etc.
- Other collectors: `total_workers_vcpu` (from Prometheus/Kubernetes)
- Use `since`/`until` datetime boundaries where `since` is inclusive, `until` is exclusive
- Decorated to support initialization pattern: `collector(db=conn).gather()`

**Package** (`library/package.py`):
- Takes initialized collectors and produces `.tar.gz` tarballs containing:
  - `config.json` (from config collector)
  - `manifest.json` (collector version info)
  - `data_collection_status.csv` (collector run status)
  - Multiple `*.csv` and `*.json` files from collectors
- Handles file size constraints and multi-tarball output

**Storage** (`library/storage/`):
- Unified interface for storage backends
- Common API: `put(name, dict=/filename=/fileobj=)`, `get(name)` (context manager), `exists()`, `remove()`, `glob()`
- Implementations: `StorageDirectory`, `StorageS3`, `StorageSegment`, `StorageCRC`, `StorageCRCMutual`

**Extractors** (`library/extractors.py`):
- Opposite of Package - reads tarballs from storage
- Returns raw pandas DataFrames compatible with Dataframe classes

**Dataframes** (`library/dataframes/`):
- Pandas DataFrames with metadata and helper methods
- Methods: `add_csv()` (pre-rollup), `group()` (convert to post-rollup), `add_parquet()` (rollup data), `regroup()`, `to_csv()`, `to_parquet()`, `to_json()`
- Rollups aggregate raw CSV data and save to Parquet format

**Reports** (`library/reports.py`):
- Generate XLSX files from DataFrames
- Report types: `ReportCCSP`, `ReportCCSPv2`, `ReportRenewalGuidance`

**Helpers**:
- `library/instants.py`: Datetime utilities (`now()`, `this_day()`, `last_month()`, `days_ago(n)`, etc.) - all return UTC datetime objects
- `library/lock.py`: Database locking helpers
- `library/utils.py`: Temporary directory and other utilities

### CLI Layer

**Django Management Commands** (`metrics_utility/management/commands/`):
- `gather_automation_controller_billing_data.py`: Collects data and saves tarballs
- `build_report.py`: Generates XLSX reports from tarballs or database

**Supporting Modules** (`metrics_utility/automation_controller_billing/`):
- `package/`: Factory for Package implementations (directory, S3, CRC)
- `extract/`: Factory for Extractor implementations (directory, S3, controller_db)
- `report/`: Factory for Report implementations (CCSP, CCSPv2, RENEWAL_GUIDANCE)
- `dataframe_engine/`: Dataframe classes with specific aggregation logic
- `dedup/`: Deduplication strategies for reports
- `report_saver/`: Factory for saving reports to storage

**Mock AWX** (`mock_awx/`):
- Provides minimal AWX/Controller environment simulation for standalone development
- Mocks settings that would normally come from Controller

### Data Flow

**Gather workflow:**
1. CLI reads environment variables
2. Initializes collectors with DB connection and time boundaries
3. Package calls collectors and creates tarballs
4. Storage saves tarballs to configured backend (directory/S3/CRC)

**Report workflow:**
1. CLI reads environment variables and report configuration
2. Extractor loads tarballs from storage (or reads directly from DB for RENEWAL_GUIDANCE)
3. DataFrames aggregate and process data
4. Deduplicator removes duplicate managed nodes
5. Report generates XLSX file
6. ReportSaver stores report to configured location

### Time Boundary Conventions

Throughout the codebase, time ranges follow this convention:
- `since`: First moment of the interval (INCLUSIVE)
- `until`: First moment outside the interval (EXCLUSIVE)
- This ensures no data is lost between periods (e.g., 23:59:59 to 00:00:00)

### Testing Structure

Tests are organized under `metrics_utility/test/`:
- `ccspv_reports/`: Integration tests for CCSP report generation
- `gather/`: Tests for data gathering functionality
- `management/commands/`: Tests for CLI commands
- `renewal_guidance/`: Tests for renewal guidance reports
- `snapshot_tests/`: Snapshot-based testing for report consistency
- `validation/`: Tests for parameter validation

Many tests require the docker compose environment (postgres + minio) to be running.

## Important Environment Variables

See `docs/environment.md` for the complete list. Key variables:

**Development:**
- `AWX_PATH`: Path to Controller virtualenv (default: `/awx_devel`)
- `METRICS_UTILITY_DB_HOST`: Database host for standalone mode

**Storage:**
- `METRICS_UTILITY_SHIP_TARGET`: Storage backend (`directory`, `s3`, `controller_db`, `crc`)
- `METRICS_UTILITY_SHIP_PATH`: Base path for storage

**S3 Configuration:**
- `METRICS_UTILITY_BUCKET_NAME`, `BUCKET_ENDPOINT`, `BUCKET_ACCESS_KEY`, `BUCKET_SECRET_KEY`, `BUCKET_REGION`

**Report Configuration:**
- `METRICS_UTILITY_REPORT_TYPE`: Report type (`CCSPv2`, `CCSP`, `RENEWAL_GUIDANCE`)
- `METRICS_UTILITY_PRICE_PER_NODE`: Price per managed node
- Various `METRICS_UTILITY_REPORT_*` variables for report metadata

**Collectors:**
- `METRICS_UTILITY_OPTIONAL_COLLECTORS`: Comma-separated list of optional collectors
- `METRICS_UTILITY_DISABLE_JOB_HOST_SUMMARY_COLLECTOR`: Disable specific collector
- `METRICS_UTILITY_PROMETHEUS_URL`: For Prometheus-based collectors

## Code Organization Notes

- The library layer (`metrics_utility/library/`) is environment-agnostic and uses no environment variables
- The CLI layer handles environment configuration and Django integration
- Collectors are decorated with `@collector` from `metrics_utility/base/decorators.py` to provide the initialization pattern
- All datetime operations should use the helpers from `library/instants.py` for consistency
- Storage operations use context managers to ensure proper cleanup of temporary files
- The package uses Python 3.12+ features; requires Python >=3.12

## Branch Strategy

- Main development branch: `devel`
- Create feature branches off `devel`
- PRs should target `devel`, not `main`/`master`

## Terminal User Interface (TUI)

### Overview

The TUI provides an interactive full-screen interface for configuring and running metrics-utility commands. It's built with the Textual framework and offers a modern, user-friendly alternative to managing environment variables and CLI flags.

**Location:** `metrics_utility/tui/`

### Key Features

- **Configuration Management**: Interactive forms for all 50+ configuration fields
- **Multi-Profile Support**: Create, switch, and manage multiple configuration profiles
- **Import/Export**: Export configs as YAML or shell scripts, import from files or environment
- **Validation**: Pre-flight checks for configuration completeness and connectivity
- **Command Execution**: Run gather/build commands with real-time output (Phase 3+)
- **Config Persistence**: YAML files at `~/.metrics-utility/config.yaml`

### Architecture

**Main Application** (`tui/app.py`):
- Textual App with header/footer and screen management
- Keyboard shortcuts: `C`=Config, `M`=Menu, `S`=Save, `Q`=Quit, `Esc`=Back

**Configuration** (`tui/config/`):
- `schema.py`: Complete schema of all fields with types, validators, categories
- `manager.py`: Config file + env var management (ENV > FILE > DEFAULTS precedence)
- `profiles.py`: Multi-profile support (not yet implemented)

**Screens** (`tui/screens/`):
- `main_menu.py`: Dashboard with config summary and quick actions
- `config_editor.py`: Tabbed interface for editing config by category (Core, S3, CRC, Billing, Collection, Report, Prometheus)
- `gather_screen.py`: Gather command UI with date parameters, ship/dry-run options
- `build_screen.py`: Build report UI with month/date parameters, force option
- `validation_screen.py`: Pre-flight checks with tree view of results
- `help_screen.py`: Help and documentation with usage guide
- `profile_manager.py`: Profile management UI (Phase 5 - future enhancement)

**Widgets** (`tui/widgets/`):
- `config_form.py`: Reusable form widget with dynamic field generation
  - Supports: text input, selects, checkboxes, password fields, multiselect
  - Context-aware: Shows/hides fields based on dependencies (e.g., S3 fields only when ship_target=s3)
  - Inline validation with error messages
- `command_output.py`: Real-time command output display with color-coded log levels

**Validators** (`tui/validators/`):
- `connectivity.py`: Async connectivity checks for Database, S3, CRC, and Filesystem
  - Database: Tests PostgreSQL connection with timeout
  - S3: Tests bucket access with boto3
  - CRC: Tests SSO endpoint and service account credentials
  - Filesystem: Validates write permissions for ship_path
- `field_validators.py`: Field-level validation functions
  - URL, email, date, month, path formats
  - Positive numbers, port ranges, integer ranges
  - Non-empty values

**Executors** (`tui/executors/`):
- `base.py`: Base command executor with async subprocess management and real-time output
- `gather_executor.py`: Gather command wrapper with parameter building
- `build_executor.py`: Build command wrapper with parameter building

### Configuration Schema

The schema (`tui/config/schema.py`) defines all fields with:
- **Field metadata**: key, display_name, description, type, category
- **Types**: STRING, INTEGER, FLOAT, BOOLEAN, SELECT, MULTISELECT, PASSWORD
- **Categories**: Core, S3, CRC, Billing, Collection, Report, Prometheus
- **Validation**: Required fields, custom validators, allowed values
- **Dependencies**: Conditional visibility (e.g., S3 fields require ship_target=s3)

Reuses constants from `management/validation.py` for consistency with CLI validation.

### Configuration Manager

The ConfigManager (`tui/config/manager.py`) handles:
- **Load/Save**: YAML files at `~/.metrics-utility/config.yaml`
- **Precedence**: ENV VARS > CONFIG FILE > DEFAULTS (12-factor app pattern)
- **Multi-profile**: Profiles stored in single YAML file
- **Type-aware parsing**: Handles booleans, integers, floats, lists
- **Import/Export**:
  - Export as YAML
  - Export as shell script (with `export` statements)
  - Import from YAML
  - Import from environment

### Current Implementation Status (Core Features Complete)

✅ **Phase 1 (Foundation)**:
- Dependencies added (Textual, PyYAML)
- Package structure created
- Configuration schema (50+ fields)
- Configuration manager with multi-profile support

✅ **Phase 2 (Basic TUI & Config Editor)**:
- Main TUI application with screen management
- Config form widget with dynamic field generation
- Config editor screen with tabbed categories
- Main menu/dashboard screen
- Django management command (`tui`)

✅ **Phase 3 (Command Execution)**:
- Base command executor with async subprocess execution
- Gather executor for `gather_automation_controller_billing_data`
- Build executor for `build_report`
- Real-time command output widget with color-coded log levels
- Gather screen with date parameters and options
- Build screen with month/date parameters and options
- Command cancellation support

✅ **Phase 4 (Validation)**:
- Connectivity validators for Database, S3, CRC, and Filesystem
- Async validation with concurrent checks
- Field validators for URLs, dates, emails, paths, numbers
- Validation screen with tree view of check results
- Color-coded pass/fail indicators

✅ **Phase 5 (Documentation & Help)**:
- Help screen with comprehensive usage guide
- Keyboard shortcuts reference
- Troubleshooting tips
- Configuration precedence documentation

🔜 **Future Enhancements**:
- Profile manager UI (backend already implemented, can use --profile flag)
- Enhanced import/export UI
- Report preview functionality
- Historical run logs

### Usage

```bash
# Launch TUI
uv run ./manage.py tui

# Launch with specific profile
uv run ./manage.py tui --profile=production

# TUI Keyboard Shortcuts
# C - Open configuration editor
# M - Return to main menu
# S - Save current configuration
# Q - Quit application
# Esc - Go back/close current screen
```

### Config File Format

```yaml
# ~/.metrics-utility/config.yaml
active_profile: default

profiles:
  default:
    # Core Configuration
    SHIP_TARGET: directory
    SHIP_PATH: ./out
    REPORT_TYPE: CCSPv2

    # S3 Configuration (shown only when SHIP_TARGET=s3)
    BUCKET_NAME: ""
    BUCKET_ENDPOINT: ""
    # ... other fields

  production:
    SHIP_TARGET: s3
    BUCKET_NAME: prod-metrics-bucket
    # ... other settings
```

### TUI Development Notes

- **Textual Framework**: Modern Python TUI framework (like htop/k9s)
- **Screen-based navigation**: Push/pop screens for different views
- **Reactive UI**: Forms update based on field dependencies
- **No environment pollution**: TUI doesn't modify environment variables, only config files
- **Integration**: Works alongside traditional CLI commands
- **Testing**: Unit tests for config manager and schema, integration tests for TUI flows

### Key Design Decisions

1. **Config precedence**: ENV VARS > FILE > DEFAULTS (allows temporary overrides)
2. **Subprocess execution**: Commands run in subprocess for isolation and safety
3. **YAML over JSON**: More readable, supports comments
4. **Single config file**: All profiles in `~/.metrics-utility/config.yaml`
5. **No CLI replacement**: TUI is additive, existing commands unchanged
6. **Contextual UI**: Fields shown/hidden based on dependencies (e.g., S3 fields only when needed)

## Additional Documentation

- `docs/cli.md`: Detailed CLI usage examples
- `docs/environment.md`: Complete environment variable reference
- `docs/awx.md`: Running against AWX development environment
- `docs/CONTRIBUTING.md`: Contribution guidelines and workflow
- `metrics_utility/library/README.md`: Detailed library API documentation
