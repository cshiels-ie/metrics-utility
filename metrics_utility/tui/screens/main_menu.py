"""
Main menu/dashboard screen for TUI.

Provides overview and quick actions.
"""

from textual.app import ComposeResult
from textual.containers import Container, Grid, Vertical
from textual.screen import Screen
from textual.widgets import Static

from ..config.manager import ConfigManager


class MainMenuScreen(Screen):
    """Main menu/dashboard screen"""

    CSS = """
    MainMenuScreen {
        background: $surface;
    }

    #welcome {
        background: $panel;
        color: white;
        height: 5;
        padding: 1 2;
        text-align: center;
        content-align: center middle;
    }

    #config-summary {
        background: $panel;
        color: $panel;
        border: thick $panel;
        margin: 1 2;
        padding: 1 2;
        height: auto;
    }

    .summary-title {
        text-style: bold;
        color: white;
        margin-bottom: 1;
    }

    .summary-item {
        margin: 0 2;
    }

    .summary-label {
        text-style: bold;
        color: white;
    }

    #quick-actions {
        margin: 1 2;
        color: white;
    }

    .action-grid {
        grid-size: 2 3;
        grid-gutter: 1 2;
        padding: 1;
        color: white;
    }

    .action-card {
        background: $panel;
        border: solid black;
        padding: 2;
        height: 8;
    }

    .action-card:hover {
        background: $accent;
        border: solid $secondary;
    }

    .action-title {
        text-style: bold;
        color: $text;
        text-align: center;
        margin-bottom: 1;
        width: 100%;
        height: auto;
    }

    .action-description {
        color: $text;
        text-align: center;
        width: 100%;
        height: auto;
    }

    #help-text {
        background: $panel;
        color: white;
        margin: 1 2;
        padding: 1 2;
        height: auto;
    }

    .help-title {
        text-style: bold;
        color: white;
    }
    """

    def __init__(self, config_manager: ConfigManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_manager = config_manager

    def compose(self) -> ComposeResult:
        """Create main menu widgets"""
        yield Static(
            'Welcome to Metrics Utility',
            id='welcome',
            markup=False,
        )

        # Configuration summary
        with Container(id='config-summary'):
            yield Static(
                'Current Configuration',
                classes='summary-title',
                markup=False,
            )
            yield self.get_config_summary()

        # Quick actions
        with Container(id='quick-actions'):
            yield Static('Quick Actions', classes='summary-title', markup=False)

            with Grid(classes='action-grid'):
                yield ActionCard(
                    'Edit Configuration',
                    'Modify settings for data collection and reports',
                    'config',
                )
                yield ActionCard(
                    'Gather Data',
                    'Collect billing data from Controller',
                    'gather',
                )
                yield ActionCard(
                    'Build Report',
                    'Generate CSV reports from collected data',
                    'build',
                )
                yield ActionCard(
                    'Validate Configuration',
                    'Check configuration and connectivity',
                    'validate',
                )
                yield ActionCard(
                    'Manage Profiles',
                    'Create, switch, and manage profiles',
                    'profiles',
                )
                yield ActionCard(
                    'Help & Documentation',
                    'View help and documentation',
                    'help',
                )

        # Help text
        with Container(id='help-text'):
            yield Static('Keyboard Shortcuts', classes='help-title', markup=False)
            yield Static(
                '  [C] - Edit Configuration  |  [S] - Save Config  |  [M] - Main Menu  |  [Q] - Quit',
                markup=False,
            )

    def get_config_summary(self) -> Static:
        """Generate configuration summary widget"""
        ship_target = self.config_manager.get('SHIP_TARGET', 'not set')
        ship_path = self.config_manager.get('SHIP_PATH', 'not set')
        report_type = self.config_manager.get('REPORT_TYPE', 'not set')
        profile = self.config_manager.profile

        summary_text = f'Profile: {profile}\nShip Target: {ship_target}\nShip Path: {ship_path}\nReport Type: {report_type}'

        return Static(summary_text, markup=False)


class ActionCard(Vertical):
    """Quick action card"""

    def __init__(self, title: str, description: str, action: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.description = description
        self.action = action
        self.add_class('action-card')

    def compose(self) -> ComposeResult:
        """Create card content"""
        yield Static(self.title, classes='action-title', markup=False)
        yield Static(self.description, classes='action-description', markup=False)

    def on_click(self) -> None:
        """Handle click event"""
        # Import here to avoid circular imports
        from .build_screen import BuildScreen
        from .config_editor import ConfigEditorScreen
        from .gather_screen import GatherScreen
        from .help_screen import HelpScreen
        from .validation_screen import ValidationScreen

        if self.action == 'config':
            self.app.push_screen(ConfigEditorScreen(self.app.config_manager))
        elif self.action == 'gather':
            self.app.push_screen(GatherScreen(self.app.config_manager))
        elif self.action == 'build':
            self.app.push_screen(BuildScreen(self.app.config_manager))
        elif self.action == 'validate':
            self.app.push_screen(ValidationScreen(self.app.config_manager))
        elif self.action == 'profiles':
            self.app.notify('Profiles screen not yet implemented', severity='warning')
        elif self.action == 'help':
            self.app.push_screen(HelpScreen())
