"""
Django management command to launch the TUI.

Provides an interactive terminal user interface for configuring and running
metrics-utility commands.
"""

from django.core.management.base import BaseCommand

from metrics_utility.tui.app import MetricsUtilityTUI


class Command(BaseCommand):
    """
    Launch the interactive TUI for metrics-utility
    """

    help = 'Launch the interactive Terminal User Interface (TUI) for metrics-utility configuration and operation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--profile',
            dest='profile',
            default='default',
            help='Configuration profile to use (default: default)',
        )

    def handle(self, *args, **options):
        profile = options.get('profile', 'default')

        # Launch the TUI
        app = MetricsUtilityTUI(profile=profile)
        app.run()
