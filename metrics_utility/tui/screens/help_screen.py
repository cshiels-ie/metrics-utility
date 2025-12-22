"""
Help and documentation screen for TUI.

Provides usage information and keyboard shortcuts.
"""

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Markdown, Static


class HelpScreen(Screen):
    """Screen for displaying help and documentation"""

    CSS = """
    HelpScreen {
        background: $surface;
    }

    #help-header {
        background: $panel;
        height: 3;
        padding: 1 2;
        text-align: center;
    }

    #help-content {
        margin: 1 2;
        height: 1fr;
    }

    #help-actions {
        background: $panel;
        height: 5;
        padding: 1 2;
        align: center middle;
    }

    Markdown {
        height: 1fr;
        margin: 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        """Create help screen widgets"""
        yield Static(
            'Help & Documentation',
            id='help-header',
            markup=False,
        )

        with VerticalScroll(id='help-content'):
            yield Markdown(self.get_help_content())

        with Container(id='help-actions'):
            yield Button('Close', variant='primary', id='btn-close')

    def get_help_content(self) -> str:
        """Generate help content in Markdown format"""
        return """
# Metrics Utility TUI

Welcome to the Metrics Utility Terminal User Interface!

## Quick Start

1. **Configure Settings**: Click "Edit Configuration" to set up your connection details
2. **Validate**: Click "Validate Configuration" to test connectivity
3. **Gather Data**: Click "Gather Data" to collect billing data from Controller
4. **Build Reports**: Click "Build Report" to generate CSV reports

## Keyboard Shortcuts

- **C** - Open configuration editor
- **M** - Return to main menu
- **S** - Save current configuration
- **Q** - Quit application
- **Esc** - Go back / Close current screen

## Configuration

Configuration is stored in `~/.metrics-utility/config.yaml` and organized into categories:

### Core Configuration
- **Ship Target**: Where to send data (directory, s3, crc)
- **Ship Path**: Local directory path for output
- **Report Type**: Type of report to generate (CCSPv2, etc.)

### S3 Configuration
Required when `Ship Target = s3`:
- Bucket name, endpoint URL, access credentials
- AWS region

### CRC Configuration
Required when `Ship Target = crc`:
- Ingress URL, SSO URL
- Service account credentials

### Collection & Reporting
- Cluster name
- Optional collectors
- Report metadata (SKU, company name, email, etc.)

## Configuration Precedence

The TUI follows the 12-factor app pattern for configuration:

**Environment Variables > Config File > Defaults**

This means:
- Environment variables take highest precedence
- Config file values are used if no env var is set
- Built-in defaults are used if neither is set

## Validation Checks

The validation screen performs pre-flight checks:

1. **Database Connectivity**: Tests PostgreSQL connection
2. **S3 Access**: Validates bucket permissions (if using S3)
3. **CRC Authentication**: Tests service account credentials (if using CRC)
4. **Filesystem Access**: Verifies write permissions (if using directory)

## Gather Command

Collect billing data from Automation Controller:

- **Since/Until Dates**: Date range for data collection (YYYY-MM-DD)
- **Ship**: Automatically ship collected data to configured target
- **Dry Run**: Preview what would be collected without making changes

## Build Report

Generate CSV reports from collected data:

- **Month**: Which month to build report for (YYYY-MM)
- **Since/Until**: Alternative date range specification
- **Force**: Rebuild even if report already exists
- **Ephemeral**: Path to ephemeral data (optional)

## Profiles

Use different configurations for different environments:

```bash
# Launch with specific profile
uv run ./manage.py tui --profile=production
uv run ./manage.py tui --profile=dev
```

Profiles are stored in the same config file under different keys.

## For More Information

- Documentation: `docs/` directory in project
- CLI Reference: `docs/cli.md`
- Environment Variables: `docs/environment.md`
- GitHub: Project repository

## Troubleshooting

### Text Not Displaying
If text appears invisible or incorrectly colored, check your terminal's color scheme and ensure it supports 256 colors.

### Validation Failures
Run validation checks to identify specific connectivity issues. Check:
- Database connection parameters
- Network connectivity
- Service credentials
- File permissions

### Command Errors
Check the command output panel for detailed error messages. Common issues:
- Missing required configuration
- Invalid date formats
- Permission denied errors
- Network timeouts

---

Press **Esc** or click **Close** to return to the previous screen.
"""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events"""
        if event.button.id == 'btn-close':
            self.app.pop_screen()
