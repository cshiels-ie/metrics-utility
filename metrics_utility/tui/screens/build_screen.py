"""
Build report screen for TUI.

Provides interface for running build_report command.
"""

import asyncio

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Input, Label, Static

from ..config.manager import ConfigManager
from ..executors.build_executor import BuildExecutor
from ..widgets.command_output import CommandOutput


class BuildScreen(Screen):
    """Screen for building reports"""

    CSS = """
    BuildScreen {
        background: $surface;
    }

    #build-header {
        background: $panel;
        height: 3;
        padding: 1 2;
        text-align: center;
    }

    #build-config {
        background: $panel;
        margin: 1 2;
        padding: 1 2;
        height: auto;
    }

    #build-params {
        background: $panel;
        margin: 1 2;
        padding: 1 2;
        height: auto;
    }

    .param-row {
        height: auto;
        margin: 1 0;
    }

    .param-label {
        width: 20;
        padding: 0 1;
        text-style: bold;
    }

    .param-input {
        width: 1fr;
    }

    #build-actions {
        background: $panel;
        height: 5;
        padding: 1 2;
        align: center middle;
    }

    .action-button {
        margin: 0 1;
    }

    .start-button {
        background: $success;
    }

    .cancel-button {
        background: $error;
    }

    #output-container {
        margin: 1 2;
        height: 1fr;
    }

    .section-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .status-running {
        background: $warning;
        padding: 0 1;
    }

    .status-success {
        background: $success;
        padding: 0 1;
    }

    .status-error {
        background: $error;
        padding: 0 1;
    }
    """

    def __init__(self, config_manager: ConfigManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_manager = config_manager
        self.executor = BuildExecutor(config_manager)
        self._is_running = False

    def compose(self) -> ComposeResult:
        """Create build screen widgets"""
        yield Static(
            'Build Report',
            id='build-header',
            markup=False,
        )

        # Configuration summary
        with Container(id='build-config'):
            yield Static('Current Configuration', classes='section-title', markup=False)
            yield self.get_config_summary()

        # Parameters
        with Container(id='build-params'):
            yield Static('Build Parameters', classes='section-title', markup=False)

            # Month
            with Horizontal(classes='param-row'):
                yield Label('Month:', classes='param-label')
                default_month = datetime.now().strftime('%Y-%m')
                yield Input(
                    value=default_month,
                    placeholder='YYYY-MM',
                    classes='param-input',
                    id='input-month',
                )

            # Since date
            with Horizontal(classes='param-row'):
                yield Label('Since Date:', classes='param-label')
                yield Input(
                    value='',
                    placeholder='YYYY-MM-DD (optional)',
                    classes='param-input',
                    id='input-since',
                )

            # Until date
            with Horizontal(classes='param-row'):
                yield Label('Until Date:', classes='param-label')
                yield Input(
                    value='',
                    placeholder='YYYY-MM-DD (optional)',
                    classes='param-input',
                    id='input-until',
                )

            # Ephemeral path
            with Horizontal(classes='param-row'):
                yield Label('Ephemeral Path:', classes='param-label')
                yield Input(
                    value='',
                    placeholder='Path to ephemeral data (optional)',
                    classes='param-input',
                    id='input-ephemeral',
                )

            # Force checkbox
            with Horizontal(classes='param-row'):
                yield Label('Force Rebuild:', classes='param-label')
                yield Checkbox('Force rebuild of existing reports', id='checkbox-force')

        # Action buttons
        with Container(id='build-actions'):
            with Horizontal():
                yield Button('Build Report', variant='success', classes='action-button start-button', id='btn-start')
                yield Button('Cancel', variant='error', classes='action-button cancel-button', id='btn-cancel')
                yield Static('Ready', id='status-text', markup=False)

        # Output display
        with Container(id='output-container'):
            yield Static('Command Output', classes='section-title', markup=False)
            yield CommandOutput(id='command-output')

    def get_config_summary(self) -> Static:
        """Generate configuration summary widget"""
        ship_target = self.config_manager.get('SHIP_TARGET', 'not set')
        ship_path = self.config_manager.get('SHIP_PATH', 'not set')
        report_type = self.config_manager.get('REPORT_TYPE', 'not set')

        summary_text = f'Ship Target: {ship_target}\nShip Path: {ship_path}\nReport Type: {report_type}'

        return Static(summary_text, markup=False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events"""
        if event.button.id == 'btn-start':
            if not self._is_running:
                asyncio.create_task(self.start_build())
        elif event.button.id == 'btn-cancel':
            if self._is_running:
                asyncio.create_task(self.cancel_build())
            else:
                self.app.pop_screen()

    async def start_build(self):
        """Start build command"""
        # Get parameters
        month = self.query_one('#input-month', Input).value
        since = self.query_one('#input-since', Input).value or None
        until = self.query_one('#input-until', Input).value or None
        ephemeral = self.query_one('#input-ephemeral', Input).value or None
        force = self.query_one('#checkbox-force', Checkbox).value

        # Validate month
        if not month:
            self.app.notify('Please enter a month', severity='error')
            return

        # Update UI
        self._is_running = True
        self.query_one('#btn-start', Button).disabled = True
        self.query_one('#btn-cancel', Button).label = 'Stop'
        status = self.query_one('#status-text', Static)
        status.update('Running...')
        status.add_class('status-running')

        # Clear output
        output = self.query_one('#command-output', CommandOutput)
        output.clear_output()

        # Build and execute command
        command = self.executor.build_command(
            month=month,
            since=since,
            until=until,
            ephemeral=ephemeral,
            force=force,
        )

        output.append_output(f'Executing: {" ".join(command)}')
        output.append_output('')

        try:
            return_code = await self.executor.execute(
                command,
                output_callback=lambda line: output.append_output(line),
                error_callback=lambda line: output.append_output(line),  # Use append_output for stderr too
            )

            # Update status based on return code
            status.remove_class('status-running')
            if return_code == 0:
                status.update('Completed Successfully')
                status.add_class('status-success')
                self.app.notify('Build completed successfully', severity='information')
            else:
                status.update(f'Failed (exit code {return_code})')
                status.add_class('status-error')
                self.app.notify(f'Build failed with exit code {return_code}', severity='error')

        except Exception as e:
            output.append_error(f'Exception: {str(e)}')
            status.remove_class('status-running')
            status.update('Error')
            status.add_class('status-error')
            self.app.notify(f'Build failed: {str(e)}', severity='error')

        finally:
            self._is_running = False
            self.query_one('#btn-start', Button).disabled = False
            self.query_one('#btn-cancel', Button).label = 'Cancel'

    async def cancel_build(self):
        """Cancel running build command"""
        if self.executor.is_running():
            await self.executor.cancel()
            self.app.notify('Build cancelled', severity='warning')
