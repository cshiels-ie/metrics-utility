#!/usr/bin/env python3
"""
Direct JSON extraction script that calls the collector functions directly
and saves the JSON files to a visible directory.
"""

import json
import os
import sys

from datetime import datetime, timedelta


# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock Django settings if needed
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
    print('Django not available - some functions may not work')


def extract_json_reports():
    """Extract JSON reports directly from collector functions."""
    try:
        import inspect

        from metrics_utility.automation_controller_billing import reports_collectors

        print('🚀 Direct JSON Reports Extraction')
        print('=' * 50)

        # Create output directory
        output_dir = '/tmp/json_reports_direct'
        os.makedirs(output_dir, exist_ok=True)
        print(f'📁 Output directory: {output_dir}')

        # Set up time parameters
        until = datetime.now()
        since = until - timedelta(days=1)

        print(f'📅 Time range: {since} to {until}')
        print()

        # Find all collector functions
        functions = []
        for name, obj in inspect.getmembers(reports_collectors):
            if inspect.isfunction(obj) and hasattr(obj, '__insights_analytics_key__'):
                functions.append(
                    {
                        'name': name,
                        'key': obj.__insights_analytics_key__,
                        'function': obj,
                        'format': obj.__insights_analytics_type__,
                    }
                )

        print(f'✅ Found {len(functions)} collector functions')
        print()

        # Call each function and save results
        successful = 0
        failed = 0

        for func_info in functions:
            func_name = func_info['name']
            func_key = func_info['key']
            func_obj = func_info['function']

            print(f'🔄 Processing: {func_key}')

            try:
                # Call the function
                if func_name == 'config':
                    # Config function doesn't need since/until
                    result = func_obj(since=since)
                else:
                    result = func_obj(since=since, until=until)

                # Save to JSON file
                output_file = os.path.join(output_dir, f'{func_key}.json')
                with open(output_file, 'w') as f:
                    json.dump(result, f, indent=2, default=str)

                print(f'   ✅ Saved: {output_file}')
                print(f'   📊 Size: {os.path.getsize(output_file)} bytes')

                # Show a preview of the data
                preview = json.dumps(result, default=str)
                if len(preview) > 200:
                    preview = preview[:200] + '...'
                print(f'   👀 Preview: {preview}')
                print()

                successful += 1

            except Exception as e:
                print(f'   ❌ Error: {e}')
                print()
                failed += 1

        print('=' * 50)
        print(f'📈 Summary: {successful} successful, {failed} failed')
        print(f'📁 All JSON files saved to: {output_dir}')

        # List the files
        files = os.listdir(output_dir)
        json_files = [f for f in files if f.endswith('.json')]
        print(f'📋 Generated {len(json_files)} JSON files:')
        for f in sorted(json_files):
            file_path = os.path.join(output_dir, f)
            size = os.path.getsize(file_path)
            print(f'   • {f} ({size} bytes)')

        return output_dir

    except Exception as e:
        print(f'❌ Failed to extract reports: {e}')
        import traceback

        traceback.print_exc()
        return None


if __name__ == '__main__':
    output_dir = extract_json_reports()
    if output_dir:
        print()
        print('🎉 SUCCESS! You can now view the JSON files at:')
        print(f'   {output_dir}')
        print()
        print('💡 To view a specific file:')
        print(f'   cat {output_dir}/active_clusters_count.json')
        print(f'   cat {output_dir}/job_execution_stats.json')
    else:
        print('❌ Extraction failed')
