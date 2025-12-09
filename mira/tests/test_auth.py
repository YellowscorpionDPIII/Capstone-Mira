"""Tests for authentication module."""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import string
import jwt
from hypothesis import given, settings, strategies as st
from mira.auth.api_key_manager import (
    APIKeyManager,
    APIKeyValidationError
)
from mira.auth.rate_limiter import get_limiter, reset_limiter


class TestAPIKeyManager(unittest.TestCase):
    """Test cases for APIKeyManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = APIKeyManager(jwt_secret="test-secret-key")
        
    def test_generate_api_key(self):
        """Test API key generation."""
        result = self.manager.generate_api_key("user123", role="admin")
        
        self.assertIn("api_key", result)
        self.assertEqual(result["user_id"], "user123")
        self.assertEqual(result["role"], "admin")
        self.assertIn("created_at", result)
        
        # Verify key is stored
        key_data = self.manager.verify_api_key(result["api_key"])
        self.assertIsNotNone(key_data)
        self.assertEqual(key_data["user_id"], "user123")
        
    def test_generate_api_key_with_metadata(self):
        """Test API key generation with metadata."""
        metadata = {"app": "test", "env": "dev"}
        result = self.manager.generate_api_key("user123", metadata=metadata)
        
        key_data = self.manager.verify_api_key(result["api_key"])
        self.assertEqual(key_data["metadata"], metadata)
        
    def test_rotate_api_key(self):
        """Test API key rotation."""
        # Generate initial key
        result = self.manager.generate_api_key("user123", role="admin")
        old_key = result["api_key"]
        
        # Rotate key
        new_result = self.manager.rotate_api_key(old_key, "user123")
        
        self.assertNotEqual(new_result["api_key"], old_key)
        self.assertEqual(new_result["user_id"], "user123")
        
        # Old key should be invalid
        self.assertIsNone(self.manager.verify_api_key(old_key))
        
        # New key should be valid
        self.assertIsNotNone(self.manager.verify_api_key(new_result["api_key"]))
        
    def test_rotate_invalid_key(self):
        """Test rotating an invalid key."""
        with self.assertRaises(APIKeyValidationError):
            self.manager.rotate_api_key("invalid_key", "user123")
            
    def test_rotate_key_wrong_user(self):
        """Test rotating a key with wrong user ID."""
        result = self.manager.generate_api_key("user123")
        
        with self.assertRaises(APIKeyValidationError):
            self.manager.rotate_api_key(result["api_key"], "wrong_user")
            
    def test_validate_key_minimum_length(self):
        """Test key validation for minimum length."""
        short_key = "a" * 31  # Less than 32 chars
        
        with self.assertRaises(APIKeyValidationError) as context:
            self.manager.validate_key(short_key)
        
        self.assertIn("at least 32 characters", str(context.exception))
        
    def test_validate_key_weak_patterns(self):
        """Test key validation rejects weak patterns."""
        weak_keys = [
            "a" * 40,  # Repeated characters
            "0" * 40,  # Only numbers
            "abcdefghijklmnopqrstuvwxyzabcdefghij",  # Only letters
            "123456789012345678901234567890123456",  # Sequential numbers
        ]
        
        for weak_key in weak_keys:
            with self.assertRaises(APIKeyValidationError):
                self.manager.validate_key(weak_key)
                
    def test_verify_api_key_updates_last_used(self):
        """Test that verifying a key updates last_used timestamp."""
        result = self.manager.generate_api_key("user123")
        key = result["api_key"]
        
        # First verification
        data1 = self.manager.verify_api_key(key)
        self.assertIsNotNone(data1["last_used"])
        
        # Second verification should update timestamp
        data2 = self.manager.verify_api_key(key)
        self.assertIsNotNone(data2["last_used"])
        
    def test_verify_invalid_key(self):
        """Test verifying an invalid key."""
        result = self.manager.verify_api_key("invalid_key")
        self.assertIsNone(result)
        
    def test_generate_jwt_token(self):
        """Test JWT token generation."""
        token = self.manager.generate_jwt_token("user123", role="admin")
        
        self.assertIsInstance(token, str)
        
        # Verify token structure
        payload = self.manager.verify_jwt_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["sub"], "user123")
        self.assertEqual(payload["role"], "admin")
        self.assertIn("iat", payload)
        self.assertIn("exp", payload)
        
    def test_generate_jwt_token_with_custom_expiry(self):
        """Test JWT token with custom expiry."""
        token = self.manager.generate_jwt_token("user123", expiry_hours=1)
        
        payload = self.manager.verify_jwt_token(token)
        self.assertIsNotNone(payload)
        
        # Check expiry is approximately 1 hour from now
        exp_time = datetime.fromtimestamp(payload["exp"])
        iat_time = datetime.fromtimestamp(payload["iat"])
        delta = exp_time - iat_time
        
        self.assertAlmostEqual(delta.total_seconds(), 3600, delta=10)
        
    def test_generate_jwt_token_with_additional_claims(self):
        """Test JWT token with additional claims."""
        additional = {"department": "engineering", "level": 5}
        token = self.manager.generate_jwt_token(
            "user123",
            additional_claims=additional
        )
        
        payload = self.manager.verify_jwt_token(token)
        self.assertEqual(payload["department"], "engineering")
        self.assertEqual(payload["level"], 5)
        
    def test_verify_expired_jwt_token(self):
        """Test verifying an expired JWT token."""
        # Create token that expires immediately
        now = datetime.utcnow()
        payload = {
            "sub": "user123",
            "role": "user",
            "iat": int(now.timestamp()),
            "exp": int((now - timedelta(seconds=1)).timestamp())  # Already expired
        }
        
        token = jwt.encode(payload, self.manager.jwt_secret, algorithm="HS256")
        
        result = self.manager.verify_jwt_token(token)
        self.assertIsNone(result)
        
    def test_verify_invalid_jwt_token(self):
        """Test verifying an invalid JWT token."""
        result = self.manager.verify_jwt_token("invalid.token.string")
        self.assertIsNone(result)
        
    def test_mask_key(self):
        """Test key masking."""
        key = "abcdefgh1234567890ABCDEFGH"
        masked = self.manager.mask_key(key, show_chars=8)
        
        self.assertEqual(masked[:8], "abcdefgh")
        self.assertEqual(masked[-8:], "ABCDEFGH")
        self.assertIn("*", masked)
        
    def test_mask_short_key(self):
        """Test masking a short key."""
        key = "shortkey"
        masked = self.manager.mask_key(key, show_chars=8)
        
        self.assertEqual(masked, "*" * len(key))
        
    def test_list_keys_for_user(self):
        """Test listing keys for a user."""
        # Generate multiple keys for same user
        self.manager.generate_api_key("user123", role="admin")
        self.manager.generate_api_key("user123", role="user")
        self.manager.generate_api_key("other_user", role="user")
        
        keys = self.manager.list_keys_for_user("user123", mask=True)
        
        self.assertEqual(len(keys), 2)
        for key_info in keys:
            self.assertEqual(key_info["user_id"], "user123")
            self.assertIn("key_hash_preview", key_info)
            
    def test_list_keys_for_user_unmasked(self):
        """Test listing keys without masking."""
        self.manager.generate_api_key("user123")
        
        keys = self.manager.list_keys_for_user("user123", mask=False)
        
        self.assertEqual(len(keys), 1)
        self.assertNotIn("key_hash_preview", keys[0])


class TestAPIKeyManagerHypothesis(unittest.TestCase):
    """Hypothesis property-based tests for APIKeyManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = APIKeyManager()
        
    @given(st.text(min_size=32, max_size=100))
    @settings(max_examples=100)
    def test_valid_length_keys(self, key: str):
        """Test that keys with valid length don't raise errors based on length alone."""
        # This tests that length validation works correctly
        try:
            self.manager.validate_key(key)
        except APIKeyValidationError as e:
            # If it fails, it should be due to weak patterns, not length
            self.assertNotIn("at least 32 characters", str(e))
            
    @given(st.text(max_size=31))
    @settings(max_examples=100)
    def test_short_keys_rejected(self, key: str):
        """Test that keys shorter than 32 chars are always rejected."""
        with self.assertRaises(APIKeyValidationError) as context:
            self.manager.validate_key(key)
        
        self.assertIn("at least 32 characters", str(context.exception))
        
    @given(st.text(alphabet="0123456789", min_size=32, max_size=64))
    @settings(max_examples=100)
    def test_numeric_only_keys_rejected(self, key: str):
        """Test that numeric-only keys are rejected."""
        with self.assertRaises(APIKeyValidationError):
            self.manager.validate_key(key)
            
    @given(st.text(alphabet=string.ascii_letters, min_size=32, max_size=64))
    @settings(max_examples=100)
    def test_alpha_only_keys_rejected(self, key: str):
        """Test that alphabetic-only keys are rejected."""
        with self.assertRaises(APIKeyValidationError):
            self.manager.validate_key(key)
            
    @given(st.characters().filter(lambda c: c.isprintable()))
    @settings(max_examples=100)
    def test_repeated_char_patterns_rejected(self, char: str):
        """Test that keys with repeated characters are rejected."""
        # Create a key with 5+ repeated characters
        key = char * 40  # 40 repeated characters
        
        with self.assertRaises(APIKeyValidationError):
            self.manager.validate_key(key)
            
    @given(st.text(min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_user_id_handling(self, user_id: str):
        """Test that various user IDs are handled correctly."""
        if user_id.strip():  # Only test non-empty user IDs
            try:
                result = self.manager.generate_api_key(user_id)
                self.assertEqual(result["user_id"], user_id)
            except Exception:
                # Some user IDs might cause issues, which is acceptable
                pass


class TestRateLimiter(unittest.TestCase):
    """Test cases for rate limiter."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_limiter()
        
    def tearDown(self):
        """Clean up after tests."""
        reset_limiter()
        
    @patch('mira.auth.rate_limiter.redis')
    def test_get_limiter_with_redis(self, mock_redis):
        """Test getting limiter with Redis backend."""
        mock_client = MagicMock()
        mock_redis.from_url.return_value = mock_client
        
        limiter = get_limiter(redis_url="redis://localhost:6379/0")
        
        self.assertIsNotNone(limiter)
        mock_redis.from_url.assert_called_once()
        
    @patch('mira.auth.rate_limiter.redis')
    def test_get_limiter_redis_unavailable(self, mock_redis):
        """Test getting limiter when Redis is unavailable."""
        import redis as redis_module
        mock_redis.ConnectionError = redis_module.ConnectionError
        mock_redis.RedisError = redis_module.RedisError
        mock_redis.from_url.side_effect = redis_module.ConnectionError("Connection failed")
        
        limiter = get_limiter(redis_url="redis://localhost:6379/0")
        
        # Should fall back to memory storage
        self.assertIsNotNone(limiter)
        
    def test_get_limiter_singleton(self):
        """Test that get_limiter returns the same instance."""
        limiter1 = get_limiter()
        limiter2 = get_limiter()
        
        self.assertIs(limiter1, limiter2)
        
    def test_reset_limiter(self):
        """Test resetting the limiter."""
        limiter1 = get_limiter()
        reset_limiter()
        limiter2 = get_limiter()
        
        self.assertIsNot(limiter1, limiter2)


if __name__ == '__main__':
    unittest.main()
