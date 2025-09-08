#!/usr/bin/env python3
"""
Test script for the reports collector.

This script allows you to test the reports collector without needing to set up
all the environment variables required by the full CLI command.
"""

import os
import sys
import tempfile

from datetime import datetime, timedelta


# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock Django settings if not already configured
try:
    import django

    from django.conf import settings

    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.postgresql',
                    'NAME': os.getenv('DATABASE_NAME', 'awx'),
                    'USER': os.getenv('DATABASE_USER', 'awx'),
                    'PASSWORD': os.getenv('DATABASE_PASSWORD', 'password'),
                    'HOST': os.getenv('DATABASE_HOST', 'localhost'),
                    'PORT': os.getenv('DATABASE_PORT', '5432'),
                }
            },
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
            ],
        )
    django.setup()
except ImportError:
    print('Django not available - using mock setup')


def test_reports_collector():
    """
    Test the reports collector with minimal setup.
    """
    print('=' * 60)
    print('TESTING REPORTS COLLECTOR')
    print('=' * 60)

    try:
        from metrics_utility.automation_controller_billing import reports_collectors
        from metrics_utility.automation_controller_billing.collector import Collector

        print('✓ Successfully imported collector modules')

        # Set up minimal environment
        temp_dir = tempfile.mkdtemp()
        os.environ['METRICS_UTILITY_SHIP_TARGET'] = 'directory'
        os.environ['METRICS_UTILITY_SHIP_PATH'] = temp_dir

        print(f'✓ Using temporary directory: {temp_dir}')

        # Create time range (last 7 days)
        until = datetime.now()
        since = until - timedelta(days=7)

        print(f'✓ Collection period: {since} to {until}')

        # Create collector
        collector = Collector(
            collection_type=Collector.DRY_RUN,
            collector_module=reports_collectors,
        )

        print('✓ Collector created successfully')

        # List available collectors
        import inspect

        functions = []
        for name, obj in inspect.getmembers(reports_collectors):
            if inspect.isfunction(obj) and hasattr(obj, '__insights_analytics_key__'):
                functions.append(
                    {
                        'name': name,
                        'key': obj.__insights_analytics_key__,
                        'format': obj.__insights_analytics_type__,
                    }
                )

        print(f'✓ Found {len(functions)} collector functions:')
        for func in functions:
            print(f'  • {func["key"]} ({func["format"]})')

        print('\n' + '=' * 60)
        print('RUNNING COLLECTION...')
        print('=' * 60)

        # Run collection
        try:
            tgzfiles = collector.gather(since=since, until=until)

            if tgzfiles:
                print(f'✓ Collection successful! Generated {len(tgzfiles)} file(s)')
                for tgzfile in tgzfiles:
                    print(f'  • {tgzfile}')

                print(f'\n✓ Files saved to: {temp_dir}')
                print('✓ To inspect the JSON files, extract the .tar.gz files')

            else:
                print('⚠ No data collected (this may be expected if database is empty)')

        except Exception as e:
            print(f'✗ Collection failed: {e}')
            import traceback

            traceback.print_exc()

    except ImportError as e:
        print(f'✗ Import error: {e}')
        print('Make sure you have the required dependencies installed')
        print("and that you're in the correct environment")

    except Exception as e:
        print(f'✗ Unexpected error: {e}')
        import traceback

        traceback.print_exc()


def test_individual_collector():
    """
    Test individual collector functions directly.
    """
    print('\n' + '=' * 60)
    print('TESTING INDIVIDUAL COLLECTORS')
    print('=' * 60)

    try:
        from datetime import datetime, timedelta

        from metrics_utility.automation_controller_billing import reports_collectors

        # Test time range
        until = datetime.now()
        since = until - timedelta(days=1)

        # Test the config collector (should always work)
        print('Testing config collector...')
        try:
            result = reports_collectors.config(since=since)
            print(f'✓ Config result: {result}')
        except Exception as e:
            print(f'✗ Config failed: {e}')

        # Test a simple collector that doesn't require much data
        print('\nTesting active_clusters_count collector...')
        try:
            result = reports_collectors.active_clusters_count(since=since, until=until)
            print(f'✓ Active clusters result: {result}')
        except Exception as e:
            print(f'✗ Active clusters failed: {e}')

        print('\n✓ Individual collector tests completed')

    except Exception as e:
        print(f'✗ Individual collector test failed: {e}')


if __name__ == '__main__':
    print('AWX Reports Collector Test Script')
    print('This script tests the new JSON-based reports collector')
    print()

    # Test individual collectors first (safer)
    test_individual_collector()

    # Then test full collection
    test_reports_collector()

    print('\n' + '=' * 60)
    print('TEST COMPLETE')
    print('=' * 60)
    print('If you see errors, they may be due to:')
    print('1. Missing database connection')
    print('2. Empty database (no AWX data)')
    print('3. Missing Django/AWX dependencies')
    print('4. Database permissions')
    print()
    print('To use in production:')
    print('python manage.py gather_automation_controller_reports_data --dry-run')
