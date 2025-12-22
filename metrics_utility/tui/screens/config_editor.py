"""
Configuration editor screen for TUI.

Provides tabbed interface for editing configuration organized by category.
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Static, TabbedContent, TabPane

from ..config.manager import ConfigManager
from ..config.schema import FieldCategory
from ..widgets.config_form import ConfigForm


class ConfigEditorScreen(Screen):
    """Screen for editing configuration"""

    CSS = """
    ConfigEditorScreen {
        background: $surface;
    }

    #config-header {
        background: $panel;
        height: 3;
        padding: 1 2;
        text-align: center;
    }

    #config-actions {
        background: $panel;
        height: 5;
        padding: 1 2;
        align: center middle;
    }

    .action-button {
        margin: 0 1;
    }

    .save-button {
        background: $success;
    }

    .cancel-button {
        background: $error;
    }

    .validation-error {
        background: $error;
        padding: 1 2;
        margin: 1 0;
    }

    .validation-success {
        background: $success;
        padding: 1 2;
        margin: 1 0;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        padding: 0;
    }
    """

    def __init__(self, config_manager: ConfigManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_manager = config_manager
        self.forms = {}

    def compose(self) -> ComposeResult:
        """Create config editor widgets"""
        yield Static(
            f'Configuration Editor - Profile: {self.config_manager.profile}',
            id='config-header',
            markup=False,
        )

        # Tabbed content for categories
        with TabbedContent():
            # Core Configuration
            with TabPane('Core', id='tab-core'):
                with VerticalScroll():
                    form = ConfigForm(FieldCategory.CORE, self.config_manager)
                    self.forms[FieldCategory.CORE] = form
                    yield form

            # S3 Configuration
            with TabPane('S3', id='tab-s3'):
                with VerticalScroll():
                    form = ConfigForm(FieldCategory.S3, self.config_manager)
                    self.forms[FieldCategory.S3] = form
                    yield form

            # CRC Configuration
            with TabPane('CRC', id='tab-crc'):
                with VerticalScroll():
                    form = ConfigForm(FieldCategory.CRC, self.config_manager)
                    self.forms[FieldCategory.CRC] = form
                    yield form

            # Billing Configuration
            with TabPane('Billing', id='tab-billing'):
                with VerticalScroll():
                    form = ConfigForm(FieldCategory.BILLING, self.config_manager)
                    self.forms[FieldCategory.BILLING] = form
                    yield form

            # Collection Configuration
            with TabPane('Collection', id='tab-collection'):
                with VerticalScroll():
                    form = ConfigForm(FieldCategory.COLLECTION, self.config_manager)
                    self.forms[FieldCategory.COLLECTION] = form
                    yield form

            # Report Configuration
            with TabPane('Report', id='tab-report'):
                with VerticalScroll():
                    form = ConfigForm(FieldCategory.REPORT, self.config_manager)
                    self.forms[FieldCategory.REPORT] = form
                    yield form

            # Prometheus Configuration
            with TabPane('Prometheus', id='tab-prometheus'):
                with VerticalScroll():
                    form = ConfigForm(FieldCategory.PROMETHEUS, self.config_manager)
                    self.forms[FieldCategory.PROMETHEUS] = form
                    yield form

        # Action buttons
        with Container(id='config-actions'):
            with Horizontal():
                yield Button('Save', variant='success', classes='action-button save-button', id='btn-save')
                yield Button('Save & Exit', variant='primary', classes='action-button', id='btn-save-exit')
                yield Button('Reset', variant='warning', classes='action-button', id='btn-reset')
                yield Button('Validate', variant='default', classes='action-button', id='btn-validate')
                yield Button('Cancel', variant='error', classes='action-button cancel-button', id='btn-cancel')

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events"""
        if event.button.id == 'btn-save':
            self.save_config()
        elif event.button.id == 'btn-save-exit':
            self.save_config()
            self.app.pop_screen()
        elif event.button.id == 'btn-reset':
            self.reset_config()
        elif event.button.id == 'btn-validate':
            self.validate_config()
        elif event.button.id == 'btn-cancel':
            self.app.pop_screen()

    def save_config(self) -> None:
        """Save all form values to config manager"""
        try:
            # Collect all values from forms
            all_values = {}
            for form in self.forms.values():
                all_values.update(form.get_values())

            # Set in config manager
            self.config_manager.set_all(all_values)

            # Save to file
            self.config_manager.save_config()

            self.app.notify('Configuration saved successfully', severity='information')

        except Exception as e:
            self.app.notify(f'Error saving configuration: {e}', severity='error')

    def reset_config(self) -> None:
        """Reset form to current config values"""
        current_config = self.config_manager.get_all()
        for form in self.forms.values():
            form.set_values(current_config)

        self.app.notify('Configuration reset to saved values', severity='information')

    def validate_config(self) -> None:
        """Validate all forms"""
        all_errors = []

        # Collect values and validate each form
        for category, form in self.forms.items():
            errors = form.validate()
            if errors:
                all_errors.extend([f'[{category.value}] {err}' for err in errors])

        if all_errors:
            error_msg = 'Validation errors:\n' + '\n'.join(all_errors)
            self.app.notify(error_msg, severity='error', timeout=10)
        else:
            self.app.notify('Configuration is valid', severity='information')
