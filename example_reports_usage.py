#!/usr/bin/env python3
"""
Example usage script for the new reports_collectors module.

This script demonstrates how to use the new JSON-based collector that provides
comprehensive reporting metrics for AWX Automation Controller.

Run this script to collect all the specified reporting metrics and output them
as JSON instead of CSV files.
"""

import json
import os
import sys


# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the collector infrastructure
from metrics_utility.automation_controller_billing import reports_collectors


def example_reports_collection():
    """
    Example of how to use the reports_collectors module to gather
    comprehensive JSON-based metrics.
    """
    print('=' * 60)
    print('AWX Reports Collector - JSON Output Example')
    print('=' * 60)

    print('\nThis collector provides the following metrics:')
    print('• Active number of Clusters')
    print('• Active number of Clusters by Controller Version')
    print('• Total number of modules automated')
    print('• Job duration average/min/max/total in seconds/minutes by template')
    print('• Avg tasks by template')
    print('• Number of jobs that succeeded/failed/executed')
    print('• Number of tasks executed')
    print('• Success ratio of tasks executed')
    print('• Failure/Success rate of modules')
    print('• KPI - count of Modules used across all customer, grouped by job ID')
    print('• Number of templates executed by company')
    print('• Total number of hosts automated over time')
    print('• Number of execution environment configured in the controller')
    print('• Ratio of Default EE vs Custom EE')
    print('• Modules Used to Automate')
    print('• Avg number of modules used in a playbook')

    print('\n' + '=' * 60)
    print('USAGE INSTRUCTIONS')
    print('=' * 60)

    print('\n1. To use this collector in your AWX environment:')
    print('   from metrics_utility.automation_controller_billing.collector import Collector')
    print('   from metrics_utility.automation_controller_billing import reports_collectors')

    print('\n2. Create a collector instance:')
    print('   collector = Collector(')
    print('       collection_type=Collector.DRY_RUN,  # or MANUAL_COLLECTION')
    print('       collector_module=reports_collectors')
    print('   )')

    print('\n3. Run the collection:')
    print('   collector.gather()')

    print('\n4. Output will be JSON files instead of CSV files.')

    print('\n' + '=' * 60)
    print('EXAMPLE COLLECTOR FUNCTIONS')
    print('=' * 60)

    # Show what functions are available
    import inspect

    functions = []
    for name, obj in inspect.getmembers(reports_collectors):
        if inspect.isfunction(obj) and hasattr(obj, '__insights_analytics_key__'):
            functions.append(
                {
                    'name': name,
                    'key': obj.__insights_analytics_key__,
                    'description': obj.__insights_analytics_description__ or 'No description',
                    'format': obj.__insights_analytics_type__,
                }
            )

    print(f'\nFound {len(functions)} collector functions:')
    for func in functions:
        print(f'• {func["key"]} ({func["format"]})')
        print(f'  Function: {func["name"]}()')
        print(f'  Description: {func["description"]}')
        print()

    print('=' * 60)
    print('SAMPLE OUTPUT STRUCTURE')
    print('=' * 60)

    print('\nEach collector function returns a JSON structure like:')
    print(
        json.dumps(
            {
                'data_field': 'actual_metric_data',
                'period_start': '2024-01-01T00:00:00Z',
                'period_end': '2024-01-07T23:59:59Z',
            },
            indent=2,
        )
    )

    print('\nFor detailed metrics, the structure might be:')
    print(
        json.dumps(
            {
                'job_duration_stats': [
                    {
                        'template_name': 'Deploy Application',
                        'template_id': 123,
                        'job_count': 45,
                        'avg_duration_seconds': 120.5,
                        'avg_duration_minutes': 2.0,
                    }
                ],
                'period_start': '2024-01-01T00:00:00Z',
                'period_end': '2024-01-07T23:59:59Z',
            },
            indent=2,
        )
    )

    print('\n' + '=' * 60)
    print('INTEGRATION WITH EXISTING BILLING COLLECTOR')
    print('=' * 60)

    print('\nTo use alongside the existing billing collector:')
    print('1. The reports_collectors module is in the same package')
    print('2. It follows the same patterns as the existing collectors.py')
    print('3. Use the same Collector class but specify reports_collectors as the module')
    print('4. All output will be JSON instead of CSV for easier consumption by')
    print('   dashboards and reporting tools')

    print('\n' + '=' * 60)
    print('READY TO USE!')
    print('=' * 60)


if __name__ == '__main__':
    example_reports_collection()
