"""Tests for webhook handler functionality."""
import unittest
import json
import os
import tempfile
from mira.core.webhook_handler import WebhookHandler


class TestWebhookHandler(unittest.TestCase):
    """Test cases for WebhookHandler."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = WebhookHandler(secret_key='test-secret')
        self.test_data = {'test': 'data', 'value': 123}
        
    def test_handler_initialization(self):
        """Test webhook handler initialization."""
        self.assertIsNotNone(self.handler.app)
        self.assertEqual(self.handler.secret_key, 'test-secret')
        self.assertIsInstance(self.handler.handlers, dict)
        self.assertIsInstance(self.handler.operator_keys, set)
        
    def test_generate_operator_key(self):
        """Test operator key generation."""
        key = self.handler.generate_operator_key()
        self.assertTrue(key.startswith('op_'))
        self.assertEqual(len(key), 35)  # 'op_' + 32 hex chars
        self.assertIn(key, self.handler.operator_keys)
        
    def test_verify_operator_key_valid(self):
        """Test verification of valid operator key."""
        key = self.handler.generate_operator_key()
        self.assertTrue(self.handler._verify_operator_key(key))
        
    def test_verify_operator_key_invalid(self):
        """Test verification of invalid operator key."""
        self.assertFalse(self.handler._verify_operator_key('invalid-key'))
        
    def test_register_handler(self):
        """Test registering a webhook handler."""
        def test_handler(data):
            return {'status': 'ok', 'data': data}
            
        self.handler.register_handler('test_service', test_handler)
        self.assertIn('test_service', self.handler.handlers)
        self.assertEqual(self.handler.handlers['test_service'], test_handler)
        
    def test_webhook_with_valid_operator_key(self):
        """Test webhook endpoint with valid operator key."""
        def mock_handler(data):
            return {'status': 'processed', 'data': data}
            
        self.handler.register_handler('test', mock_handler)
        key = self.handler.generate_operator_key()
        
        with self.handler.app.test_client() as client:
            response = client.post(
                '/webhook/test',
                json=self.test_data,
                headers={'X-Operator-Key': key}
            )
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['status'], 'processed')
            
    def test_webhook_with_invalid_operator_key(self):
        """Test webhook endpoint with invalid operator key."""
        def mock_handler(data):
            return {'status': 'processed'}
            
        self.handler.register_handler('test', mock_handler)
        
        with self.handler.app.test_client() as client:
            response = client.post(
                '/webhook/test',
                json=self.test_data,
                headers={'X-Operator-Key': 'invalid-key'}
            )
            self.assertEqual(response.status_code, 403)
            data = json.loads(response.data)
            self.assertIn('error', data)
            
    def test_webhook_without_operator_key(self):
        """Test webhook endpoint without operator key."""
        def mock_handler(data):
            return {'status': 'processed'}
            
        self.handler.register_handler('test', mock_handler)
        
        with self.handler.app.test_client() as client:
            response = client.post(
                '/webhook/test',
                json=self.test_data
            )
            self.assertEqual(response.status_code, 200)
            
    def test_webhook_unknown_service(self):
        """Test webhook with unknown service."""
        key = self.handler.generate_operator_key()
        
        with self.handler.app.test_client() as client:
            response = client.post(
                '/webhook/unknown',
                json=self.test_data,
                headers={'X-Operator-Key': key}
            )
            self.assertEqual(response.status_code, 404)
            data = json.loads(response.data)
            self.assertIn('error', data)
            
    def test_webhook_with_signature_verification(self):
        """Test webhook with signature verification."""
        import hmac
        import hashlib
        
        def mock_handler(data):
            return {'status': 'processed'}
            
        self.handler.register_handler('test', mock_handler)
        payload = json.dumps(self.test_data).encode()
        signature = 'sha256=' + hmac.new(
            b'test-secret',
            payload,
            hashlib.sha256
        ).hexdigest()
        
        with self.handler.app.test_client() as client:
            response = client.post(
                '/webhook/test',
                data=payload,
                content_type='application/json',
                headers={'X-Hub-Signature-256': signature}
            )
            self.assertEqual(response.status_code, 200)
            
    def test_webhook_with_invalid_signature(self):
        """Test webhook with invalid signature."""
        def mock_handler(data):
            return {'status': 'processed'}
            
        self.handler.register_handler('test', mock_handler)
        payload = json.dumps(self.test_data).encode()
        
        with self.handler.app.test_client() as client:
            response = client.post(
                '/webhook/test',
                data=payload,
                content_type='application/json',
                headers={'X-Hub-Signature-256': 'sha256=invalid'}
            )
            self.assertEqual(response.status_code, 403)
            
    def test_health_check_endpoint(self):
        """Test health check endpoint."""
        with self.handler.app.test_client() as client:
            response = client.get('/health')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['status'], 'healthy')
            self.assertEqual(data['service'], 'mira-webhook')
            
    def test_webhook_handler_exception(self):
        """Test webhook handler with exception."""
        def failing_handler(data):
            raise ValueError("Test error")
            
        self.handler.register_handler('test', failing_handler)
        key = self.handler.generate_operator_key()
        
        with self.handler.app.test_client() as client:
            response = client.post(
                '/webhook/test',
                json=self.test_data,
                headers={'X-Operator-Key': key}
            )
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.data)
            self.assertIn('error', data)
            
    def test_load_operator_keys_from_env(self):
        """Test loading operator keys from environment."""
        os.environ['OPERATOR_KEYS'] = 'key1,key2,key3'
        handler = WebhookHandler()
        self.assertIn('key1', handler.operator_keys)
        self.assertIn('key2', handler.operator_keys)
        self.assertIn('key3', handler.operator_keys)
        del os.environ['OPERATOR_KEYS']
        
    def test_load_operator_keys_from_file(self):
        """Test loading operator keys from file."""
        # Create a temporary config directory and file
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = os.path.join(tmpdir, 'config')
            os.makedirs(config_dir, exist_ok=True)
            keys_file = os.path.join(config_dir, 'operator_keys.txt')
            
            with open(keys_file, 'w') as f:
                f.write('file_key1\n')
                f.write('file_key2\n')
                f.write('# This is a comment\n')
                f.write('file_key3\n')
            
            # Temporarily change the keys file path
            original_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'operator_keys.txt')
            if os.path.exists(original_file):
                os.rename(original_file, original_file + '.bak')
            
            # Create the config directory for the handler
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config')
            os.makedirs(config_path, exist_ok=True)
            os.rename(keys_file, os.path.join(config_path, 'operator_keys.txt'))
            
            try:
                handler = WebhookHandler()
                self.assertIn('file_key1', handler.operator_keys)
                self.assertIn('file_key2', handler.operator_keys)
                self.assertIn('file_key3', handler.operator_keys)
            finally:
                # Cleanup
                test_keys_file = os.path.join(config_path, 'operator_keys.txt')
                if os.path.exists(test_keys_file):
                    os.remove(test_keys_file)
                if os.path.exists(original_file + '.bak'):
                    os.rename(original_file + '.bak', original_file)


if __name__ == '__main__':
    unittest.main()
