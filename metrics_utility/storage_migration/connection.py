import os
import subprocess

import psycopg

from django.conf import settings

from metrics_utility.exceptions import MetricsException, MissingRequiredEnvVar
from metrics_utility.logger import logger


def build_pg_connection_string(host, port, name, user, password):
    """Build PostgreSQL connection string for pg_dump/pg_restore/psql"""
    if password:
        # Include password in connection string
        return f'postgresql://{user}:{password}@{host}:{port}/{name}'
    else:
        # No password - for tools that will prompt or use .pgpass
        return f'postgresql://{user}@{host}:{port}/{name}'


def get_controller_db_params():
    """
    Extract controller DB params from Django settings or env vars.

    Returns dict with keys: host, port, name, user, password
    """
    db_config = settings.DATABASES.get('default', {})

    return {
        'host': os.getenv('METRICS_UTILITY_DB_HOST', db_config.get('HOST', 'localhost')),
        'port': os.getenv('METRICS_UTILITY_DB_PORT', db_config.get('PORT', '5432')),
        'name': os.getenv('METRICS_UTILITY_DB_NAME', db_config.get('NAME', 'awx')),
        'user': os.getenv('METRICS_UTILITY_DB_USER', db_config.get('USER', '')),
        'password': os.getenv('METRICS_UTILITY_DB_PASSWORD', db_config.get('PASSWORD', '')),
    }


def get_storage_db_params():
    """
    Extract storage DB params from env vars.

    Returns dict with keys: host, port, name, user, password, schema
    """
    return {
        'host': os.getenv('METRICS_UTILITY_STORAGE_DB_HOST'),
        'port': os.getenv('METRICS_UTILITY_STORAGE_DB_PORT', '5432'),
        'name': os.getenv('METRICS_UTILITY_STORAGE_DB_NAME'),
        'user': os.getenv('METRICS_UTILITY_STORAGE_DB_USER'),
        'password': os.getenv('METRICS_UTILITY_STORAGE_DB_PASSWORD'),
        'schema': os.getenv('METRICS_UTILITY_STORAGE_DB_SCHEMA', 'public'),
    }


def validate_storage_db_params(params):
    """
    Validate that required storage DB parameters are present.

    Raises MissingRequiredEnvVar if any required param is missing.
    """
    required = ['host', 'name', 'user', 'password']
    missing = []

    for key in required:
        if not params.get(key):
            env_var_name = f'METRICS_UTILITY_STORAGE_DB_{key.upper()}'
            missing.append(env_var_name)

    if missing:
        raise MissingRequiredEnvVar(f'Missing required storage database environment variables: {", ".join(missing)}')


def validate_connections(source_params, dest_params):
    """
    Validate both database connections before migration.

    Tests connections using psql command.
    Raises MetricsException if either connection fails.
    """
    errors = []

    # Test source connection
    logger.info('Validating source database connection...')
    try:
        source_conn_str = build_pg_connection_string(**source_params)
        result = subprocess.run(['psql', source_conn_str, '-c', 'SELECT 1'], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            errors.append(f'Source database connection failed: {result.stderr}')
        else:
            logger.info(f'Source database connection successful ({source_params["host"]}:{source_params["port"]}/{source_params["name"]})')
    except subprocess.TimeoutExpired:
        errors.append('Source database connection timeout')
    except Exception as e:
        errors.append(f'Source database connection error: {str(e)}')

    # Test destination connection
    logger.info('Validating destination database connection...')
    try:
        dest_conn_str = build_pg_connection_string(**dest_params)
        result = subprocess.run(['psql', dest_conn_str, '-c', 'SELECT 1'], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            errors.append(f'Destination database connection failed: {result.stderr}')
        else:
            logger.info(f'Destination database connection successful ({dest_params["host"]}:{dest_params["port"]}/{dest_params["name"]})')
    except subprocess.TimeoutExpired:
        errors.append('Destination database connection timeout')
    except Exception as e:
        errors.append(f'Destination database connection error: {str(e)}')

    if errors:
        raise MetricsException('\n'.join(errors))


def check_pg_tools():
    """
    Verify PostgreSQL client tools are installed.

    Raises MetricsException if any required tool is missing.
    """
    required_tools = ['pg_dump', 'pg_restore', 'psql']
    missing = []

    for tool in required_tools:
        result = subprocess.run(['which', tool], capture_output=True, text=True)
        if result.returncode != 0:
            missing.append(tool)

    if missing:
        raise MetricsException(f'Required PostgreSQL tools not found: {", ".join(missing)}\nPlease install PostgreSQL client tools.')

    logger.info('PostgreSQL client tools verified')


def get_psycopg_connection(params):
    """
    Create a psycopg connection from database parameters.

    Returns psycopg.Connection
    """
    conn_str = f'host={params["host"]} port={params["port"]} dbname={params["name"]} user={params["user"]}'
    if params.get('password'):
        conn_str += f' password={params["password"]}'

    return psycopg.connect(conn_str)
