"""
Configuration validation screen for TUI.

Provides pre-flight checks for database, S3, CRC connectivity and configuration.
"""

import asyncio

from typing import Dict, Tuple

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Static, Tree

from ..config.manager import ConfigManager
from ..validators.connectivity import ConnectivityValidator


class ValidationScreen(Screen):
    """Screen for validating configuration and connectivity"""

    CSS = """
    ValidationScreen {
        background: $surface;
    }

    #validation-header {
        background: $panel;
        height: 3;
        padding: 1 2;
        text-align: center;
    }

    #validation-status {
        background: $panel;
        margin: 1 2;
        padding: 1 2;
        height: auto;
    }

    #validation-results {
        margin: 1 2;
        height: 1fr;
    }

    #validation-actions {
        background: $panel;
        height: 5;
        padding: 1 2;
        align: center middle;
    }

    .action-button {
        margin: 0 1;
    }

    .run-button {
        background: $success;
    }

    .close-button {
        background: $error;
    }

    .section-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .status-pending {
        color: $text-muted;
    }

    .status-running {
        color: $warning;
    }

    .status-pass {
        color: $success;
    }

    .status-fail {
        color: $error;
    }

    Tree {
        height: 1fr;
        border: solid $primary;
    }
    """

    def __init__(self, config_manager: ConfigManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_manager = config_manager
        self.validator = ConnectivityValidator(config_manager)
        self.is_running = False
        self.results: Dict[str, Tuple[bool, str]] = {}

    def compose(self) -> ComposeResult:
        """Create validation screen widgets"""
        yield Static(
            'Configuration Validation',
            id='validation-header',
            markup=False,
        )

        # Status summary
        with Container(id='validation-status'):
            yield Static('Validation Status', classes='section-title', markup=False)
            yield Static('Ready to run validation checks', id='status-text', markup=False)

        # Results tree
        with Container(id='validation-results'):
            yield Static('Validation Checks', classes='section-title', markup=False)
            yield self.create_results_tree()

        # Action buttons
        with Container(id='validation-actions'):
            with Horizontal():
                yield Button('Run All Checks', variant='success', classes='action-button run-button', id='btn-run')
                yield Button('Close', variant='error', classes='action-button close-button', id='btn-close')

    def create_results_tree(self) -> Tree:
        """Create tree widget for displaying validation results"""
        tree = Tree('Validation Checks', id='results-tree')
        tree.root.expand()

        # Configuration checks
        config_node = tree.root.add('Configuration', expand=True)
        config_node.add_leaf('Required fields present')
        config_node.add_leaf('Valid field values')
        config_node.add_leaf('Contextual requirements met')

        # Connectivity checks
        connectivity_node = tree.root.add('Connectivity', expand=True)
        self.db_node = connectivity_node.add_leaf('⏳ Database connection')
        self.s3_node = connectivity_node.add_leaf('⏳ S3 bucket access')
        self.crc_node = connectivity_node.add_leaf('⏳ CRC authentication')

        # Filesystem checks
        fs_node = tree.root.add('Filesystem', expand=True)
        self.fs_node = fs_node.add_leaf('⏳ Ship path writable')

        return tree

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events"""
        if event.button.id == 'btn-run':
            if not self.is_running:
                asyncio.create_task(self.run_validation())
        elif event.button.id == 'btn-close':
            self.app.pop_screen()

    async def run_validation(self):
        """Run all validation checks"""
        self.is_running = True
        self.query_one('#btn-run', Button).disabled = True

        status = self.query_one('#status-text', Static)
        status.update('Running validation checks...')
        status.add_class('status-running')

        # Update UI to show running status
        self.db_node.label = '⏳ Database connection (running...)'
        self.s3_node.label = '⏳ S3 bucket access (running...)'
        self.crc_node.label = '⏳ CRC authentication (running...)'
        self.fs_node.label = '⏳ Ship path writable (running...)'
        self.refresh()

        try:
            # Run all checks
            results = await self.validator.validate_all()
            self.results = results

            # Update tree with results
            db_success, db_msg = results.get('database', (False, 'Not run'))
            s3_success, s3_msg = results.get('s3', (False, 'Not run'))
            crc_success, crc_msg = results.get('crc', (False, 'Not run'))
            fs_success, fs_msg = results.get('filesystem', (False, 'Not run'))

            self.db_node.label = f'{"✓" if db_success else "✗"} Database: {db_msg}'
            self.s3_node.label = f'{"✓" if s3_success else "✗"} S3: {s3_msg}'
            self.crc_node.label = f'{"✓" if crc_success else "✗"} CRC: {crc_msg}'
            self.fs_node.label = f'{"✓" if fs_success else "✗"} Filesystem: {fs_msg}'

            # Update status summary
            total_checks = len(results)
            passed_checks = sum(1 for success, _ in results.values() if success)

            status.remove_class('status-running')
            if passed_checks == total_checks:
                status.update(f'All checks passed ({passed_checks}/{total_checks})')
                status.add_class('status-pass')
                self.app.notify('All validation checks passed', severity='information')
            else:
                failed = total_checks - passed_checks
                status.update(f'Validation complete: {passed_checks} passed, {failed} failed')
                status.add_class('status-fail')
                self.app.notify(f'{failed} validation check(s) failed', severity='warning')

        except Exception as e:
            status.remove_class('status-running')
            status.update(f'Validation error: {str(e)}')
            status.add_class('status-fail')
            self.app.notify(f'Validation failed: {str(e)}', severity='error')

        finally:
            self.is_running = False
            self.query_one('#btn-run', Button).disabled = False
