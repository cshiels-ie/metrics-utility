"""
Gather data screen for TUI.

Provides interface for running gather_automation_controller_billing_data command.
"""

import asyncio

from datetime import datetime, timedelta

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Input, Label, Static

from ..config.manager import ConfigManager
from ..executors.gather_executor import GatherExecutor
from ..widgets.command_output import CommandOutput


class GatherScreen(Screen):
    """Screen for gathering billing data"""

    CSS = """
    GatherScreen {
        background: $surface;
    }

    #gather-header {
        background: $panel;
        height: 3;
        padding: 1 2;
        text-align: center;
    }

    #gather-config {
        background: $panel;
        margin: 1 2;
        padding: 1 2;
        height: auto;
    }

    #gather-params {
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

    #gather-actions {
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
        self.executor = GatherExecutor(config_manager)
        self._is_running = False

    def compose(self) -> ComposeResult:
        """Create gather screen widgets"""
        yield Static(
            'Gather Billing Data',
            id='gather-header',
            markup=False,
        )

        # Configuration summary
        with Container(id='gather-config'):
            yield Static('Current Configuration', classes='section-title', markup=False)
            yield self.get_config_summary()

        # Parameters
        with Container(id='gather-params'):
            yield Static('Gather Parameters', classes='section-title', markup=False)

            # Since date
            with Horizontal(classes='param-row'):
                yield Label('Since Date:', classes='param-label')
                default_since = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                yield Input(
                    value=default_since,
                    placeholder='YYYY-MM-DD',
                    classes='param-input',
                    id='input-since',
                )

            # Until date
            with Horizontal(classes='param-row'):
                yield Label('Until Date:', classes='param-label')
                default_until = datetime.now().strftime('%Y-%m-%d')
                yield Input(
                    value=default_until,
                    placeholder='YYYY-MM-DD',
                    classes='param-input',
                    id='input-until',
                )

            # Ship checkbox
            with Horizontal(classes='param-row'):
                yield Label('Ship Data:', classes='param-label')
                yield Checkbox('Ship collected data to target', id='checkbox-ship')

            # Dry run checkbox
            with Horizontal(classes='param-row'):
                yield Label('Dry Run:', classes='param-label')
                yield Checkbox('Dry run mode (no changes)', id='checkbox-dry-run')

        # Action buttons
        with Container(id='gather-actions'):
            with Horizontal():
                yield Button('Start Gather', variant='success', classes='action-button start-button', id='btn-start')
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
        cluster_name = self.config_manager.get('CLUSTER_NAME', 'not set')

        summary_text = f'Ship Target: {ship_target}\nShip Path: {ship_path}\nCluster Name: {cluster_name}'

        return Static(summary_text, markup=False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events"""
        if event.button.id == 'btn-start':
            if not self._is_running:
                asyncio.create_task(self.start_gather())
        elif event.button.id == 'btn-cancel':
            if self._is_running:
                asyncio.create_task(self.cancel_gather())
            else:
                self.app.pop_screen()

    async def start_gather(self):
        """Start gather command"""
        # Get parameters
        since = self.query_one('#input-since', Input).value
        until = self.query_one('#input-until', Input).value
        ship = self.query_one('#checkbox-ship', Checkbox).value
        dry_run = self.query_one('#checkbox-dry-run', Checkbox).value

        # Validate dates
        if not since or not until:
            self.app.notify('Please enter both since and until dates', severity='error')
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
            since=since,
            until=until,
            ship=ship,
            dry_run=dry_run,
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
                self.app.notify('Gather completed successfully', severity='information')
            else:
                status.update(f'Failed (exit code {return_code})')
                status.add_class('status-error')
                self.app.notify(f'Gather failed with exit code {return_code}', severity='error')

        except Exception as e:
            output.append_error(f'Exception: {str(e)}')
            status.remove_class('status-running')
            status.update('Error')
            status.add_class('status-error')
            self.app.notify(f'Gather failed: {str(e)}', severity='error')

        finally:
            self._is_running = False
            self.query_one('#btn-start', Button).disabled = False
            self.query_one('#btn-cancel', Button).label = 'Cancel'

    async def cancel_gather(self):
        """Cancel running gather command"""
        if self.executor.is_running():
            await self.executor.cancel()
            self.app.notify('Gather cancelled', severity='warning')
