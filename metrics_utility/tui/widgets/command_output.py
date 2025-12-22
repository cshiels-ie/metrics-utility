"""
Command output display widget.

Shows real-time output from running commands with color-coded log levels.
"""

from textual.widgets import RichLog


class CommandOutput(RichLog):
    """Widget for displaying command output with syntax highlighting"""

    CSS = """
    CommandOutput {
        border: solid $primary;
        height: 1fr;
        margin: 1 0;
    }
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('highlight', True)
        kwargs.setdefault('markup', True)
        kwargs.setdefault('wrap', True)
        super().__init__(*args, **kwargs)
        self.max_lines = 1000

    def append_output(self, line: str):
        """
        Append output line with color coding.

        Args:
            line: Output line to append
        """
        # Color code based on log level
        line_lower = line.lower()

        if 'error' in line_lower or 'exception' in line_lower or 'traceback' in line_lower:
            styled_line = f'[bold red]{line}[/bold red]'
        elif 'warning' in line_lower or 'warn' in line_lower:
            styled_line = f'[bold yellow]{line}[/bold yellow]'
        elif 'success' in line_lower or 'complete' in line_lower or 'finished' in line_lower:
            styled_line = f'[bold green]{line}[/bold green]'
        elif 'info' in line_lower:
            styled_line = f'[cyan]{line}[/cyan]'
        elif 'debug' in line_lower:
            styled_line = f'[dim]{line}[/dim]'
        else:
            styled_line = line

        self.write(styled_line)

    def append_error(self, line: str):
        """
        Append error line.

        Args:
            line: Error line to append
        """
        self.write(f'[bold red]ERROR: {line}[/bold red]')

    def clear_output(self):
        """Clear all output"""
        self.clear()
