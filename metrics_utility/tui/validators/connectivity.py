"""
Connectivity validators for external services.

Provides pre-flight checks for database, S3, and CRC connectivity.
"""

import asyncio
import os

from pathlib import Path
from typing import Dict, Tuple


class ConnectivityValidator:
    """Validates connectivity to external services"""

    def __init__(self, config_manager):
        """
        Initialize validator with configuration.

        Args:
            config_manager: ConfigManager instance for getting configuration
        """
        self.config_manager = config_manager

    async def validate_database(self) -> Tuple[bool, str]:
        """
        Validate database connectivity.

        Returns:
            Tuple of (success, message)
        """
        try:
            # Import here to avoid dependency issues
            import psycopg

            # Get database config from environment (Django manages this)
            db_name = os.environ.get('POSTGRES_DB', 'postgres')
            db_user = os.environ.get('POSTGRES_USER', 'postgres')
            db_password = os.environ.get('POSTGRES_PASSWORD', '')
            db_host = os.environ.get('POSTGRES_HOST', 'localhost')
            db_port = os.environ.get('POSTGRES_PORT', '5432')

            # Build connection string
            conn_str = f'dbname={db_name} user={db_user} password={db_password} host={db_host} port={db_port}'

            # Try to connect with timeout
            conn = await asyncio.wait_for(
                psycopg.AsyncConnection.connect(conn_str),
                timeout=5.0,
            )

            # Test with a simple query
            async with conn.cursor() as cur:
                await cur.execute('SELECT 1')
                result = await cur.fetchone()

            await conn.close()

            if result and result[0] == 1:
                return True, f'Successfully connected to database at {db_host}:{db_port}'
            else:
                return False, 'Database connection succeeded but test query failed'

        except asyncio.TimeoutError:
            return False, 'Database connection timed out (5s)'
        except ImportError:
            return False, 'psycopg library not installed'
        except Exception as e:
            return False, f'Database connection failed: {str(e)}'

    async def validate_s3(self) -> Tuple[bool, str]:
        """
        Validate S3 connectivity.

        Returns:
            Tuple of (success, message)
        """
        # Check if S3 is configured
        ship_target = self.config_manager.get('SHIP_TARGET')
        if ship_target != 's3':
            return True, 'S3 not configured (ship_target is not s3)'

        try:
            # Import here to avoid dependency issues
            import boto3

            from botocore.exceptions import ClientError

            # Get S3 config
            bucket_name = self.config_manager.get('BUCKET_NAME')
            bucket_endpoint = self.config_manager.get('BUCKET_ENDPOINT_URL')
            access_key = self.config_manager.get('BUCKET_ACCESS_KEY_ID')
            secret_key = self.config_manager.get('BUCKET_SECRET_ACCESS_KEY')
            region = self.config_manager.get('BUCKET_REGION')

            if not bucket_name:
                return False, 'BUCKET_NAME not configured'

            # Create S3 client
            session = boto3.session.Session()
            s3_client = session.client(
                's3',
                endpoint_url=bucket_endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
            )

            # Test bucket access with timeout
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(s3_client.head_bucket, Bucket=bucket_name),
                    timeout=5.0,
                )
                return True, f'Successfully accessed S3 bucket: {bucket_name}'
            except asyncio.TimeoutError:
                return False, 'S3 connection timed out (5s)'

        except ImportError:
            return False, 'boto3 library not installed'
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == '404':
                return False, f'Bucket not found: {bucket_name}'
            elif error_code == '403':
                return False, f'Access denied to bucket: {bucket_name}'
            else:
                return False, f'S3 error ({error_code}): {str(e)}'
        except Exception as e:
            return False, f'S3 connection failed: {str(e)}'

    async def validate_crc(self) -> Tuple[bool, str]:
        """
        Validate CRC (Console Red Hat Cloud) connectivity.

        Returns:
            Tuple of (success, message)
        """
        # Check if CRC is configured
        ship_target = self.config_manager.get('SHIP_TARGET')
        if ship_target != 'crc':
            return True, 'CRC not configured (ship_target is not crc)'

        try:
            # Import here to avoid dependency issues
            import requests

            # Get CRC config
            self.config_manager.get('CRC_INGRESS_URL')
            sso_url = self.config_manager.get('CRC_SSO_URL')
            service_account_id = self.config_manager.get('SERVICE_ACCOUNT_ID')
            service_account_secret = self.config_manager.get('SERVICE_ACCOUNT_SECRET')

            if not sso_url:
                return False, 'CRC_SSO_URL not configured'

            if not service_account_id or not service_account_secret:
                return False, 'Service account credentials not configured'

            # Test SSO endpoint with timeout
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        requests.get,
                        sso_url,
                        timeout=5,
                    ),
                    timeout=6.0,
                )

                if response.status_code == 200:
                    return True, f'Successfully connected to CRC SSO: {sso_url}'
                else:
                    return False, f'CRC SSO returned status {response.status_code}'

            except asyncio.TimeoutError:
                return False, 'CRC connection timed out (5s)'

        except ImportError:
            return False, 'requests library not installed'
        except Exception as e:
            return False, f'CRC connection failed: {str(e)}'

    async def validate_filesystem(self) -> Tuple[bool, str]:
        """
        Validate filesystem access for ship_path.

        Returns:
            Tuple of (success, message)
        """
        # Check if directory shipping is configured
        ship_target = self.config_manager.get('SHIP_TARGET')
        if ship_target not in ['directory', 'local']:
            return True, 'Filesystem shipping not configured'

        try:
            ship_path = self.config_manager.get('SHIP_PATH')
            if not ship_path:
                return False, 'SHIP_PATH not configured'

            path = Path(ship_path)

            # Check if path exists or can be created
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    created = True
                except PermissionError:
                    return False, f'Cannot create directory (permission denied): {ship_path}'
                except Exception as e:
                    return False, f'Cannot create directory: {str(e)}'
            else:
                created = False

            # Check write permissions
            if not os.access(path, os.W_OK):
                return False, f'No write permission for: {ship_path}'

            # Try to create a test file
            test_file = path / '.tui_test'
            try:
                test_file.write_text('test')
                test_file.unlink()
                msg = f'Successfully validated write access to: {ship_path}'
                if created:
                    msg += ' (directory created)'
                return True, msg
            except Exception as e:
                return False, f'Cannot write to directory: {str(e)}'

        except Exception as e:
            return False, f'Filesystem validation failed: {str(e)}'

    async def validate_all(self) -> Dict[str, Tuple[bool, str]]:
        """
        Run all validation checks concurrently.

        Returns:
            Dictionary mapping check name to (success, message) tuple
        """
        results = await asyncio.gather(
            self.validate_database(),
            self.validate_s3(),
            self.validate_crc(),
            self.validate_filesystem(),
            return_exceptions=True,
        )

        checks = ['database', 's3', 'crc', 'filesystem']
        validation_results = {}

        for check, result in zip(checks, results):
            if isinstance(result, Exception):
                validation_results[check] = (False, f'Validation error: {str(result)}')
            else:
                validation_results[check] = result

        return validation_results
