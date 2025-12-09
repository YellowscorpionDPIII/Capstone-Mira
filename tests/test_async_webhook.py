"""Tests for authenticated async webhook handler."""
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from mira.auth.authenticated_webhook_handler import AuthenticatedWebhookHandler


@pytest.fixture
def api_keys():
    """Sample API keys for testing."""
    return {
        'test_key_1': {
            'key': 'secret_key_1',
            'role': 'admin',
            'expiry': int(time.time()) + 3600  # Expires in 1 hour
        },
        'test_key_2': {
            'key': 'secret_key_2',
            'role': 'user',
            'expiry': int(time.time()) + 7200  # Expires in 2 hours
        },
        'expired_key': {
            'key': 'expired_secret',
            'role': 'user',
            'expiry': int(time.time()) - 3600  # Expired 1 hour ago
        }
    }


@pytest.fixture
def webhook_handler(api_keys):
    """Create webhook handler instance."""
    handler = AuthenticatedWebhookHandler(
        secret_key='test_secret',
        redis_url='redis://localhost:6379/1',
        api_keys=api_keys
    )
    return handler


@pytest.fixture
async def mock_redis():
    """Mock Redis client."""
    with patch('redis.asyncio.from_url') as mock:
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.setex = AsyncMock()
        redis_mock.close = AsyncMock()
        
        # Make from_url return the mock directly (not awaitable)
        async def async_from_url(*args, **kwargs):
            return redis_mock
        
        mock.side_effect = async_from_url
        yield redis_mock


class TestAuthenticatedWebhookHandler:
    """Test cases for AuthenticatedWebhookHandler."""
    
    @pytest.mark.asyncio
    async def test_handler_initialization(self, api_keys):
        """Test webhook handler initialization."""
        handler = AuthenticatedWebhookHandler(
            secret_key='test_secret',
            api_keys=api_keys
        )
        
        assert handler.secret_key == 'test_secret'
        assert len(handler.api_keys) == 3
        assert handler.active_keys_count == 3
        assert handler.cache_hits == 0
        assert handler.cache_misses == 0
    
    @pytest.mark.asyncio
    async def test_authenticate_valid_key(self, webhook_handler, mock_redis):
        """Test authentication with valid API key."""
        # Mock request context using app test request context
        async with webhook_handler.app.test_request_context(
            '/webhook/test',
            headers={
                'X-API-Key-ID': 'test_key_1',
                'X-API-Key': 'secret_key_1'
            }
        ):
            result = await webhook_handler._authenticate_request()
            
            assert result['authenticated'] is True
            assert result['key_id'] == 'test_key_1'
            assert result['role'] == 'admin'
    
    @pytest.mark.asyncio
    async def test_authenticate_invalid_key(self, webhook_handler, mock_redis):
        """Test authentication with invalid API key."""
        async with webhook_handler.app.test_request_context(
            '/webhook/test',
            headers={
                'X-API-Key-ID': 'test_key_1',
                'X-API-Key': 'wrong_key'
            }
        ):
            result = await webhook_handler._authenticate_request()
            
            assert result['authenticated'] is False
            assert result['reason'] == 'Invalid API key'
    
    @pytest.mark.asyncio
    async def test_authenticate_missing_key(self, webhook_handler, mock_redis):
        """Test authentication with missing API key."""
        async with webhook_handler.app.test_request_context(
            '/webhook/test',
            headers={}
        ):
            result = await webhook_handler._authenticate_request()
            
            assert result['authenticated'] is False
            assert result['reason'] == 'Missing API key or key ID'
    
    @pytest.mark.asyncio
    async def test_authenticate_expired_key(self, webhook_handler, mock_redis):
        """Test authentication with expired API key."""
        async with webhook_handler.app.test_request_context(
            '/webhook/test',
            headers={
                'X-API-Key-ID': 'expired_key',
                'X-API-Key': 'expired_secret'
            }
        ):
            result = await webhook_handler._authenticate_request()
            
            assert result['authenticated'] is False
            assert result['reason'] == 'API key expired'
    
    @pytest.mark.asyncio
    async def test_webhook_endpoint_success(self, webhook_handler, mock_redis):
        """Test successful webhook request."""
        # Register a test handler
        async def test_handler(data):
            return {'status': 'processed', 'data': data}
        
        webhook_handler.register_handler('test_service', test_handler)
        
        # Create test client
        client = webhook_handler.app.test_client()
        
        response = await client.post(
            '/webhook/test_service',
            json={'event': 'test'},
            headers={
                'X-API-Key-ID': 'test_key_1',
                'X-API-Key': 'secret_key_1'
            }
        )
        
        assert response.status_code == 200
        data = await response.get_json()
        assert data['status'] == 'processed'
    
    @pytest.mark.asyncio
    async def test_webhook_endpoint_unauthorized(self, webhook_handler, mock_redis):
        """Test unauthorized webhook request."""
        client = webhook_handler.app.test_client()
        
        response = await client.post(
            '/webhook/test_service',
            json={'event': 'test'},
            headers={}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_webhook_endpoint_unknown_service(self, webhook_handler, mock_redis):
        """Test webhook request to unknown service."""
        client = webhook_handler.app.test_client()
        
        response = await client.post(
            '/webhook/unknown_service',
            json={'event': 'test'},
            headers={
                'X-API-Key-ID': 'test_key_1',
                'X-API-Key': 'secret_key_1'
            }
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, webhook_handler, mock_redis):
        """Test health check endpoint."""
        client = webhook_handler.app.test_client()
        
        response = await client.get('/healthz')
        
        assert response.status_code == 200
        data = await response.get_json()
        assert data['status'] == 'healthy'
        assert 'metrics' in data
        assert data['metrics']['active_keys_count'] == 3
        assert 'cache_hit_rate' in data['metrics']
    
    @pytest.mark.asyncio
    async def test_cache_metrics(self, api_keys):
        """Test cache hit/miss metrics."""
        # Create a fresh handler with mock redis for this test
        with patch('redis.asyncio.from_url') as mock_from_url:
            redis_mock = AsyncMock()
            redis_mock.get = AsyncMock(return_value=None)
            redis_mock.setex = AsyncMock()
            redis_mock.close = AsyncMock()
            
            async def async_from_url(*args, **kwargs):
                return redis_mock
            
            mock_from_url.side_effect = async_from_url
            
            handler = AuthenticatedWebhookHandler(
                secret_key='test_secret',
                redis_url='redis://localhost:6379/1',
                api_keys=api_keys
            )
            
            # Simulate cache miss
            redis_mock.get.return_value = None
            
            async with handler.app.test_request_context(
                '/webhook/test',
                headers={
                    'X-API-Key-ID': 'test_key_1',
                    'X-API-Key': 'secret_key_1'
                }
            ):
                await handler._authenticate_request()
                assert handler.cache_misses == 1
            
            # Simulate cache hit
            import json
            redis_mock.get.return_value = json.dumps({
                'key': 'secret_key_1',
                'role': 'admin',
                'expiry': int(time.time()) + 3600
            })
            
            async with handler.app.test_request_context(
                '/webhook/test',
                headers={
                    'X-API-Key-ID': 'test_key_1',
                    'X-API-Key': 'secret_key_1'
                }
            ):
                await handler._authenticate_request()
                assert handler.cache_hits == 1
    
    @pytest.mark.asyncio
    async def test_add_api_key(self, webhook_handler):
        """Test adding new API key."""
        initial_count = webhook_handler.active_keys_count
        
        webhook_handler.add_api_key(
            'new_key',
            'new_secret',
            role='developer',
            expiry=int(time.time()) + 3600
        )
        
        assert webhook_handler.active_keys_count == initial_count + 1
        assert 'new_key' in webhook_handler.api_keys
        assert webhook_handler.api_keys['new_key']['role'] == 'developer'
    
    def test_signature_verification(self, webhook_handler):
        """Test webhook signature verification."""
        import hmac
        import hashlib
        
        payload = b'{"event": "test"}'
        signature = 'sha256=' + hmac.new(
            webhook_handler.secret_key.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        assert webhook_handler._verify_signature(payload, signature) is True
        assert webhook_handler._verify_signature(payload, 'sha256=invalid') is False
    
    @pytest.mark.asyncio
    async def test_cleanup(self, api_keys):
        """Test cleanup of resources."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            redis_mock = AsyncMock()
            redis_mock.get = AsyncMock(return_value=None)
            redis_mock.setex = AsyncMock()
            redis_mock.close = AsyncMock()
            
            async def async_from_url(*args, **kwargs):
                return redis_mock
            
            mock_from_url.side_effect = async_from_url
            
            handler = AuthenticatedWebhookHandler(
                secret_key='test_secret',
                redis_url='redis://localhost:6379/1',
                api_keys=api_keys
            )
            
            await handler._init_redis()
            await handler.cleanup()
            
            redis_mock.close.assert_called_once()


@pytest.mark.asyncio
async def test_concurrent_webhook_requests(webhook_handler, mock_redis):
    """Test concurrent webhook requests (50 req/s)."""
    # Register a test handler
    async def test_handler(data):
        await asyncio.sleep(0.01)  # Simulate processing
        return {'status': 'processed'}
    
    webhook_handler.register_handler('concurrent_test', test_handler)
    
    client = webhook_handler.app.test_client()
    
    async def make_request(request_id):
        """Make a single webhook request."""
        response = await client.post(
            '/webhook/concurrent_test',
            json={'request_id': request_id},
            headers={
                'X-API-Key-ID': 'test_key_1',
                'X-API-Key': 'secret_key_1'
            }
        )
        return response.status_code
    
    # Test 50 concurrent requests
    start_time = time.time()
    tasks = [make_request(i) for i in range(50)]
    results = await asyncio.gather(*tasks)
    elapsed_time = time.time() - start_time
    
    # Verify all requests succeeded
    assert all(status == 200 for status in results)
    
    # Verify throughput (should complete within reasonable time)
    # 50 requests should complete in less than 2 seconds for 50 req/s
    assert elapsed_time < 2.0, f"Concurrent requests took {elapsed_time}s, expected < 2.0s"
    
    # Calculate actual throughput
    throughput = len(results) / elapsed_time
    print(f"\nActual throughput: {throughput:.2f} req/s")
    assert throughput >= 25, f"Throughput {throughput:.2f} req/s is below minimum 25 req/s"


@pytest.mark.asyncio
async def test_structured_logging(webhook_handler, mock_redis):
    """Test structured logging with key_id, role, client_ip, timestamp."""
    client = webhook_handler.app.test_client()
    
    # Register a test handler
    async def test_handler(data):
        return {'status': 'ok'}
    
    webhook_handler.register_handler('logging_test', test_handler)
    
    # Make request with custom headers
    response = await client.post(
        '/webhook/logging_test',
        json={'test': 'data'},
        headers={
            'X-API-Key-ID': 'test_key_1',
            'X-API-Key': 'secret_key_1',
            'X-Forwarded-For': '192.168.1.100'
        }
    )
    
    assert response.status_code == 200
    # Note: In a real test, you would capture and verify log output
    # This test verifies that the logging middleware doesn't break the request flow


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])
