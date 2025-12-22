"""
Main TUI application for metrics-utility.

Provides full-screen interactive interface with navigation and multiple screens.
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from .config.manager import ConfigManager
from .screens.config_editor import ConfigEditorScreen
from .screens.main_menu import MainMenuScreen


class MetricsUtilityTUI(App):
    """Main TUI application for metrics-utility"""

    CSS = """
    * {
        color: auto;
    }

    Static {
        color: auto;
    }

    Label {
        color: auto;
    }

    Input {
        color: auto;
    }

    Button {
        color: auto;
    }
    """

    BINDINGS = [
        Binding('q', 'quit', 'Quit', priority=True),
        Binding('c', 'show_config', 'Config'),
        Binding('m', 'show_menu', 'Menu'),
        Binding('s', 'save_config', 'Save'),
        Binding('escape', 'app.pop_screen', 'Back'),
    ]

    def __init__(self, profile: str = 'default', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = profile
        self.config_manager = None

    def on_mount(self) -> None:
        """Called when app is mounted"""
        self.title = 'metrics-utility TUI'
        self.sub_title = f'Profile: {self.profile}'

        # Initialize config manager
        self.config_manager = ConfigManager(profile=self.profile)

        # Push main menu screen
        self.push_screen(MainMenuScreen(self.config_manager))

    def compose(self) -> ComposeResult:
        """Create base widgets"""
        yield Header()
        yield Footer()

    def action_show_config(self) -> None:
        """Show configuration screen"""
        self.push_screen(ConfigEditorScreen(self.config_manager))

    def action_show_menu(self) -> None:
        """Show main menu"""
        # Pop all screens and show main menu
        while len(self.screen_stack) > 1:
            self.pop_screen()

    def action_save_config(self) -> None:
        """Save current configuration"""
        if self.config_manager:
            try:
                self.config_manager.save_config()
                self.notify('Configuration saved successfully', severity='information')
            except Exception as e:
                self.notify(f'Error saving configuration: {e}', severity='error')
