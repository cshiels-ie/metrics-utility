"""
Configuration manager for metrics-utility TUI.

Handles loading/saving configuration from YAML files, merging with environment
variables, and managing multiple profiles.

Precedence order: ENV VARS > CONFIG FILE > DEFAULTS
"""

import os

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .schema import CONFIG_SCHEMA, FieldType, get_field_by_key


class ConfigManager:
    """Manages configuration for metrics-utility TUI"""

    DEFAULT_CONFIG_DIR = Path.home() / '.metrics-utility'
    DEFAULT_CONFIG_FILE = 'config.yaml'

    def __init__(self, config_path: Optional[Path] = None, profile: str = 'default'):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to config file (default: ~/.metrics-utility/config.yaml)
            profile: Profile name to use (default: 'default')
        """
        self.config_path = config_path or (self.DEFAULT_CONFIG_DIR / self.DEFAULT_CONFIG_FILE)
        self.profile = profile
        self._config_data = {}
        self._load_config()

    def _ensure_config_dir(self):
        """Ensure config directory exists"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_config(self):
        """Load configuration from file"""
        if not self.config_path.exists():
            self._config_data = {'profiles': {self.profile: {}}}
            return

        try:
            with open(self.config_path, 'r') as f:
                self._config_data = yaml.safe_load(f) or {}

            # Ensure profiles key exists
            if 'profiles' not in self._config_data:
                self._config_data['profiles'] = {}

            # Ensure current profile exists
            if self.profile not in self._config_data['profiles']:
                self._config_data['profiles'][self.profile] = {}

        except Exception as e:
            raise RuntimeError(f'Failed to load config from {self.config_path}: {e}')

    def save_config(self):
        """Save current configuration to file"""
        self._ensure_config_dir()

        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self._config_data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise RuntimeError(f'Failed to save config to {self.config_path}: {e}')

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with precedence: ENV VAR > CONFIG FILE > DEFAULT.

        Args:
            key: Field key (e.g., 'SHIP_TARGET')
            default: Default value if not found

        Returns:
            Configuration value
        """
        field = get_field_by_key(key)
        if not field:
            return default

        # 1. Check environment variable (highest precedence)
        env_value = os.getenv(field.env_var_name)
        if env_value is not None:
            return self._parse_value(env_value, field.field_type)

        # 2. Check config file
        profile_data = self._config_data.get('profiles', {}).get(self.profile, {})
        if key in profile_data:
            return profile_data[key]

        # 3. Return default from schema or provided default
        return field.default if default is None else default

    def set(self, key: str, value: Any):
        """
        Set configuration value in the config file.

        Args:
            key: Field key (e.g., 'SHIP_TARGET')
            value: Value to set
        """
        if 'profiles' not in self._config_data:
            self._config_data['profiles'] = {}

        if self.profile not in self._config_data['profiles']:
            self._config_data['profiles'][self.profile] = {}

        self._config_data['profiles'][self.profile][key] = value

    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values for current profile.

        Returns:
            Dictionary of all config values (merged from env vars, file, and defaults)
        """
        config = {}
        for field in CONFIG_SCHEMA:
            config[field.key] = self.get(field.key)
        return config

    def set_all(self, config: Dict[str, Any]):
        """
        Set multiple configuration values.

        Args:
            config: Dictionary of key-value pairs
        """
        for key, value in config.items():
            if value is not None:  # Don't set None values
                self.set(key, value)

    def _parse_value(self, value: str, field_type: FieldType) -> Any:
        """Parse string value based on field type"""
        if field_type == FieldType.BOOLEAN:
            return value.lower() in ('true', '1', 'yes', 'on')
        elif field_type == FieldType.INTEGER:
            try:
                return int(value)
            except ValueError:
                return None
        elif field_type == FieldType.FLOAT:
            try:
                return float(value)
            except ValueError:
                return None
        elif field_type == FieldType.MULTISELECT:
            # Parse comma-separated values
            if isinstance(value, str):
                return [v.strip() for v in value.split(',') if v.strip()]
            return value
        else:
            # STRING, SELECT, PASSWORD - return as-is
            return value

    def list_profiles(self) -> list[str]:
        """List all available profiles"""
        return list(self._config_data.get('profiles', {}).keys())

    def create_profile(self, name: str, copy_from: Optional[str] = None):
        """
        Create a new profile.

        Args:
            name: Profile name
            copy_from: Optional profile name to copy settings from
        """
        if 'profiles' not in self._config_data:
            self._config_data['profiles'] = {}

        if name in self._config_data['profiles']:
            raise ValueError(f'Profile "{name}" already exists')

        if copy_from:
            if copy_from not in self._config_data['profiles']:
                raise ValueError(f'Source profile "{copy_from}" does not exist')
            self._config_data['profiles'][name] = self._config_data['profiles'][copy_from].copy()
        else:
            self._config_data['profiles'][name] = {}

    def delete_profile(self, name: str):
        """
        Delete a profile.

        Args:
            name: Profile name

        Raises:
            ValueError: If trying to delete the last profile
        """
        if name not in self._config_data.get('profiles', {}):
            raise ValueError(f'Profile "{name}" does not exist')

        if len(self._config_data['profiles']) == 1:
            raise ValueError('Cannot delete the last profile')

        del self._config_data['profiles'][name]

        # If we deleted the active profile, switch to another
        if name == self.profile:
            self.profile = list(self._config_data['profiles'].keys())[0]

    def switch_profile(self, name: str):
        """
        Switch to a different profile.

        Args:
            name: Profile name
        """
        if name not in self._config_data.get('profiles', {}):
            raise ValueError(f'Profile "{name}" does not exist')

        self.profile = name

    def export_as_yaml(self, output_path: Path):
        """
        Export current profile configuration as YAML.

        Args:
            output_path: Path to output file
        """
        profile_data = self._config_data.get('profiles', {}).get(self.profile, {})

        with open(output_path, 'w') as f:
            yaml.dump(profile_data, f, default_flow_style=False, sort_keys=False)

    def export_as_shell_script(self, output_path: Path):
        """
        Export current profile configuration as shell script with export statements.

        Args:
            output_path: Path to output file
        """
        profile_data = self._config_data.get('profiles', {}).get(self.profile, {})

        with open(output_path, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write('# metrics-utility configuration\n')
            f.write(f'# Profile: {self.profile}\n')
            f.write('# Generated by metrics-utility TUI\n\n')

            for field in CONFIG_SCHEMA:
                value = profile_data.get(field.key)
                if value is not None:
                    # Handle different types
                    if field.field_type == FieldType.BOOLEAN:
                        value_str = 'true' if value else 'false'
                    elif field.field_type == FieldType.MULTISELECT:
                        if isinstance(value, list):
                            value_str = ','.join(str(v) for v in value)
                        else:
                            value_str = str(value)
                    else:
                        value_str = str(value)

                    # Escape single quotes in value
                    value_str = value_str.replace("'", "'\\''")

                    f.write(f"export {field.env_var_name}='{value_str}'\n")

        # Make script executable
        output_path.chmod(0o755)

    def import_from_yaml(self, input_path: Path):
        """
        Import configuration from YAML file into current profile.

        Args:
            input_path: Path to input file
        """
        with open(input_path, 'r') as f:
            imported_data = yaml.safe_load(f) or {}

        # Merge into current profile
        if 'profiles' not in self._config_data:
            self._config_data['profiles'] = {}

        if self.profile not in self._config_data['profiles']:
            self._config_data['profiles'][self.profile] = {}

        self._config_data['profiles'][self.profile].update(imported_data)

    def import_from_environment(self):
        """
        Import configuration from current environment variables into current profile.
        """
        for field in CONFIG_SCHEMA:
            env_value = os.getenv(field.env_var_name)
            if env_value is not None:
                parsed_value = self._parse_value(env_value, field.field_type)
                self.set(field.key, parsed_value)

    def validate_config(self) -> list[str]:
        """
        Validate current configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        config = self.get_all()

        for field in CONFIG_SCHEMA:
            value = config.get(field.key)

            # Check required fields
            if field.required and not value:
                errors.append(f'{field.display_name} is required')

            # Check field-specific validators
            if value and field.validator:
                try:
                    if not field.validator(value):
                        errors.append(f'{field.display_name} has invalid value: {value}')
                except Exception as e:
                    errors.append(f'{field.display_name} validation error: {e}')

            # Check select options
            if value and field.field_type == FieldType.SELECT:
                if field.options and value not in field.options:
                    errors.append(f'{field.display_name} must be one of: {", ".join(field.options)}')

            # Check multiselect options
            if value and field.field_type == FieldType.MULTISELECT:
                if field.options:
                    if isinstance(value, list):
                        values = value
                    else:
                        values = [v.strip() for v in str(value).split(',') if v.strip()]

                    invalid = set(values) - set(field.options)
                    if invalid:
                        errors.append(f'{field.display_name} contains invalid values: {", ".join(invalid)}')

            # Check conditional dependencies
            if field.depends_on:
                for dep_key, dep_values in field.depends_on.items():
                    dep_value = config.get(dep_key)
                    if dep_value in dep_values and not value:
                        errors.append(f'{field.display_name} is required when {dep_key}={dep_value}')

        return errors

    def get_profile_data(self, profile_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get raw profile data from config file (without env var merging).

        Args:
            profile_name: Profile name (default: current profile)

        Returns:
            Dictionary of profile data
        """
        name = profile_name or self.profile
        return self._config_data.get('profiles', {}).get(name, {}).copy()
