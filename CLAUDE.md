# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AAP metrics-utility is a standalone CLI utility for collecting and reporting metrics from Ansible Automation Platform (AAP) Controller instances. The tool operates in two modes:
- **Controller mode**: Running inside Controller containers with direct access to awx modules
- **Standalone mode**: Development/testing mode using mock awx modules and PostgreSQL data

## Key Commands

### Development Setup
```bash
# Install dependencies and create virtual environment
uv sync

# Activate virtual environment (optional - uv run handles this automatically)
source .venv/bin/activate

# Run tests (standalone mode)
uv run pytest -s -v

# Run specific test file
uv run pytest -s -v metrics_utility/test/gather/test_jobhostsummary_gather.py::test_command

# Start development environment with containers
docker compose -f tools/docker/docker-compose.yaml up

# For full testing with database
docker compose -f tools/docker/docker-compose.yaml --profile=pytest up
```

### Linting & Formatting
```bash
# Check code style
uv run ruff check
uv run ruff format --check

# Auto-fix issues
uv run ruff check --fix
uv run ruff format

# Or use Makefile shortcuts (these use uv run internally)
make lint
make fix
```

### Main Application Commands
The application uses Django management commands. Always use `uv run` to ensure proper virtual environment:

```bash
# Collect metrics data
uv run python manage.py gather_automation_controller_billing_data --ship --until=10m --force

# Build reports from collected data
uv run python manage.py build_report --month=2024-04 --force

# Example with different report types
export METRICS_UTILITY_REPORT_TYPE="CCSPv2"  # or "CCSP", "RENEWAL_GUIDANCE"
uv run python manage.py build_report --since=12months --ephemeral=1month --force

# Alternative: activate venv first, then use python directly
source .venv/bin/activate
python manage.py build_report --month=2024-04 --force
```

## Architecture

### Core Structure
- **`metrics_utility/`**: Main package
  - **`management/commands/`**: Django management commands
    - `gather_automation_controller_billing_data.py`: Data collection
    - `build_report.py`: Report generation
  - **`automation_controller_billing/`**: Core billing logic
    - `extract/`: Data extraction from various sources
    - `package/`: Data packaging and tarball creation
    - `report/`: Report generation (CCSP, CCSPv2, RENEWAL_GUIDANCE)
    - `report_saver/`: Report output handling
    - `dataframe_engine/`: Pandas-based data processing
  - **`base/`**: Shared utilities and base classes
  - **`test/`**: Test suite with sample data

### Key Concepts
- **Report Types**: CCSP, CCSPv2 (usage reports), RENEWAL_GUIDANCE (renewal guidance)
- **Ship Targets**: `directory`, `s3`, `crc` (console.redhat.com), `controller_db`
- **Mock Environment**: `mock_awx/` provides standalone development without Controller dependency
- **Data Pipeline**: Extract → Package → Report → Save

### Environment Configuration
The application heavily relies on environment variables for configuration:
- `METRICS_UTILITY_SHIP_TARGET`: Storage mechanism (required)
- `METRICS_UTILITY_REPORT_TYPE`: Report format
- `METRICS_UTILITY_SHIP_PATH`: Output directory
- Database connection settings for standalone mode
- AWS S3 credentials for S3 storage
- Console.redhat.com credentials for CRC shipping

### Testing Strategy
- **Standalone tests**: `uv run pytest -s -v` (some require containers)
- **Container-based tests**: Full integration with PostgreSQL and MinIO
- **Gather tests**: Require database configuration modifications for container mode
- **Snapshot tests**: Compare generated reports against known good outputs

## Async Library Interface

The project now includes an async library interface in `metrics_utility/lib/` for programmatic integration:

```python
from metrics_utility import AsyncMetricsClient, CollectionConfig, ReportConfig

client = AsyncMetricsClient()
result = await client.collect_data(collection_config)
report_result = await client.generate_report(report_config)
```

Key library components:
- **AsyncMetricsClient**: Main async client for all operations
- **CollectionConfig/ReportConfig**: Type-safe configuration dataclasses
- **Environment isolation**: Each operation runs with isolated environment variables
- **Thread-safe**: Safe for concurrent operations
- **Full feature parity**: All CLI functionality available through library

See `metrics_utility/lib/README.md` and `metrics_utility/lib/examples.py` for detailed usage.

## Development Notes

- Uses `uv` for dependency management and virtual environments
- Code style enforced by `ruff` with pre-commit hooks
- Django-based management command structure
- Supports both Docker and Podman for containerized development
- Pre-commit hooks configured for automatic linting
- Async library preserves all existing CLI functionality