"""
Simple test to verify the async library functionality
"""

import asyncio
import os
import tempfile

from .async_client import AsyncMetricsClient
from .models import CollectionConfig, ReportConfig, ReportType, ShipTarget


async def test_library_imports():
    """Test that all library components can be imported"""
    print('✓ Testing library imports...')

    # Test client creation
    client = AsyncMetricsClient()
    assert client is not None
    print('  ✓ AsyncMetricsClient created')

    # Test config creation
    collection_config = CollectionConfig(ship_target=ShipTarget.DIRECTORY, ship_path='./test')
    assert collection_config.ship_target == ShipTarget.DIRECTORY
    print('  ✓ CollectionConfig created')

    report_config = ReportConfig(report_type=ReportType.CCSPV2, ship_target=ShipTarget.DIRECTORY, ship_path='./test', month='2024-04')
    assert report_config.report_type == ReportType.CCSPV2
    print('  ✓ ReportConfig created')


async def test_status_methods():
    """Test status and listing methods with temporary directory"""
    print('✓ Testing status methods...')

    with tempfile.TemporaryDirectory() as temp_dir:
        client = AsyncMetricsClient()

        # Test collection status (should show no data)
        status = await client.get_collection_status(temp_dir)
        assert status['has_data'] is False
        print('  ✓ get_collection_status works')

        # Test list reports (should be empty)
        reports = await client.list_available_reports(temp_dir)
        assert isinstance(reports, list)
        assert len(reports) == 0
        print('  ✓ list_available_reports works')


async def test_environment_management():
    """Test environment variable management"""
    print('✓ Testing environment management...')

    from .environment import EnvironmentManager

    # Test collection config to env conversion
    config = CollectionConfig(ship_target=ShipTarget.DIRECTORY, ship_path='./test', billing_account_id='test-account')

    env_vars = EnvironmentManager.create_environment_context(config)
    assert env_vars['METRICS_UTILITY_SHIP_TARGET'] == 'directory'
    assert env_vars['METRICS_UTILITY_SHIP_PATH'] == './test'
    assert env_vars['METRICS_UTILITY_BILLING_ACCOUNT_ID'] == 'test-account'
    print('  ✓ Environment variable conversion works')

    # Test environment context manager
    original_value = os.environ.get('TEST_VAR')
    test_env = {'TEST_VAR': 'test_value'}

    with EnvironmentManager.apply_environment(test_env):
        assert os.environ.get('TEST_VAR') == 'test_value'

    # Should be restored
    assert os.environ.get('TEST_VAR') == original_value
    print('  ✓ Environment context manager works')


async def test_sync_wrapper_creation():
    """Test that sync wrapper can be created and has expected methods"""
    print('✓ Testing sync wrapper...')

    from .sync_wrapper import SyncWrapper

    wrapper = SyncWrapper()
    assert hasattr(wrapper, 'run_collection')
    assert hasattr(wrapper, 'run_report')
    assert hasattr(wrapper, 'get_collection_status')
    assert hasattr(wrapper, 'list_available_reports')
    print('  ✓ SyncWrapper has all required methods')


async def test_validation():
    """Test configuration validation"""
    print('✓ Testing configuration validation...')

    client = AsyncMetricsClient()

    # Test invalid collection config (missing ship_path)
    try:
        invalid_config = CollectionConfig(
            ship_target=ShipTarget.DIRECTORY,
            ship_path='',  # Empty path should cause validation error
        )
        client._validate_collection_config(invalid_config)
        assert False, 'Should have raised ConfigurationError'
    except Exception as e:
        assert 'ship_path is required' in str(e)
        print('  ✓ Collection config validation works')

    # Test invalid report config (no time specification)
    try:
        invalid_report_config = ReportConfig(
            report_type=ReportType.CCSPV2,
            ship_target=ShipTarget.DIRECTORY,
            ship_path='./test',
            # No month, since, or until specified
        )
        client._validate_report_config(invalid_report_config)
        assert False, 'Should have raised ConfigurationError'
    except Exception as e:
        assert 'month or since/until must be specified' in str(e)
        print('  ✓ Report config validation works')


async def run_all_tests():
    """Run all tests"""
    print('🧪 Running async library tests...\n')

    try:
        await test_library_imports()
        await test_status_methods()
        await test_environment_management()
        await test_sync_wrapper_creation()
        await test_validation()

        print('\n🎉 All tests passed! The async library is functional.')
        return True

    except Exception as e:
        print(f'\n❌ Test failed: {e}')
        import traceback

        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
