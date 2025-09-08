#!/usr/bin/env python3
"""
Script to extract and view the JSON reports from the generated tar.gz files.

This script finds the most recent tar.gz files created by the reports collector
and extracts them so you can see the individual JSON files.
"""

import glob
import json
import os
import tarfile

from datetime import datetime


def find_recent_tgz_files():
    """Find recently created tar.gz files that might contain our reports."""
    # Common locations where files might be created
    search_paths = [
        '/tmp/**/automation-controller-*.tar.gz',
        '/tmp/**/awx-*.tar.gz',
        '/tmp/**/analytics-*.tar.gz',
        '/tmp/**/reports-*.tar.gz',
        '/tmp/*.tar.gz',
        '/tmp/reports_*/*.tar.gz',
        '/tmp/visible_reports/*.tar.gz',
        '/tmp/test_output/*.tar.gz',
    ]

    files = []
    for pattern in search_paths:
        files.extend(glob.glob(pattern, recursive=True))

    # Sort by modification time (newest first)
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return files


def extract_and_show_reports(tgz_file, output_dir):
    """Extract a tar.gz file and show the JSON reports."""
    print(f'\n📦 Extracting: {tgz_file}')
    print(f'📁 Output directory: {output_dir}')

    with tarfile.open(tgz_file, 'r:gz') as tar:
        # List contents
        members = tar.getmembers()
        json_files = [m for m in members if m.name.endswith('.json')]
        csv_files = [m for m in members if m.name.endswith('.csv')]

        print(f'📊 Found {len(json_files)} JSON files and {len(csv_files)} CSV files')

        # Extract all files
        tar.extractall(output_dir)

        # Show JSON files
        for member in json_files:
            file_path = os.path.join(output_dir, member.name)
            if os.path.exists(file_path):
                print(f'\n📄 {member.name}:')
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        print(json.dumps(data, indent=2)[:500] + '...' if len(json.dumps(data)) > 500 else json.dumps(data, indent=2))
                except Exception as e:
                    print(f'   Error reading file: {e}')


def main():
    print('🔍 Looking for reports collector tar.gz files...')

    tgz_files = find_recent_tgz_files()

    if not tgz_files:
        print('❌ No tar.gz files found. Try running the collector first:')
        print('   python manage.py gather_automation_controller_reports_data --dry-run --since=1d')
        return

    print(f'✅ Found {len(tgz_files)} tar.gz files:')
    for i, f in enumerate(tgz_files[:5]):  # Show first 5
        mtime = datetime.fromtimestamp(os.path.getmtime(f))
        print(f'   {i + 1}. {f} (modified: {mtime})')

    # Use the most recent file
    latest_file = tgz_files[0]
    print(f'\n🎯 Using most recent file: {latest_file}')

    # Create output directory
    output_dir = '/tmp/extracted_reports'
    os.makedirs(output_dir, exist_ok=True)

    # Extract and show
    extract_and_show_reports(latest_file, output_dir)

    print(f'\n✅ All files extracted to: {output_dir}')
    print('📋 Individual JSON files are now available for inspection!')


if __name__ == '__main__':
    main()
