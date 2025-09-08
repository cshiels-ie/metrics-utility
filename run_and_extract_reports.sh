#!/bin/bash

# Script to run the reports collector and extract the JSON files for viewing

set -e

echo "🚀 AWX Reports Collector - JSON File Extraction"
echo "================================================"

# Setup environment
source .venv/bin/activate

# Set up output directory
OUTPUT_DIR="/tmp/awx_reports_output"
EXTRACT_DIR="/tmp/awx_reports_extracted"

rm -rf "$OUTPUT_DIR" "$EXTRACT_DIR"
mkdir -p "$OUTPUT_DIR" "$EXTRACT_DIR"

echo "📁 Output directory: $OUTPUT_DIR"
echo "📁 Extract directory: $EXTRACT_DIR"
echo

# Set environment variables
export METRICS_UTILITY_SHIP_TARGET=directory
export METRICS_UTILITY_SHIP_PATH="$OUTPUT_DIR"

echo "🔄 Running reports collector..."
python manage.py gather_automation_controller_reports_data --dry-run --since=1d --verbose > /tmp/collector_output.log 2>&1

echo "✅ Collector completed. Checking for output files..."

# The collector creates temporary files, let's find them
echo "🔍 Searching for generated files..."

# Find any tar.gz files in /tmp that were created recently
RECENT_FILES=$(find /tmp -name "*.tar.gz" -newermt "2 minutes ago" 2>/dev/null || true)

if [ -n "$RECENT_FILES" ]; then
    echo "📦 Found recent tar.gz files:"
    echo "$RECENT_FILES"
    
    # Extract the first/most recent file
    LATEST_FILE=$(echo "$RECENT_FILES" | head -1)
    echo "📂 Extracting: $LATEST_FILE"
    
    cd "$EXTRACT_DIR"
    tar -xzf "$LATEST_FILE"
    
    echo "✅ Files extracted to: $EXTRACT_DIR"
    echo
    echo "📋 JSON Files found:"
    find "$EXTRACT_DIR" -name "*.json" -exec basename {} \; | sort
    
    echo
    echo "💡 To view a specific file:"
    echo "   cat $EXTRACT_DIR/*.json"
    
else
    echo "⚠️  No tar.gz files found. Let's check the collector output:"
    echo "📄 Last 20 lines of collector output:"
    tail -20 /tmp/collector_output.log
    
    echo
    echo "🔍 Let's look for any JSON files in /tmp:"
    find /tmp -name "*.json" -newermt "2 minutes ago" 2>/dev/null | head -10 || echo "No JSON files found"
    
    echo
    echo "💡 The collector might be working differently. Check the full log:"
    echo "   cat /tmp/collector_output.log"
fi

echo
echo "🎯 Summary:"
echo "   Extract directory: $EXTRACT_DIR"
echo "   Full log: /tmp/collector_output.log"

