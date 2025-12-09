"""Comprehensive tests for Airtable integration."""
import unittest
import asyncio
from mira.integrations.airtable_integration import AirtableIntegration


class TestAirtableIntegration(unittest.TestCase):
    """Comprehensive test cases for Airtable integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.valid_config = {
            'api_key': 'test_key_12345',
            'base_id': 'app_test_base_id'
        }
        self.integration = AirtableIntegration(self.valid_config)
    
    def test_initialization(self):
        """Test integration initialization."""
        self.assertEqual(self.integration.service_name, 'airtable')
        self.assertEqual(self.integration.api_key, 'test_key_12345')
        self.assertEqual(self.integration.base_id, 'app_test_base_id')
        self.assertFalse(self.integration.connected)
    
    def test_connect_with_valid_config(self):
        """Test connection with valid configuration."""
        result = self.integration.connect()
        self.assertTrue(result)
        self.assertTrue(self.integration.connected)
    
    def test_connect_without_config(self):
        """Test connection fails without configuration."""
        integration = AirtableIntegration()
        result = integration.connect()
        self.assertFalse(result)
        self.assertFalse(integration.connected)
    
    def test_connect_with_missing_api_key(self):
        """Test connection fails with missing API key."""
        integration = AirtableIntegration({'base_id': 'test_base'})
        result = integration.connect()
        self.assertFalse(result)
    
    def test_connect_with_missing_base_id(self):
        """Test connection fails with missing base ID."""
        integration = AirtableIntegration({'api_key': 'test_key'})
        result = integration.connect()
        self.assertFalse(result)
    
    def test_disconnect(self):
        """Test disconnection."""
        self.integration.connect()
        self.assertTrue(self.integration.connected)
        
        self.integration.disconnect()
        self.assertFalse(self.integration.connected)
    
    def test_sync_records_success(self):
        """Test successful records synchronization."""
        self.integration.connect()
        
        records = [
            {'id': 'rec1', 'fields': {'name': 'Record 1', 'value': 100}},
            {'id': 'rec2', 'fields': {'name': 'Record 2', 'value': 200}},
            {'id': 'rec3', 'fields': {'name': 'Record 3', 'value': 300}}
        ]
        
        result = self.integration.sync_data('records', records)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['synced_count'], 3)
        self.assertEqual(result['base_id'], 'app_test_base_id')
    
    def test_sync_empty_records(self):
        """Test synchronization with empty records list."""
        self.integration.connect()
        
        result = self.integration.sync_data('records', [])
        
        self.assertTrue(result['success'])
        self.assertEqual(result['synced_count'], 0)
    
    def test_sync_records_not_connected(self):
        """Test syncing records fails when not connected."""
        records = [{'id': 'rec1', 'fields': {'name': 'Record 1'}}]
        
        result = self.integration.sync_data('records', records)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Not connected', result['error'])
    
    def test_sync_reports_success(self):
        """Test successful reports synchronization."""
        self.integration.connect()
        
        reports = [
            {'id': 'rep1', 'title': 'Monthly Report', 'status': 'completed'},
            {'id': 'rep2', 'title': 'Quarterly Review', 'status': 'draft'}
        ]
        
        result = self.integration.sync_data('reports', reports)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['synced_count'], 2)
        self.assertEqual(result['base_id'], 'app_test_base_id')
    
    def test_sync_reports_not_connected(self):
        """Test syncing reports fails when not connected."""
        reports = [{'id': 'rep1', 'title': 'Report 1'}]
        
        result = self.integration.sync_data('reports', reports)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_sync_unknown_data_type(self):
        """Test syncing with unknown data type."""
        self.integration.connect()
        
        result = self.integration.sync_data('unknown_type', [])
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Unknown data type', result['error'])
    
    def test_get_kpis_success(self):
        """Test successful KPI retrieval."""
        self.integration.connect()
        
        result = self.integration.get_kpis('INIT-001')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['initiative_id'], 'INIT-001')
        self.assertIn('ebit_pct', result)
        self.assertIn('revenue_change', result)
        self.assertIn('cost_reduction', result)
        self.assertIn('last_updated', result)
        
        # Verify KPI values are numeric
        self.assertIsInstance(result['ebit_pct'], (int, float))
        self.assertIsInstance(result['revenue_change'], (int, float))
        self.assertIsInstance(result['cost_reduction'], (int, float))
    
    def test_get_kpis_not_connected(self):
        """Test getting KPI data when not connected."""
        result = self.integration.get_kpis('INIT-001')
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('Not connected', result['error'])
    
    def test_get_kpis_with_different_initiatives(self):
        """Test KPI retrieval for different initiatives."""
        self.integration.connect()
        
        initiatives = ['INIT-001', 'INIT-002', 'INIT-003']
        
        for init_id in initiatives:
            result = self.integration.get_kpis(init_id)
            self.assertTrue(result['success'])
            self.assertEqual(result['initiative_id'], init_id)
    
    def test_multiple_sync_operations(self):
        """Test multiple sequential sync operations."""
        self.integration.connect()
        
        # First sync
        records1 = [{'id': 'rec1', 'data': 'Data 1'}]
        result1 = self.integration.sync_data('records', records1)
        self.assertTrue(result1['success'])
        self.assertEqual(result1['synced_count'], 1)
        
        # Second sync
        records2 = [
            {'id': 'rec2', 'data': 'Data 2'},
            {'id': 'rec3', 'data': 'Data 3'}
        ]
        result2 = self.integration.sync_data('records', records2)
        self.assertTrue(result2['success'])
        self.assertEqual(result2['synced_count'], 2)
    
    def test_connection_lifecycle(self):
        """Test complete connection lifecycle."""
        # Initial state
        self.assertFalse(self.integration.connected)
        
        # Connect
        self.assertTrue(self.integration.connect())
        self.assertTrue(self.integration.connected)
        
        # Use connection
        result = self.integration.sync_data('records', [{'id': 'rec1'}])
        self.assertTrue(result['success'])
        
        # Disconnect
        self.integration.disconnect()
        self.assertFalse(self.integration.connected)
        
        # Verify operations fail after disconnect
        result = self.integration.sync_data('records', [{'id': 'rec2'}])
        self.assertFalse(result['success'])
    
    def test_reconnection(self):
        """Test reconnecting after disconnect."""
        # First connection
        self.integration.connect()
        self.assertTrue(self.integration.connected)
        
        # Disconnect
        self.integration.disconnect()
        self.assertFalse(self.integration.connected)
        
        # Reconnect
        self.integration.connect()
        self.assertTrue(self.integration.connected)
        
        # Verify functionality works
        result = self.integration.sync_data('records', [{'id': 'rec1'}])
        self.assertTrue(result['success'])
    
    def test_sync_large_dataset(self):
        """Test syncing a large dataset."""
        self.integration.connect()
        
        # Create a large dataset
        large_dataset = [
            {'id': f'rec{i}', 'fields': {'value': i}}
            for i in range(1000)
        ]
        
        result = self.integration.sync_data('records', large_dataset)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['synced_count'], 1000)
    
    def test_validate_config_method(self):
        """Test configuration validation."""
        # Valid configuration
        self.assertTrue(self.integration.validate_config(['api_key', 'base_id']))
        
        # Missing fields
        incomplete_integration = AirtableIntegration({'api_key': 'test'})
        self.assertFalse(incomplete_integration.validate_config(['api_key', 'base_id']))
    
    def test_sync_with_metadata(self):
        """Test synchronization with additional metadata."""
        self.integration.connect()
        
        records_with_metadata = [
            {
                'id': 'rec1',
                'fields': {
                    'name': 'Project Alpha',
                    'status': 'active',
                    'owner': 'team@example.com'
                },
                'metadata': {
                    'created_at': '2025-01-01',
                    'updated_at': '2025-12-09'
                }
            }
        ]
        
        result = self.integration.sync_data('records', records_with_metadata)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['synced_count'], 1)


class TestAirtableIntegrationAsync(unittest.TestCase):
    """Test async operations with Airtable integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.valid_config = {
            'api_key': 'test_key_async',
            'base_id': 'app_test_async'
        }
        self.integration = AirtableIntegration(self.valid_config)
    
    def test_concurrent_operations(self):
        """Test that integration can handle operations correctly."""
        self.integration.connect()
        
        # Simulate concurrent-like operations
        results = []
        for i in range(5):
            records = [{'id': f'rec{i}', 'data': f'Data {i}'}]
            result = self.integration.sync_data('records', records)
            results.append(result)
        
        # All operations should succeed
        for result in results:
            self.assertTrue(result['success'])
            self.assertEqual(result['synced_count'], 1)


if __name__ == '__main__':
    unittest.main()
