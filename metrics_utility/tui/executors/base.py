"""
Base command executor for running Django management commands.

Provides subprocess execution with real-time output capture.
"""

import asyncio
import os

from typing import Callable, Optional

from ..config.schema import get_field_by_key


class CommandExecutor:
    """Base class for executing Django management commands via subprocess"""

    def __init__(self, config_manager):
        """
        Initialize executor with configuration.

        Args:
            config_manager: ConfigManager instance for getting configuration
        """
        self.config_manager = config_manager
        self.process = None
        self.return_code = None

    def build_command(self, *args, **kwargs) -> list:
        """
        Build command arguments list.

        Must be implemented by subclasses.

        Returns:
            List of command arguments
        """
        raise NotImplementedError('Subclasses must implement build_command')

    def get_env(self) -> dict:
        """
        Get environment variables for command execution.

        Merges current environment with configuration values.

        Returns:
            Dictionary of environment variables
        """
        env = os.environ.copy()

        # Add all config values as environment variables
        config = self.config_manager.get_all()
        for key, value in config.items():
            if value is not None:
                # Get the proper environment variable name from schema
                field = get_field_by_key(key)
                if field:
                    env_var_name = field.env_var_name

                    # Convert to string for environment
                    if isinstance(value, bool):
                        env[env_var_name] = 'true' if value else 'false'
                    elif isinstance(value, list):
                        env[env_var_name] = ','.join(str(v) for v in value)
                    else:
                        env[env_var_name] = str(value)

        return env

    async def execute(
        self,
        command: list,
        output_callback: Optional[Callable[[str], None]] = None,
        error_callback: Optional[Callable[[str], None]] = None,
    ) -> int:
        """
        Execute command asynchronously with real-time output.

        Args:
            command: Command arguments list
            output_callback: Called with each line of stdout
            error_callback: Called with each line of stderr

        Returns:
            Return code of the process
        """
        env = self.get_env()

        # Create subprocess
        self.process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        # Read stdout and stderr concurrently
        async def read_stream(stream, callback):
            while True:
                line = await stream.readline()
                if not line:
                    break
                line_str = line.decode('utf-8').rstrip()
                if callback:
                    callback(line_str)

        # Start reading both streams
        await asyncio.gather(
            read_stream(self.process.stdout, output_callback),
            read_stream(self.process.stderr, error_callback),
        )

        # Wait for process to complete
        self.return_code = await self.process.wait()
        return self.return_code

    async def cancel(self):
        """Cancel running command"""
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()

    def is_running(self) -> bool:
        """Check if command is currently running"""
        return self.process is not None and self.process.returncode is None
