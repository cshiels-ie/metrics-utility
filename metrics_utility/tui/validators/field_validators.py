"""
Field-level validators for configuration values.

Provides validation functions for individual configuration fields.
"""

import re

from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class FieldValidators:
    """Collection of field validation functions"""

    @staticmethod
    def validate_url(value: str) -> bool:
        """
        Validate URL format.

        Args:
            value: URL to validate

        Returns:
            True if valid URL format
        """
        if not value:
            return False

        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$',
            re.IGNORECASE,
        )

        return bool(url_pattern.match(value))

    @staticmethod
    def validate_date(value: str) -> bool:
        """
        Validate date format (YYYY-MM-DD).

        Args:
            value: Date string to validate

        Returns:
            True if valid date format
        """
        if not value:
            return False

        try:
            datetime.strptime(value, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_month(value: str) -> bool:
        """
        Validate month format (YYYY-MM).

        Args:
            value: Month string to validate

        Returns:
            True if valid month format
        """
        if not value:
            return False

        try:
            datetime.strptime(value, '%Y-%m')
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_email(value: str) -> bool:
        """
        Validate email format.

        Args:
            value: Email to validate

        Returns:
            True if valid email format
        """
        if not value:
            return False

        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        return bool(email_pattern.match(value))

    @staticmethod
    def validate_path(value: str) -> bool:
        """
        Validate file path format.

        Args:
            value: Path to validate

        Returns:
            True if valid path format
        """
        if not value:
            return False

        try:
            Path(value)
            return True
        except Exception:
            return False

    @staticmethod
    def validate_positive_number(value: Any) -> bool:
        """
        Validate positive number.

        Args:
            value: Number to validate

        Returns:
            True if positive number
        """
        try:
            num = float(value)
            return num >= 0
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_port(value: Any) -> bool:
        """
        Validate port number (1-65535).

        Args:
            value: Port to validate

        Returns:
            True if valid port
        """
        try:
            port = int(value)
            return 1 <= port <= 65535
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_non_empty(value: Any) -> bool:
        """
        Validate non-empty value.

        Args:
            value: Value to validate

        Returns:
            True if non-empty
        """
        if value is None:
            return False

        if isinstance(value, str):
            return bool(value.strip())

        if isinstance(value, (list, dict)):
            return len(value) > 0

        return True

    @staticmethod
    def validate_integer_range(value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None) -> bool:
        """
        Validate integer within range.

        Args:
            value: Integer to validate
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)

        Returns:
            True if valid integer in range
        """
        try:
            num = int(value)

            if min_val is not None and num < min_val:
                return False

            if max_val is not None and num > max_val:
                return False

            return True

        except (ValueError, TypeError):
            return False
