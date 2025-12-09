"""Tests for authentication and API key management."""
import unittest
from unittest.mock import Mock
from mira.auth.api_key_manager import ApiKeyManager, ApiKey
from mira.integrations.airtable_integration import AirtableIntegration


class TestApiKeyManager(unittest.TestCase):
    """Test cases for ApiKeyManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create manager without storage for basic tests
        self.manager = ApiKeyManager(storage_backend=None, default_expiry_days=90)
    
    def test_generate_key_viewer(self):
        """Test generating a viewer API key."""
        raw_key, api_key = self.manager.generate_key(role='viewer', name='Test Viewer')
        
        self.assertIsNotNone(raw_key)
        self.assertIsNotNone(api_key)
        self.assertEqual(api_key.role, 'viewer')
        self.assertEqual(api_key.status, 'active')
        self.assertEqual(api_key.name, 'Test Viewer')
        self.assertIsNotNone(api_key.key_id)
        self.assertIsNotNone(api_key.created_at)
        self.assertIsNotNone(api_key.expires_at)
    
    def test_generate_key_admin(self):
        """Test generating an admin API key."""
        raw_key, api_key = self.manager.generate_key(role='admin')
        
        self.assertEqual(api_key.role, 'admin')
        self.assertEqual(api_key.status, 'active')
    
    def test_generate_key_operator(self):
        """Test generating an operator API key."""
        raw_key, api_key = self.manager.generate_key(role='operator')
        
        self.assertEqual(api_key.role, 'operator')
        self.assertEqual(api_key.status, 'active')
    
    def test_generate_key_invalid_role(self):
        """Test generating a key with invalid role raises ValueError."""
        with self.assertRaises(ValueError):
            self.manager.generate_key(role='invalid_role')
    
    def test_generate_key_no_expiry(self):
        """Test generating a key with no expiration."""
        raw_key, api_key = self.manager.generate_key(role='admin', expiry_days=0)
        
        self.assertIsNone(api_key.expires_at)
    
    def test_validate_key_success(self):
        """Test validating a valid API key."""
        raw_key, api_key = self.manager.generate_key(role='viewer')
        
        validated_key = self.manager.validate_key(raw_key)
        
        self.assertIsNotNone(validated_key)
        self.assertEqual(validated_key.key_id, api_key.key_id)
        self.assertEqual(validated_key.role, 'viewer')
        self.assertIsNotNone(validated_key.last_used)
    
    def test_validate_key_invalid(self):
        """Test validating an invalid API key."""
        validated_key = self.manager.validate_key('invalid_key')
        
        self.assertIsNone(validated_key)
    
    def test_validate_key_revoked(self):
        """Test validating a revoked API key."""
        raw_key, api_key = self.manager.generate_key(role='viewer')
        self.manager.revoke_key(api_key.key_id)
        
        validated_key = self.manager.validate_key(raw_key)
        
        self.assertIsNone(validated_key)
    
    def test_revoke_key_success(self):
        """Test revoking an API key."""
        raw_key, api_key = self.manager.generate_key(role='viewer')
        
        success = self.manager.revoke_key(api_key.key_id)
        
        self.assertTrue(success)
        self.assertEqual(api_key.status, 'revoked')
    
    def test_revoke_key_not_found(self):
        """Test revoking a non-existent key."""
        success = self.manager.revoke_key('non_existent_key')
        
        self.assertFalse(success)
    
    def test_rotate_key_success(self):
        """Test rotating an API key."""
        raw_key, old_api_key = self.manager.generate_key(role='viewer')
        
        new_raw_key, new_api_key = self.manager.rotate_key(old_api_key.key_id)
        
        self.assertIsNotNone(new_raw_key)
        self.assertNotEqual(new_raw_key, raw_key)
        self.assertEqual(new_api_key.role, 'viewer')
        self.assertEqual(new_api_key.status, 'active')
        self.assertEqual(old_api_key.status, 'revoked')
    
    def test_rotate_key_with_role_change(self):
        """Test rotating a key and changing its role."""
        raw_key, old_api_key = self.manager.generate_key(role='viewer')
        
        new_raw_key, new_api_key = self.manager.rotate_key(old_api_key.key_id, role='admin')
        
        self.assertEqual(new_api_key.role, 'admin')
    
    def test_rotate_key_not_found(self):
        """Test rotating a non-existent key."""
        with self.assertRaises(ValueError):
            self.manager.rotate_key('non_existent_key')
    
    def test_list_keys(self):
        """Test listing all API keys."""
        self.manager.generate_key(role='viewer')
        self.manager.generate_key(role='admin')
        self.manager.generate_key(role='operator')
        
        keys = self.manager.list_keys()
        
        self.assertEqual(len(keys), 3)
    
    def test_list_keys_filter_by_role(self):
        """Test listing API keys filtered by role."""
        self.manager.generate_key(role='viewer')
        self.manager.generate_key(role='admin')
        self.manager.generate_key(role='viewer')
        
        viewer_keys = self.manager.list_keys(role='viewer')
        
        self.assertEqual(len(viewer_keys), 2)
        for key in viewer_keys:
            self.assertEqual(key.role, 'viewer')
    
    def test_list_keys_filter_by_status(self):
        """Test listing API keys filtered by status."""
        raw_key1, api_key1 = self.manager.generate_key(role='viewer')
        raw_key2, api_key2 = self.manager.generate_key(role='admin')
        
        self.manager.revoke_key(api_key1.key_id)
        
        active_keys = self.manager.list_keys(status='active')
        revoked_keys = self.manager.list_keys(status='revoked')
        
        self.assertEqual(len(active_keys), 1)
        self.assertEqual(len(revoked_keys), 1)
    
    def test_check_permission_viewer(self):
        """Test permission checking for viewer role."""
        raw_key, api_key = self.manager.generate_key(role='viewer')
        
        self.assertTrue(self.manager.check_permission(api_key, 'read'))
        self.assertTrue(self.manager.check_permission(api_key, 'list'))
        self.assertFalse(self.manager.check_permission(api_key, 'write'))
        self.assertFalse(self.manager.check_permission(api_key, 'manage_keys'))
    
    def test_check_permission_operator(self):
        """Test permission checking for operator role."""
        raw_key, api_key = self.manager.generate_key(role='operator')
        
        self.assertTrue(self.manager.check_permission(api_key, 'read'))
        self.assertTrue(self.manager.check_permission(api_key, 'write'))
        self.assertTrue(self.manager.check_permission(api_key, 'execute'))
        self.assertFalse(self.manager.check_permission(api_key, 'manage_keys'))
    
    def test_check_permission_admin(self):
        """Test permission checking for admin role."""
        raw_key, api_key = self.manager.generate_key(role='admin')
        
        self.assertTrue(self.manager.check_permission(api_key, 'read'))
        self.assertTrue(self.manager.check_permission(api_key, 'write'))
        self.assertTrue(self.manager.check_permission(api_key, 'execute'))
        self.assertTrue(self.manager.check_permission(api_key, 'manage_keys'))
        self.assertTrue(self.manager.check_permission(api_key, 'manage_users'))


class TestApiKeyManagerWithStorage(unittest.TestCase):
    """Test cases for ApiKeyManager with Airtable storage."""
    
    def setUp(self):
        """Set up test fixtures with mock storage."""
        # Create a mock Airtable integration
        self.mock_storage = Mock(spec=AirtableIntegration)
        self.mock_storage.sync_data.return_value = {'success': True, 'keys': []}
        
        self.manager = ApiKeyManager(
            storage_backend=self.mock_storage,
            default_expiry_days=90
        )
    
    def test_generate_key_saves_to_storage(self):
        """Test that generating a key saves it to storage."""
        raw_key, api_key = self.manager.generate_key(role='viewer')
        
        # Verify storage was called
        self.mock_storage.sync_data.assert_called()
        call_args = self.mock_storage.sync_data.call_args
        self.assertEqual(call_args[0][0], 'api_keys')
        self.assertEqual(call_args[0][1]['action'], 'save')


class TestApiKey(unittest.TestCase):
    """Test cases for ApiKey dataclass."""
    
    def test_api_key_to_dict(self):
        """Test converting ApiKey to dictionary."""
        api_key = ApiKey(
            key_id='test_key_123',
            key_hash='hash123',
            role='viewer',
            created_at='2025-12-09T00:00:00',
            expires_at='2025-03-09T00:00:00',
            last_used=None,
            status='active',
            name='Test Key'
        )
        
        key_dict = api_key.to_dict()
        
        self.assertEqual(key_dict['key_id'], 'test_key_123')
        self.assertEqual(key_dict['role'], 'viewer')
        self.assertEqual(key_dict['status'], 'active')
    
    def test_api_key_from_dict(self):
        """Test creating ApiKey from dictionary."""
        key_dict = {
            'key_id': 'test_key_123',
            'key_hash': 'hash123',
            'role': 'admin',
            'created_at': '2025-12-09T00:00:00',
            'expires_at': '2025-03-09T00:00:00',
            'last_used': None,
            'status': 'active',
            'name': 'Test Key'
        }
        
        api_key = ApiKey.from_dict(key_dict)
        
        self.assertEqual(api_key.key_id, 'test_key_123')
        self.assertEqual(api_key.role, 'admin')
        self.assertEqual(api_key.status, 'active')


if __name__ == '__main__':
    unittest.main()
