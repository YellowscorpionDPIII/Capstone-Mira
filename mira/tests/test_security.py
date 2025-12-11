"""Tests for security features: API key manager and webhook security."""
import unittest
from datetime import datetime, timedelta
from mira.core.api_key_manager import (
    APIKeyManager, InMemoryAPIKeyStorage, FileAPIKeyStorage,
    APIKeyRecord, KeyStatus
)
from mira.core.webhook_security import (
    WebhookAuthenticator, WebhookSecurityConfig, AuthFailureReason
)
import tempfile
import os
import hmac
import hashlib


class TestAPIKeyManager(unittest.TestCase):
    """Test cases for API Key Manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.storage = InMemoryAPIKeyStorage()
        self.manager = APIKeyManager(self.storage, default_expiry_days=90)
    
    def test_create_key(self):
        """Test creating a new API key."""
        api_key, record = self.manager.create()
        
        self.assertIsNotNone(api_key)
        self.assertIsNotNone(record.key_id)
        self.assertIsNotNone(record.key_hash)
        self.assertIsNotNone(record.created_at)
        self.assertIsNotNone(record.expires_at)
    
    def test_create_key_with_custom_expiry(self):
        """Test creating a key with custom expiration."""
        api_key, record = self.manager.create(expires_in_days=30)
        
        expected_expiry = record.created_at + timedelta(days=30)
        self.assertAlmostEqual(
            record.expires_at.timestamp(),
            expected_expiry.timestamp(),
            delta=1
        )
    
    def test_validate_key(self):
        """Test validating an API key."""
        api_key, record = self.manager.create()
        
        is_valid, key_id, status = self.manager.validate(api_key)
        
        self.assertTrue(is_valid)
        self.assertEqual(key_id, record.key_id)
        self.assertEqual(status, KeyStatus.ACTIVE)
    
    def test_validate_invalid_key(self):
        """Test validating an invalid API key."""
        is_valid, key_id, status = self.manager.validate("invalid_key")
        
        self.assertFalse(is_valid)
        self.assertIsNone(key_id)
        self.assertIsNone(status)
    
    def test_rotate_key(self):
        """Test rotating an API key."""
        old_key, old_record = self.manager.create(key_id="test_key")
        
        new_key, new_record = self.manager.rotate("test_key")
        
        self.assertNotEqual(old_key, new_key)
        self.assertEqual(old_record.key_id, new_record.key_id)
        
        # Old key should no longer be valid
        is_valid, _, _ = self.manager.validate(old_key)
        self.assertFalse(is_valid)
        
        # New key should be valid
        is_valid, _, _ = self.manager.validate(new_key)
        self.assertTrue(is_valid)
    
    def test_revoke_key(self):
        """Test revoking an API key."""
        api_key, record = self.manager.create(key_id="test_key")
        
        result = self.manager.revoke("test_key")
        self.assertTrue(result)
        
        is_valid, _, status = self.manager.validate(api_key)
        self.assertFalse(is_valid)
        self.assertEqual(status, KeyStatus.REVOKED)
    
    def test_expired_key(self):
        """Test validating an expired key."""
        # Create a key that expired recently (within grace period)
        api_key, record = self.manager.create(expires_in_days=0, grace_period_seconds=86400)
        
        # Manually set expiry to 1 hour ago (within 24 hour grace period)
        from datetime import datetime, timedelta
        record.expires_at = datetime.utcnow() - timedelta(hours=1)
        self.storage.save(record.key_id, record)
        
        is_valid, _, status = self.manager.validate(api_key)
        
        # Should be in grace period
        self.assertTrue(is_valid)
        self.assertEqual(status, KeyStatus.GRACE_PERIOD)
    
    def test_key_beyond_grace_period(self):
        """Test key beyond grace period."""
        # Create expired key
        api_key, record = self.manager.create(expires_in_days=0)
        
        # Manually set expiry to past grace period
        record.expires_at = datetime.utcnow() - timedelta(days=2)
        self.storage.save(record.key_id, record)
        
        is_valid, _, status = self.manager.validate(api_key)
        
        self.assertFalse(is_valid)
        self.assertEqual(status, KeyStatus.EXPIRED)
    
    def test_list_keys(self):
        """Test listing all keys."""
        self.manager.create()
        self.manager.create()
        
        keys = self.manager.list_keys()
        self.assertEqual(len(keys), 2)
    
    def test_get_key_info(self):
        """Test getting key information."""
        api_key, record = self.manager.create(key_id="test_key")
        
        info = self.manager.get_key_info("test_key")
        
        self.assertIsNotNone(info)
        self.assertEqual(info['key_id'], "test_key")
        self.assertEqual(info['status'], KeyStatus.ACTIVE.value)
    
    def test_rate_limiting_within_limit(self):
        """Test that requests within rate limit are allowed."""
        api_key, _ = self.manager.create()
        
        # Make requests within the limit
        for i in range(50):
            self.assertFalse(self.manager.is_rate_limited(api_key))
            self.manager.increment_usage(api_key)
    
    def test_rate_limiting_exceeds_limit(self):
        """Test that requests exceeding rate limit are blocked."""
        api_key, _ = self.manager.create()
        
        # Exhaust the rate limit (default 100)
        for i in range(100):
            self.manager.increment_usage(api_key)
        
        # Next request should be rate limited
        self.assertTrue(self.manager.is_rate_limited(api_key))
        
        # Should raise exception
        with self.assertRaises(Exception) as context:
            self.manager.increment_usage(api_key)
        self.assertIn("Rate limit exceeded", str(context.exception))
    
    def test_rate_limiting_window_reset(self):
        """Test that rate limit resets after time window."""
        from unittest.mock import patch
        from datetime import datetime, timedelta
        
        api_key, _ = self.manager.create()
        
        # Exhaust the rate limit
        for i in range(100):
            self.manager.increment_usage(api_key)
        
        self.assertTrue(self.manager.is_rate_limited(api_key))
        
        # Mock time to simulate passing of 1+ minutes
        future_time = datetime.utcnow() + timedelta(minutes=2)
        with patch('mira.core.api_key_manager.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = future_time
            
            # Should not be rate limited after window reset
            self.assertFalse(self.manager.is_rate_limited(api_key))
    
    def test_rate_limiting_custom_limit(self):
        """Test custom rate limit value."""
        custom_manager = APIKeyManager(self.storage, rate_limit=10)
        api_key, _ = custom_manager.create()
        
        # Exhaust the custom limit (10)
        for i in range(10):
            custom_manager.increment_usage(api_key)
        
        # Should be rate limited
        self.assertTrue(custom_manager.is_rate_limited(api_key))


class TestFileAPIKeyStorage(unittest.TestCase):
    """Test cases for file-based API key storage."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.storage = FileAPIKeyStorage(self.temp_file.name)
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_save_and_get(self):
        """Test saving and retrieving a key."""
        record = APIKeyRecord(
            key_id="test_key",
            key_hash="test_hash",
            created_at=datetime.utcnow()
        )
        
        self.storage.save("test_key", record)
        retrieved = self.storage.get("test_key")
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.key_id, "test_key")
        self.assertEqual(retrieved.key_hash, "test_hash")
    
    def test_delete(self):
        """Test deleting a key."""
        record = APIKeyRecord(
            key_id="test_key",
            key_hash="test_hash",
            created_at=datetime.utcnow()
        )
        
        self.storage.save("test_key", record)
        result = self.storage.delete("test_key")
        
        self.assertTrue(result)
        self.assertIsNone(self.storage.get("test_key"))
    
    def test_list_all(self):
        """Test listing all keys."""
        record1 = APIKeyRecord(key_id="key1", key_hash="hash1", created_at=datetime.utcnow())
        record2 = APIKeyRecord(key_id="key2", key_hash="hash2", created_at=datetime.utcnow())
        
        self.storage.save("key1", record1)
        self.storage.save("key2", record2)
        
        all_records = self.storage.list_all()
        self.assertEqual(len(all_records), 2)


class TestWebhookSecurity(unittest.TestCase):
    """Test cases for webhook security."""
    
    def test_ip_whitelist_check(self):
        """Test IP whitelist validation."""
        config = WebhookSecurityConfig(
            allowed_ips=["192.168.1.0/24", "10.0.0.1"],
            require_ip_whitelist=True,
            require_signature=False
        )
        
        authenticator = WebhookAuthenticator(config)
        
        # Test allowed IP
        is_auth, reason = authenticator.authenticate(
            client_ip="192.168.1.100",
            payload=b"test"
        )
        self.assertTrue(is_auth)
        
        # Test blocked IP
        is_auth, reason = authenticator.authenticate(
            client_ip="203.0.113.1",
            payload=b"test"
        )
        self.assertFalse(is_auth)
        self.assertEqual(reason, AuthFailureReason.AUTH_IP_BLOCKED)
    
    def test_signature_verification(self):
        """Test HMAC signature verification."""
        secret = "test_secret"
        config = WebhookSecurityConfig(
            secret_key=secret,
            require_signature=True,
            require_ip_whitelist=False
        )
        
        authenticator = WebhookAuthenticator(config)
        payload = b"test payload"
        
        # Create valid signature
        signature = 'sha256=' + hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Test valid signature
        is_auth, reason = authenticator.authenticate(
            client_ip="127.0.0.1",
            payload=payload,
            signature_header=signature
        )
        self.assertTrue(is_auth)
        
        # Test invalid signature
        is_auth, reason = authenticator.authenticate(
            client_ip="127.0.0.1",
            payload=payload,
            signature_header="invalid"
        )
        self.assertFalse(is_auth)
        self.assertEqual(reason, AuthFailureReason.AUTH_SIGNATURE_INVALID)
    
    def test_secret_header_check(self):
        """Test secret header validation."""
        secret = "test_secret"
        config = WebhookSecurityConfig(
            secret_key=secret,
            require_secret=True,
            require_signature=False,
            require_ip_whitelist=False
        )
        
        authenticator = WebhookAuthenticator(config)
        
        # Test valid secret
        is_auth, reason = authenticator.authenticate(
            client_ip="127.0.0.1",
            payload=b"test",
            secret_header=secret
        )
        self.assertTrue(is_auth)
        
        # Test invalid secret
        is_auth, reason = authenticator.authenticate(
            client_ip="127.0.0.1",
            payload=b"test",
            secret_header="wrong_secret"
        )
        self.assertFalse(is_auth)
        self.assertEqual(reason, AuthFailureReason.AUTH_SECRET_MISMATCH)
    
    def test_authentication_pipeline(self):
        """Test full authentication pipeline."""
        secret = "test_secret"
        config = WebhookSecurityConfig(
            secret_key=secret,
            allowed_ips=["127.0.0.0/8"],
            require_ip_whitelist=True,
            require_secret=True,
            require_signature=True
        )
        
        authenticator = WebhookAuthenticator(config)
        payload = b"test payload"
        
        signature = 'sha256=' + hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Test all valid
        is_auth, reason = authenticator.authenticate(
            client_ip="127.0.0.1",
            payload=payload,
            signature_header=signature,
            secret_header=secret
        )
        self.assertTrue(is_auth)
        self.assertEqual(reason, AuthFailureReason.AUTH_SUCCESS)
        
        # Test blocked IP (should fail at IP check)
        is_auth, reason = authenticator.authenticate(
            client_ip="203.0.113.1",
            payload=payload,
            signature_header=signature,
            secret_header=secret
        )
        self.assertFalse(is_auth)
        self.assertEqual(reason, AuthFailureReason.AUTH_IP_BLOCKED)
    
    def test_invalid_cidr_config(self):
        """Test that invalid CIDR raises error at startup."""
        with self.assertRaises(ValueError):
            WebhookSecurityConfig(
                allowed_ips=["invalid_ip"],
                require_ip_whitelist=True
            )
    
    def test_timestamp_validation_valid(self):
        """Test timestamp validation with valid recent timestamp."""
        config = WebhookSecurityConfig(require_signature=False, require_ip_whitelist=False)
        authenticator = WebhookAuthenticator(config, timestamp_window_seconds=300)
        
        # Create a recent timestamp (within window)
        recent_timestamp = datetime.utcnow().isoformat()
        
        is_valid = authenticator.validate_signature_timestamp(recent_timestamp)
        self.assertTrue(is_valid)
    
    def test_timestamp_validation_expired(self):
        """Test timestamp validation with expired timestamp."""
        config = WebhookSecurityConfig(require_signature=False, require_ip_whitelist=False)
        authenticator = WebhookAuthenticator(config, timestamp_window_seconds=300)
        
        # Create an old timestamp (beyond window)
        old_timestamp = (datetime.utcnow() - timedelta(seconds=400)).isoformat()
        
        is_valid = authenticator.validate_signature_timestamp(old_timestamp)
        self.assertFalse(is_valid)
    
    def test_timestamp_validation_malformed(self):
        """Test timestamp validation with malformed timestamp."""
        config = WebhookSecurityConfig(require_signature=False, require_ip_whitelist=False)
        authenticator = WebhookAuthenticator(config, timestamp_window_seconds=300)
        
        is_valid = authenticator.validate_signature_timestamp("not-a-timestamp")
        self.assertFalse(is_valid)
    
    def test_timestamp_validation_future(self):
        """Test timestamp validation with future timestamp."""
        config = WebhookSecurityConfig(require_signature=False, require_ip_whitelist=False)
        authenticator = WebhookAuthenticator(config, timestamp_window_seconds=300)
        
        # Create a future timestamp
        future_timestamp = (datetime.utcnow() + timedelta(seconds=100)).isoformat()
        
        is_valid = authenticator.validate_signature_timestamp(future_timestamp)
        self.assertFalse(is_valid)
    
    def test_authenticate_with_valid_timestamp(self):
        """Test authentication with valid timestamp header."""
        config = WebhookSecurityConfig(
            require_signature=False,
            require_ip_whitelist=False
        )
        authenticator = WebhookAuthenticator(config, timestamp_window_seconds=300)
        
        recent_timestamp = datetime.utcnow().isoformat()
        
        is_auth, reason = authenticator.authenticate(
            client_ip="127.0.0.1",
            payload=b"test",
            timestamp_header=recent_timestamp
        )
        self.assertTrue(is_auth)
    
    def test_authenticate_with_expired_timestamp(self):
        """Test authentication rejects expired timestamp."""
        config = WebhookSecurityConfig(
            require_signature=False,
            require_ip_whitelist=False
        )
        authenticator = WebhookAuthenticator(config, timestamp_window_seconds=300)
        
        old_timestamp = (datetime.utcnow() - timedelta(seconds=400)).isoformat()
        
        is_auth, reason = authenticator.authenticate(
            client_ip="127.0.0.1",
            payload=b"test",
            timestamp_header=old_timestamp
        )
        self.assertFalse(is_auth)
        self.assertEqual(reason, AuthFailureReason.AUTH_SIGNATURE_INVALID)


if __name__ == '__main__':
    unittest.main()


class TestConcurrentFailureHandling(unittest.TestCase):
    """Test concurrent operations with intentional failures."""
    
    def test_concurrent_api_key_validation(self):
        """Test API key validation under concurrent load with failures."""
        from concurrent.futures import ThreadPoolExecutor
        import random
        
        storage = InMemoryAPIKeyStorage()
        manager = APIKeyManager(storage, default_expiry_days=90)
        
        # Create some valid keys
        valid_keys = []
        for i in range(5):
            api_key, _ = manager.create()
            valid_keys.append(api_key)
        
        def validate_with_random_failures(key_index):
            """Validate keys with random failures."""
            try:
                # Randomly use valid or invalid keys
                if random.choice([True, False]) and valid_keys:
                    key = valid_keys[key_index % len(valid_keys)]
                else:
                    key = "invalid_key_" + str(random.randint(1000, 9999))
                
                # Randomly raise exceptions
                if random.random() < 0.1:  # 10% failure rate
                    raise Exception("Simulated failure")
                
                is_valid, _, _ = manager.validate(key)
                return "success" if is_valid else "invalid"
            except Exception:
                return "failed"
        
        # Run concurrent validations
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(validate_with_random_failures, range(50)))
        
        # Verify we got a mix of results
        self.assertGreater(results.count("failed"), 0, "Should have some failures")
        self.assertGreater(results.count("success") + results.count("invalid"), 0, "Should have some successes")
        self.assertEqual(len(results), 50, "Should have all 50 results")
    
    def test_concurrent_rate_limiting(self):
        """Test rate limiting under concurrent load."""
        from concurrent.futures import ThreadPoolExecutor
        
        storage = InMemoryAPIKeyStorage()
        manager = APIKeyManager(storage, rate_limit=50)
        
        api_key, _ = manager.create()
        
        def increment_with_handling():
            """Try to increment usage, handle rate limit errors."""
            try:
                manager.increment_usage(api_key)
                return "success"
            except Exception as e:
                if "Rate limit exceeded" in str(e):
                    return "rate_limited"
                return "error"
        
        # Run concurrent increments (more than rate limit)
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(lambda _: increment_with_handling(), range(100)))
        
        # Should have mix of successes and rate limited
        self.assertGreater(results.count("success"), 0, "Should have some successes")
        self.assertGreater(results.count("rate_limited"), 0, "Should hit rate limit")
        self.assertEqual(len(results), 100, "Should have all 100 results")
    
    def test_concurrent_webhook_authentication(self):
        """Test webhook authentication under concurrent load."""
        from concurrent.futures import ThreadPoolExecutor
        import random
        
        config = WebhookSecurityConfig(
            require_signature=False,
            require_ip_whitelist=False
        )
        authenticator = WebhookAuthenticator(config)
        
        def authenticate_with_random_failures():
            """Authenticate with random failures."""
            try:
                # Randomly raise exceptions
                if random.random() < 0.05:  # 5% failure rate
                    raise Exception("Simulated network failure")
                
                is_auth, reason = authenticator.authenticate(
                    client_ip="127.0.0.1",
                    payload=b"test payload"
                )
                return "success" if is_auth else "failed"
            except Exception:
                return "error"
        
        # Run concurrent authentications
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(lambda _: authenticate_with_random_failures(), range(50)))
        
        # Verify we got results
        self.assertGreater(results.count("success"), 0, "Should have some successes")
        self.assertEqual(len(results), 50, "Should have all 50 results")
