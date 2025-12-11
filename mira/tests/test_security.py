"""Tests for security features."""
import unittest
import os
import tempfile
from datetime import datetime, timedelta
from mira.security.api_key_manager import APIKeyManager
from mira.security.audit_logger import AuditLogger
from mira.security.webhook_security import WebhookSecurity


class TestAPIKeyManager(unittest.TestCase):
    """Test cases for API Key Manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.audit_logger = AuditLogger()
        self.manager = APIKeyManager(audit_logger=self.audit_logger)
        
    def test_generate_key(self):
        """Test API key generation."""
        key_id, raw_key = self.manager.generate_key("test_key")
        
        self.assertIsNotNone(key_id)
        self.assertIsNotNone(raw_key)
        self.assertIn(key_id, self.manager.keys)
        self.assertEqual(self.manager.keys[key_id].name, "test_key")
        
    def test_generate_key_with_expiry(self):
        """Test API key generation with expiry."""
        key_id, raw_key = self.manager.generate_key("test_key", expires_in_days=7)
        
        api_key = self.manager.keys[key_id]
        self.assertIsNotNone(api_key.expires_at)
        
        # Check expiry is approximately 7 days from now
        expected_expiry = datetime.utcnow() + timedelta(days=7)
        delta = abs((api_key.expires_at - expected_expiry).total_seconds())
        self.assertLess(delta, 60)  # Within 60 seconds
        
    def test_validate_key_success(self):
        """Test successful key validation."""
        key_id, raw_key = self.manager.generate_key("test_key")
        
        is_valid, validated_key_id, reason = self.manager.validate_key(raw_key)
        
        self.assertTrue(is_valid)
        self.assertEqual(validated_key_id, key_id)
        self.assertIsNone(reason)
        
    def test_validate_key_not_found(self):
        """Test validation of non-existent key."""
        is_valid, key_id, reason = self.manager.validate_key("invalid_key")
        
        self.assertFalse(is_valid)
        self.assertIsNone(key_id)
        self.assertEqual(reason, 'not_found')
        
    def test_validate_expired_key(self):
        """Test validation of expired key."""
        key_id, raw_key = self.manager.generate_key("test_key", expires_in_days=7)
        
        # Manually set expiry to past
        self.manager.keys[key_id].expires_at = datetime.utcnow() - timedelta(days=1)
        
        is_valid, validated_key_id, reason = self.manager.validate_key(raw_key)
        
        self.assertFalse(is_valid)
        self.assertEqual(validated_key_id, key_id)
        self.assertEqual(reason, 'expired')
        
    def test_validate_revoked_key(self):
        """Test validation of revoked key."""
        key_id, raw_key = self.manager.generate_key("test_key")
        
        # Revoke the key
        self.manager.revoke_key(key_id)
        
        is_valid, validated_key_id, reason = self.manager.validate_key(raw_key)
        
        self.assertFalse(is_valid)
        self.assertEqual(validated_key_id, key_id)
        self.assertEqual(reason, 'revoked')
        
    def test_rotate_key(self):
        """Test key rotation."""
        old_key_id, old_raw_key = self.manager.generate_key("test_key")
        
        # Rotate key
        new_key_id, new_raw_key = self.manager.rotate_key(old_key_id, grace_period_days=7)
        
        # Both keys should exist
        self.assertIn(old_key_id, self.manager.keys)
        self.assertIn(new_key_id, self.manager.keys)
        
        # Old key should have expiry set
        self.assertIsNotNone(self.manager.keys[old_key_id].expires_at)
        
        # New key should reference old key
        self.assertEqual(self.manager.keys[new_key_id].rotated_from, old_key_id)
        
        # Both keys should be valid during grace period
        self.assertTrue(self.manager.validate_key(old_raw_key)[0])
        self.assertTrue(self.manager.validate_key(new_raw_key)[0])
        
    def test_rotate_key_invalid(self):
        """Test rotating non-existent key."""
        with self.assertRaises(ValueError):
            self.manager.rotate_key("invalid_key_id")
            
    def test_revoke_key(self):
        """Test key revocation."""
        key_id, raw_key = self.manager.generate_key("test_key")
        
        # Revoke key
        result = self.manager.revoke_key(key_id)
        
        self.assertTrue(result)
        self.assertTrue(self.manager.keys[key_id].revoked)
        
    def test_list_keys(self):
        """Test listing keys."""
        # Create some keys
        self.manager.generate_key("key1")
        key2_id, _ = self.manager.generate_key("key2")
        self.manager.generate_key("key3")
        
        # Revoke one
        self.manager.revoke_key(key2_id)
        
        # List without revoked
        keys = self.manager.list_keys(include_revoked=False)
        self.assertEqual(len(keys), 2)
        
        # List with revoked
        keys = self.manager.list_keys(include_revoked=True)
        self.assertEqual(len(keys), 3)
        
    def test_cleanup_expired_keys(self):
        """Test cleanup of expired keys."""
        # Create key with past expiry
        key_id, _ = self.manager.generate_key("test_key", expires_in_days=1)
        self.manager.keys[key_id].expires_at = datetime.utcnow() - timedelta(days=40)
        
        # Cleanup
        removed = self.manager.cleanup_expired_keys()
        
        self.assertEqual(removed, 1)
        self.assertNotIn(key_id, self.manager.keys)


class TestWebhookSecurity(unittest.TestCase):
    """Test cases for Webhook Security."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.audit_logger = AuditLogger()
        self.security = WebhookSecurity(audit_logger=self.audit_logger)
        
    def test_ip_allowlist(self):
        """Test IP allowlist."""
        # Add IP to allowlist
        self.security.add_ip_to_allowlist("192.168.1.0/24")
        
        # Check IP in range
        is_allowed, reason = self.security.check_ip_allowed("192.168.1.100")
        self.assertTrue(is_allowed)
        
        # Check IP outside range
        is_allowed, reason = self.security.check_ip_allowed("10.0.0.1")
        self.assertFalse(is_allowed)
        self.assertEqual(reason, 'not_in_allowlist')
        
    def test_ip_denylist(self):
        """Test IP denylist."""
        # Add IP to denylist
        self.security.add_ip_to_denylist("192.168.1.100")
        
        # Check denied IP
        is_allowed, reason = self.security.check_ip_allowed("192.168.1.100")
        self.assertFalse(is_allowed)
        self.assertEqual(reason, 'in_denylist')
        
        # Check allowed IP
        is_allowed, reason = self.security.check_ip_allowed("192.168.1.101")
        self.assertTrue(is_allowed)
        
    def test_service_secret(self):
        """Test service shared secret."""
        # Set secret for service
        self.security.set_service_secret("github", "secret123")
        
        # Verify correct secret
        is_valid = self.security.verify_service_secret("github", "secret123")
        self.assertTrue(is_valid)
        
        # Verify incorrect secret
        is_valid = self.security.verify_service_secret("github", "wrong_secret")
        self.assertFalse(is_valid)
        
    def test_authenticate_webhook_success(self):
        """Test successful webhook authentication."""
        # Setup
        self.security.add_ip_to_allowlist("192.168.1.0/24")
        self.security.set_service_secret("github", "secret123")
        
        # Authenticate
        is_auth, reason = self.security.authenticate_webhook(
            "github",
            "192.168.1.100",
            "secret123"
        )
        
        self.assertTrue(is_auth)
        self.assertIsNone(reason)
        
    def test_authenticate_webhook_ip_blocked(self):
        """Test webhook authentication with blocked IP."""
        self.security.add_ip_to_denylist("192.168.1.100")
        
        is_auth, reason = self.security.authenticate_webhook(
            "github",
            "192.168.1.100",
            None
        )
        
        self.assertFalse(is_auth)
        self.assertIn('ip_', reason)
        
    def test_authenticate_webhook_missing_secret(self):
        """Test webhook authentication with missing secret."""
        self.security.set_service_secret("github", "secret123")
        
        is_auth, reason = self.security.authenticate_webhook(
            "github",
            "192.168.1.100",
            None
        )
        
        self.assertFalse(is_auth)
        self.assertEqual(reason, 'missing_secret')
        
    def test_authenticate_webhook_invalid_secret(self):
        """Test webhook authentication with invalid secret."""
        self.security.set_service_secret("github", "secret123")
        
        is_auth, reason = self.security.authenticate_webhook(
            "github",
            "192.168.1.100",
            "wrong_secret"
        )
        
        self.assertFalse(is_auth)
        self.assertEqual(reason, 'invalid_secret')


class TestAuditLogger(unittest.TestCase):
    """Test cases for Audit Logger."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.logger = AuditLogger()
        
    def test_log_event(self):
        """Test logging an event."""
        # Should not raise exception
        self.logger.log_event(
            'test_event',
            {'key': 'value'},
            user_id='user123',
            ip_address='192.168.1.1'
        )
        
    def test_log_authentication(self):
        """Test logging authentication."""
        # Should not raise exception
        self.logger.log_authentication(
            success=True,
            method='api_key',
            details={'key_id': 'test123'},
            ip_address='192.168.1.1'
        )
        
    def test_log_key_lifecycle(self):
        """Test logging key lifecycle."""
        # Should not raise exception
        self.logger.log_key_lifecycle(
            action='created',
            key_id='test123',
            details={'name': 'test_key'}
        )


class TestAPIKeyManagerEnhancements(unittest.TestCase):
    """Test cases for API Key Manager production enhancements."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.audit_logger = AuditLogger()
        self.manager = APIKeyManager(audit_logger=self.audit_logger)
    
    def test_generate_key_with_quota(self):
        """Test API key generation with usage quota."""
        key_id, raw_key = self.manager.generate_key(
            "test_key",
            requests_per_hour=1000
        )
        
        api_key = self.manager.keys[key_id]
        self.assertEqual(api_key.requests_per_hour, 1000)
    
    def test_key_usage_tracking(self):
        """Test that key usage is tracked."""
        key_id, raw_key = self.manager.generate_key("test_key")
        
        # Validate key multiple times
        for _ in range(5):
            is_valid, _, _ = self.manager.validate_key(raw_key)
            self.assertTrue(is_valid)
        
        # Check usage count
        api_key = self.manager.keys[key_id]
        self.assertEqual(api_key.usage_count, 5)
        self.assertIsNotNone(api_key.last_used_at)
    
    def test_rotate_unused_keys(self):
        """Test automatic rotation of unused keys."""
        # Create a key and backdate it
        key_id, raw_key = self.manager.generate_key("old_key")
        api_key = self.manager.keys[key_id]
        api_key.created_at = datetime.utcnow() - timedelta(days=100)
        
        # Rotate unused keys (>90 days)
        rotated = self.manager.rotate_unused_keys(days_unused=90)
        
        # Should have rotated one key
        self.assertEqual(len(rotated), 1)
        self.assertEqual(rotated[0][0], key_id)
    
    def test_export_key_inventory_csv(self):
        """Test exporting key inventory to CSV."""
        # Create some test keys
        self.manager.generate_key("key1", expires_in_days=30)
        self.manager.generate_key("key2", requests_per_hour=100)
        
        # Export to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            temp_path = f.name
        
        try:
            success = self.manager.export_key_inventory_csv(temp_path)
            self.assertTrue(success)
            
            # Verify file was created and has content
            self.assertTrue(os.path.exists(temp_path))
            with open(temp_path, 'r') as f:
                content = f.read()
                self.assertIn('key_id', content)
                self.assertIn('name', content)
                self.assertIn('key1', content)
                self.assertIn('key2', content)
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_list_keys_includes_new_fields(self):
        """Test that list_keys includes new fields."""
        key_id, raw_key = self.manager.generate_key(
            "test_key",
            requests_per_hour=500
        )
        
        # Use the key once
        self.manager.validate_key(raw_key)
        
        # List keys
        keys = self.manager.list_keys()
        self.assertEqual(len(keys), 1)
        
        key_info = keys[0]
        self.assertIn('last_used_at', key_info)
        self.assertIn('usage_count', key_info)
        self.assertIn('requests_per_hour', key_info)
        self.assertEqual(key_info['requests_per_hour'], 500)
        self.assertEqual(key_info['usage_count'], 1)


if __name__ == '__main__':
    unittest.main()
