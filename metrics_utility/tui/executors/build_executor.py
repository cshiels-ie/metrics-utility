"""
Executor for build_report command.
"""

from pathlib import Path

from .base import CommandExecutor


class BuildExecutor(CommandExecutor):
    """Executor for build_report command"""

    def build_command(
        self,
        month: str = None,
        since: str = None,
        until: str = None,
        ephemeral: str = None,
        force: bool = False,
    ) -> list:
        """
        Build report command.

        Args:
            month: Month to build report for (YYYY-MM)
            since: Start date (YYYY-MM-DD)
            until: End date (YYYY-MM-DD)
            ephemeral: Ephemeral data path
            force: Force rebuild

        Returns:
            Command arguments list
        """
        # Find manage.py in project root
        project_root = Path(__file__).parents[3]
        manage_py = project_root / 'manage.py'

        command = ['python', str(manage_py), 'build_report']

        if month:
            command.extend(['--month', month])

        if since:
            command.extend(['--since', since])

        if until:
            command.extend(['--until', until])

        if ephemeral:
            command.extend(['--ephemeral', ephemeral])

        if force:
            command.append('--force')

        return command
