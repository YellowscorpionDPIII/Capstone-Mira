# API Key Management Guide

## Overview

The Mira HITL API Key Management system provides secure, role-based access control for webhooks and API endpoints. This system is designed for multi-agent workflows with integrations like n8n, Airtable, and other external services.

## Features

- **Secure Key Generation**: Cryptographically secure API keys using Python's `secrets` module
- **Role-Based Access Control (RBAC)**: Three roles with granular permissions
- **Key Expiration & Rotation**: Automatic expiration and manual rotation support
- **Persistent Storage**: Integration with Airtable for key persistence
- **Audit Logging**: Complete logging of all authentication events
- **RESTful API**: Simple HTTP API for key management

## Roles and Permissions

### Viewer
- **Permissions**: `read`, `list`
- **Use Case**: Read-only access for monitoring and reporting
- **Example**: Dashboard displays, status monitors

### Operator
- **Permissions**: `read`, `list`, `write`, `execute`
- **Use Case**: Automation workflows, executing tasks
- **Example**: n8n workflows, automated project creation

### Admin
- **Permissions**: `read`, `list`, `write`, `execute`, `manage_keys`, `manage_users`
- **Use Case**: Full system administration
- **Example**: API key management, system configuration

## Quick Start

### 1. Initialize API Key Manager

```python
from mira.auth import ApiKeyManager
from mira.integrations.airtable_integration import AirtableIntegration

# Set up Airtable storage (optional but recommended)
airtable = AirtableIntegration({
    'api_key': 'your-airtable-api-key',
    'base_id': 'your-base-id'
})
airtable.connect()

# Initialize manager
manager = ApiKeyManager(
    storage_backend=airtable,
    default_expiry_days=90
)
```

### 2. Generate an API Key

```python
# Generate a key for an operator
raw_key, key_metadata = manager.generate_key(
    role='operator',
    name='n8n Automation Bot',
    expiry_days=180
)

print(f"API Key: {raw_key}")
print(f"Key ID: {key_metadata.key_id}")
print(f"Expires: {key_metadata.expires_at}")
```

**⚠️ Important**: The raw API key is only shown once. Store it securely!

### 3. Set Up Authenticated Webhook Server

```python
from mira.auth import AuthenticatedWebhookHandler

# Initialize with API key manager
webhook_handler = AuthenticatedWebhookHandler(
    api_key_manager=manager,
    secret_key='your-webhook-secret'
)

# Register webhook handlers
def handle_n8n_webhook(data):
    # Access authenticated user info
    auth_info = data.get('_auth', {})
    key_id = auth_info.get('key_id')
    role = auth_info.get('role')
    
    print(f"Request from {key_id} with role {role}")
    # Process webhook...
    return {'status': 'success'}

webhook_handler.register_handler('n8n', handle_n8n_webhook)

# Start server
webhook_handler.run(host='0.0.0.0', port=5000)
```

## Configuration

Add to your `config.json`:

```json
{
  "webhook": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 5000,
    "use_authentication": true
  },
  "api_keys": {
    "enabled": true,
    "default_expiry_days": 90,
    "storage_backend": "airtable"
  },
  "integrations": {
    "airtable": {
      "enabled": true,
      "api_key": "YOUR_AIRTABLE_KEY",
      "base_id": "YOUR_BASE_ID"
    }
  }
}
```

## API Endpoints

### Authentication Header

All authenticated endpoints require:
```
Authorization: Bearer <your-api-key>
```

### Create API Key

**Endpoint**: `POST /api/keys`  
**Permission**: `manage_keys` (admin only)

**Request**:
```json
{
  "role": "operator",
  "name": "Production Bot",
  "expiry_days": 90
}
```

**Response**:
```json
{
  "api_key": "abc123xyz789...",
  "key_id": "mira_key_1234567890abcdef",
  "role": "operator",
  "expires_at": "2026-03-09T12:00:00",
  "warning": "Save this key securely. It will not be shown again."
}
```

### List API Keys

**Endpoint**: `GET /api/keys?role=operator&status=active`  
**Permission**: `manage_keys` (admin only)

**Response**:
```json
{
  "keys": [
    {
      "key_id": "mira_key_abc123",
      "role": "operator",
      "name": "Production Bot",
      "created_at": "2025-12-09T12:00:00",
      "expires_at": "2026-03-09T12:00:00",
      "last_used": "2025-12-09T13:30:00",
      "status": "active"
    }
  ]
}
```

### Revoke API Key

**Endpoint**: `DELETE /api/keys/<key_id>`  
**Permission**: `manage_keys` (admin only)

**Response**:
```json
{
  "message": "API key mira_key_abc123 revoked successfully"
}
```

### Rotate API Key

**Endpoint**: `POST /api/keys/<key_id>/rotate`  
**Permission**: `manage_keys` (admin only)

**Request** (optional):
```json
{
  "role": "admin"
}
```

**Response**:
```json
{
  "api_key": "new_key_xyz789...",
  "key_id": "mira_key_newid456",
  "role": "admin",
  "expires_at": "2026-03-09T12:00:00",
  "message": "Key mira_key_abc123 rotated successfully"
}
```

### Validate API Key

**Endpoint**: `GET /api/auth/validate`  
**Permission**: Any authenticated key

**Response**:
```json
{
  "valid": true,
  "key_id": "mira_key_abc123",
  "role": "operator",
  "expires_at": "2026-03-09T12:00:00",
  "permissions": ["read", "list", "write", "execute"]
}
```

### Authenticated Webhook

**Endpoint**: `POST /webhook/<service>`  
**Permission**: `execute`

**Request**:
```bash
curl -X POST http://localhost:5000/webhook/n8n \
  -H "Authorization: Bearer <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "generate_plan",
    "data": {
      "name": "My Project",
      "goals": ["Goal 1", "Goal 2"]
    }
  }'
```

## n8n Integration

### Step 1: Generate API Key

Use the admin key to generate an operator key for n8n:

```bash
curl -X POST http://localhost:5000/api/keys \
  -H "Authorization: Bearer <admin-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "operator",
    "name": "n8n Workflow Bot",
    "expiry_days": 180
  }'
```

Save the returned `api_key` value.

### Step 2: Configure n8n HTTP Request Node

1. Add an **HTTP Request** node to your workflow
2. Set **Method**: `POST`
3. Set **URL**: `http://your-mira-server:5000/webhook/n8n`
4. Under **Authentication**: Select "Generic Credential Type"
5. Add **Header**:
   - **Name**: `Authorization`
   - **Value**: `Bearer <your-operator-api-key>`
6. Set **Body Content Type**: `JSON`
7. Add your JSON payload

### Step 3: Example n8n Workflow

```json
{
  "nodes": [
    {
      "name": "Trigger",
      "type": "n8n-nodes-base.scheduleTrigger",
      "parameters": {
        "rule": {
          "interval": [{"field": "hours", "value": 1}]
        }
      }
    },
    {
      "name": "Call Mira API",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://mira-server:5000/webhook/n8n",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "options": {},
        "headerParameters": {
          "parameters": [
            {
              "name": "Authorization",
              "value": "Bearer <your-api-key>"
            }
          ]
        },
        "bodyParameters": {
          "parameters": [
            {
              "name": "type",
              "value": "generate_plan"
            },
            {
              "name": "data",
              "value": {
                "name": "Automated Project",
                "goals": ["Goal 1", "Goal 2"],
                "duration_weeks": 8
              }
            }
          ]
        }
      }
    }
  ]
}
```

## Airtable Integration

### Table Structure

Create a table named `API Keys` in your Airtable base with these fields:

| Field Name | Type | Description |
|------------|------|-------------|
| key_id | Single line text | Unique key identifier |
| key_hash | Long text | Hashed key (never plain text) |
| role | Single select | viewer, operator, admin |
| name | Single line text | Human-readable name |
| created_at | Date | Creation timestamp |
| expires_at | Date | Expiration timestamp |
| last_used | Date | Last usage timestamp |
| status | Single select | active, revoked, expired |

### Enable Airtable Storage

```python
from mira.integrations.airtable_integration import AirtableIntegration

airtable = AirtableIntegration({
    'api_key': 'your-airtable-api-key',
    'base_id': 'your-base-id'
})
airtable.connect()

# Keys are automatically stored in Airtable
manager = ApiKeyManager(storage_backend=airtable)
```

## Security Best Practices

1. **Never Commit Keys**: Never commit API keys to source control
2. **Use Environment Variables**: Store keys in environment variables or secure vaults
3. **Regular Rotation**: Rotate keys regularly (recommended: every 90 days)
4. **Minimal Permissions**: Use the least privileged role necessary
5. **Monitor Usage**: Regularly review `last_used` timestamps
6. **Revoke Unused Keys**: Remove keys that haven't been used in 30+ days
7. **HTTPS Only**: Always use HTTPS in production
8. **Rate Limiting**: Implement rate limiting on webhook endpoints

## Monitoring and Audit

All authentication events are logged:

```python
import logging
logging.basicConfig(level=logging.INFO)

# Logs include:
# - Authentication attempts (success/failure)
# - Permission checks
# - Key generation, rotation, revocation
# - Last usage timestamps
```

Example log output:
```
INFO - mira.auth.api_key_manager - Generated new API key: mira_key_abc123 with role: operator
INFO - mira.auth.api_key_manager - API key validated successfully: mira_key_abc123
INFO - mira.auth.middleware - Authenticated: mira_key_abc123 (role: operator) for POST /webhook/n8n
```

## Troubleshooting

### Invalid or Expired API Key

**Error**: `401 Unauthorized - Invalid or expired API key`

**Solutions**:
- Verify the API key is correct
- Check if the key has expired: `GET /api/auth/validate`
- Rotate the key if expired: `POST /api/keys/<key_id>/rotate`

### Insufficient Permissions

**Error**: `403 Forbidden - Insufficient permissions`

**Solutions**:
- Check required permission for the endpoint
- Verify your key's role has the necessary permission
- Use an admin key for key management operations
- Use an operator/admin key for executing webhooks

### Key Not Found in Storage

**Error**: Keys not persisting between restarts

**Solutions**:
- Verify Airtable integration is configured
- Check Airtable API key and base_id
- Ensure `airtable.connect()` is called before creating manager

## Examples

See `examples/api_key_management.py` for complete working examples including:
- Generating keys for different roles
- Validating and using keys
- Key rotation
- Listing and managing keys
- n8n webhook integration
- cURL command examples

Run the examples:
```bash
python examples/api_key_management.py
```

## Support

For issues or questions:
1. Check the logs for detailed error messages
2. Review the examples in `examples/api_key_management.py`
3. Consult the test suite in `mira/tests/test_auth.py`
4. Open an issue on GitHub
