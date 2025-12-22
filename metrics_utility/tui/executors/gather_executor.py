"""
Executor for gather_automation_controller_billing_data command.
"""

from pathlib import Path

from .base import CommandExecutor


class GatherExecutor(CommandExecutor):
    """Executor for gather command"""

    def build_command(
        self,
        since: str = None,
        until: str = None,
        ship: bool = False,
        dry_run: bool = False,
    ) -> list:
        """
        Build gather command.

        Args:
            since: Start date (YYYY-MM-DD)
            until: End date (YYYY-MM-DD)
            ship: Whether to ship data
            dry_run: Dry run mode

        Returns:
            Command arguments list
        """
        # Find manage.py in project root
        project_root = Path(__file__).parents[3]
        manage_py = project_root / 'manage.py'

        command = ['python', str(manage_py), 'gather_automation_controller_billing_data']

        if since:
            command.extend(['--since', since])

        if until:
            command.extend(['--until', until])

        if ship:
            command.append('--ship')

        if dry_run:
            command.append('--dry-run')

        return command
