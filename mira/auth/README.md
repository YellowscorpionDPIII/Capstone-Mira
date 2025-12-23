# Authentication Module

This module provides comprehensive API key management and JWT token authentication for the Mira platform.

## Features

- **API Key Management**: Generate, rotate, and validate API keys
- **JWT Token Support**: Generate and verify JWT tokens with custom claims
- **Rate Limiting**: Redis-backed rate limiting (with memory fallback)
- **Key Validation**: Strong validation rejecting weak patterns
- **Key Masking**: Secure display of key hashes for admin endpoints
- **Security**: Cryptographically secure key generation using Python's `secrets` module

## Installation

Dependencies are automatically installed with the main Mira package:

```bash
pip install -r requirements.txt
```

Required packages:
- `Flask>=3.0.0`
- `Flask-Limiter>=3.5.0`
- `PyJWT>=2.8.0`
- `redis>=5.0.0`
- `hypothesis>=6.92.0` (for testing)

## Usage

### Basic Setup

```python
from mira.auth.api_key_manager import APIKeyManager
from mira.auth.rate_limiter import get_limiter
from flask import Flask

app = Flask(__name__)

# Initialize rate limiter with Redis (falls back to memory if Redis unavailable)
limiter = get_limiter(app, redis_url="redis://localhost:6379/0")

# Initialize API key manager
api_key_manager = APIKeyManager(
    jwt_secret="your-secret-key-here",  # Use environment variable in production
    jwt_algorithm="HS256",
    default_token_expiry_hours=24
)
```

### Generating API Keys

```python
# Generate a new API key
result = api_key_manager.generate_api_key(
    user_id="user123",
    role="admin",
    metadata={"app": "myapp", "env": "production"}
)

# Returns: {
#     "api_key": "secure-random-key-here...",
#     "user_id": "user123",
#     "role": "admin",
#     "created_at": "2024-01-01T00:00:00"
# }
```

### Rotating API Keys

```python
# Rotate an existing key
new_result = api_key_manager.rotate_api_key(
    old_key="existing-api-key",
    user_id="user123"
)
```

### Verifying API Keys

```python
# Verify an API key
key_data = api_key_manager.verify_api_key("api-key-to-verify")

if key_data:
    user_id = key_data["user_id"]
    role = key_data["role"]
    print(f"Valid key for user {user_id} with role {role}")
else:
    print("Invalid key")
```

### JWT Tokens

```python
# Generate a JWT token
token = api_key_manager.generate_jwt_token(
    user_id="user123",
    role="admin",
    expiry_hours=24,
    additional_claims={"department": "engineering"}
)

# Verify a JWT token
payload = api_key_manager.verify_jwt_token(token)

if payload:
    print(f"Token valid for user: {payload['sub']}")
    print(f"Role: {payload['role']}")
    print(f"Expires at: {payload['exp']}")
else:
    print("Invalid or expired token")
```

### Rate Limiting

Apply rate limiting to Flask endpoints:

```python
@app.route('/api/keys/generate', methods=['POST'])
@limiter.limit("10 per minute")  # 10 requests per minute per IP
def generate_key():
    # Your endpoint logic here
    pass
```

### Key Masking

```python
# Mask a key for display (shows first/last 8 chars only)
masked = api_key_manager.mask_key("very-long-api-key-here", show_chars=8)
# Returns: "very-lon**********key-here"

# List keys for a user with masking
keys = api_key_manager.list_keys_for_user("user123", mask=True)
```

## Security Features

### Key Validation

The system validates all generated keys against:

1. **Minimum Length**: Keys must be at least 32 characters
2. **Weak Patterns**: Rejects keys with:
   - 5+ repeated characters (e.g., "aaaaa")
   - Sequential numbers (e.g., "123456789")
   - Sequential letters (e.g., "abcdefgh")
   - Only numbers
   - Only letters

### Key Storage

- Keys are hashed using SHA-256 before storage
- Original keys are never stored
- Only the hash is used for verification

### Rate Limiting

- Generate/rotate endpoints limited to 10 requests/minute per IP
- Redis-backed for distributed systems
- Automatic fallback to in-memory storage

### JWT Security

- Signed using HS256 (configurable)
- Includes standard claims: sub, role, iat, exp
- Secret key should be stored in environment variables
- Tokens expire after configurable time (default: 24 hours)

## Example Application

See `examples/auth_example.py` for a complete Flask application demonstrating all features:

```bash
python examples/auth_example.py
```

Available endpoints:
- `POST /api/keys/generate` - Generate new API key (rate limited)
- `POST /api/keys/rotate` - Rotate existing key (rate limited)
- `POST /api/keys/verify` - Verify an API key
- `GET /api/keys/list/<user_id>` - List user's keys (masked)
- `POST /api/tokens/generate` - Generate JWT token
- `POST /api/tokens/verify` - Verify JWT token

## Testing

Run the comprehensive test suite:

```bash
# Run all auth tests
pytest mira/tests/test_auth.py -v

# Run with coverage
pytest mira/tests/test_auth.py --cov=mira/auth

# Run only hypothesis property-based tests
pytest mira/tests/test_auth.py::TestAPIKeyManagerHypothesis -v
```

The test suite includes:
- 28 unit tests
- 100 hypothesis property-based test cases per test
- Tests for rate limiting, JWT, validation, and masking
- Mock tests for Redis unavailability scenarios

## Production Deployment

### Environment Variables

```bash
export MIRA_JWT_SECRET="your-super-secret-key-here"
export REDIS_URL="redis://your-redis-host:6379/0"
```

### Best Practices

1. **Never hardcode secrets** - Use environment variables or secret management systems
2. **Use Redis in production** - In-memory fallback is for development only
3. **Disable debug mode** - Never run Flask with `debug=True` in production
4. **Monitor rate limits** - Track and alert on rate limit violations
5. **Rotate JWT secrets** - Periodically rotate your JWT signing secrets
6. **Log security events** - Monitor key generation, rotation, and failed verifications

## API Reference

### APIKeyManager

#### `__init__(jwt_secret, jwt_algorithm="HS256", default_token_expiry_hours=24)`
Initialize the API Key Manager.

#### `generate_api_key(user_id, role="user", metadata=None)`
Generate a new API key for a user.

#### `rotate_api_key(old_key, user_id)`
Rotate an existing API key.

#### `validate_key(key)`
Validate key format and strength.

#### `verify_api_key(key)`
Verify an API key and return associated data.

#### `generate_jwt_token(user_id, role="user", expiry_hours=None, additional_claims=None)`
Generate a JWT token.

#### `verify_jwt_token(token)`
Verify and decode a JWT token.

#### `mask_key(key, show_chars=8)`
Mask a key for display.

#### `list_keys_for_user(user_id, mask=True)`
List all keys for a user.

### Rate Limiter

#### `get_limiter(app=None, redis_url="redis://localhost:6379/0", default_limits=None)`
Get or create the rate limiter instance.

#### `reset_limiter()`
Reset the global limiter (useful for testing).

## License

This module is part of the Mira platform and follows the same license (MIT).
