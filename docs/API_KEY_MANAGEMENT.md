# API Key Management

This document describes the API key management system for the Mira platform, including the RBAC (Role-Based Access Control) permission matrix for different user roles.

## Overview

The Mira platform uses API keys for authentication and role-based access control (RBAC) for authorization. Each API key is associated with a user and a role that determines what operations the user can perform.

## User Roles

The system supports three hierarchical roles:

1. **Viewer** - Read-only access to own resources and webhooks
2. **Operator** - Can manage keys and execute webhooks
3. **Admin** - Full access to all resources and operations

## RBAC Permission Matrix

The following table shows which operations are available for each role:

| Endpoint                   | Viewer                     | Operator                    | Admin                      |
|----------------------------|----------------------------|-----------------------------|----------------------------|
| GET /api/keys              | ✅ List own keys           | ✅ List all keys            | ✅ List/CRUD               |
| POST /api/keys             | ❌                         | ✅ Generate keys            | ✅ Manage                  |
| DELETE /api/keys/:id       | ❌                         | ❌                          | ✅ Revoke                  |
| POST /webhook/:service     | ✅ Read webhooks           | ✅ Execute webhooks         | ✅ Execute webhooks        |

### Detailed Permissions

#### Viewer Role
- **GET /api/keys**: Can only view their own API keys
- **POST /api/keys**: Cannot generate new keys
- **DELETE /api/keys/:id**: Cannot revoke keys
- **POST /webhook/:service**: Can receive webhook data but cannot execute actions (read-only)

#### Operator Role
- **GET /api/keys**: Can view all API keys in the system
- **POST /api/keys**: Can generate new API keys for viewer and operator roles
- **DELETE /api/keys/:id**: Cannot revoke keys
- **POST /webhook/:service**: Can execute webhook handlers and trigger actions

#### Admin Role
- **GET /api/keys**: Can view all API keys with full details
- **POST /api/keys**: Can generate API keys for any role (viewer, operator, admin)
- **DELETE /api/keys/:id**: Can revoke any API key
- **POST /webhook/:service**: Full access to execute webhook handlers

## API Endpoints

### Authentication

All API requests must include an API key in the `Authorization` header:

```
Authorization: Bearer mira_your_api_key_here
```

### GET /api/keys

List API keys based on user role.

**Request:**
```http
GET /api/keys
Authorization: Bearer mira_your_api_key_here
```

**Response (Viewer - own keys only):**
```json
{
  "keys": [
    {
      "key_id": "abc123",
      "user_id": "user_001",
      "role": "viewer",
      "name": "My API Key",
      "created_at": "2024-01-01T00:00:00",
      "expires_at": "2025-01-01T00:00:00",
      "is_active": true,
      "last_used_at": "2024-06-01T12:00:00"
    }
  ],
  "count": 1
}
```

**Response (Operator/Admin - all keys):**
```json
{
  "keys": [
    {
      "key_id": "abc123",
      "user_id": "user_001",
      "role": "viewer",
      "name": "User 1 Key",
      "created_at": "2024-01-01T00:00:00",
      "expires_at": "2025-01-01T00:00:00",
      "is_active": true,
      "last_used_at": "2024-06-01T12:00:00"
    },
    {
      "key_id": "def456",
      "user_id": "user_002",
      "role": "operator",
      "name": "User 2 Key",
      "created_at": "2024-01-01T00:00:00",
      "expires_at": null,
      "is_active": true,
      "last_used_at": "2024-06-01T12:00:00"
    }
  ],
  "count": 2
}
```

**Access Control:**
- Viewer: Returns only keys owned by the requesting user
- Operator: Returns all keys in the system
- Admin: Returns all keys with full details (including hashed_key field)

### POST /api/keys

Generate a new API key.

**Required Role:** Operator or Admin

**Request:**
```http
POST /api/keys
Authorization: Bearer mira_your_api_key_here
Content-Type: application/json

{
  "name": "Production API Key",
  "role": "viewer",
  "expires_in_days": 365
}
```

**Request Parameters:**
- `name` (optional): Human-readable name for the key
- `role` (required): Role for the new key (`viewer`, `operator`, or `admin`)
- `expires_in_days` (optional): Number of days until expiration (null = no expiration)
- `user_id` (optional, admin only): User ID to associate with the key

**Response:**
```json
{
  "message": "API key generated successfully",
  "key": "mira_abc123def456ghi789jkl012mno345pqr678stu",
  "key_id": "xyz789",
  "key_info": {
    "key_id": "xyz789",
    "user_id": "user_001",
    "role": "viewer",
    "name": "Production API Key",
    "created_at": "2024-06-15T14:30:00",
    "expires_at": "2025-06-15T14:30:00",
    "is_active": true,
    "last_used_at": null
  }
}
```

**Important:** The `key` field contains the raw API key and is only returned once during generation. Store it securely as it cannot be retrieved later.

**Access Control:**
- Operator: Can generate keys for `viewer` and `operator` roles
- Admin: Can generate keys for any role including `admin`
- Users can only generate keys for themselves unless they are admins

### DELETE /api/keys/:id

Revoke (deactivate) an API key.

**Required Role:** Admin only

**Request:**
```http
DELETE /api/keys/xyz789
Authorization: Bearer mira_your_api_key_here
```

**Response:**
```json
{
  "message": "API key xyz789 revoked successfully"
}
```

**Error Response (key not found):**
```json
{
  "error": "Key not found"
}
```

**Access Control:**
- Admin: Can revoke any API key
- Operator/Viewer: Access denied (403)

### POST /webhook/:service

Handle incoming webhooks from external services.

**Request:**
```http
POST /webhook/github
Authorization: Bearer mira_your_api_key_here
Content-Type: application/json

{
  "event": "push",
  "repository": "my-repo",
  "data": { ... }
}
```

**Response (Viewer - read-only):**
```json
{
  "status": "received",
  "service": "github",
  "message": "Webhook received but not executed (read-only access)"
}
```

**Response (Operator/Admin - executed):**
```json
{
  "status": "processed",
  "service": "github"
}
```

**Supported Services:**
- `github` - GitHub webhooks
- `trello` - Trello webhooks  
- `jira` - Jira webhooks

**Access Control:**
- Viewer: Can receive webhook data but cannot execute handlers (read-only)
- Operator: Can execute webhook handlers
- Admin: Full access to execute webhook handlers

### Webhook Signature Verification

If a `secret_key` is configured, webhooks should include a signature in the `X-Hub-Signature-256` header for verification:

```http
X-Hub-Signature-256: sha256=abc123def456...
```

## Security Best Practices

### API Key Management

1. **Store keys securely**: API keys are shown only once during generation. Store them in secure credential storage (e.g., environment variables, secrets managers).

2. **Use expiration dates**: Set appropriate expiration dates for API keys to limit the impact of compromised keys.

3. **Rotate keys regularly**: Generate new keys periodically and revoke old ones.

4. **Principle of least privilege**: Assign the minimum required role for each API key.

5. **Monitor usage**: Track `last_used_at` timestamps to identify unused or suspicious keys.

### Role Assignment

1. **Viewer Role**: Use for read-only integrations, monitoring tools, and reporting systems.

2. **Operator Role**: Use for automation systems that need to manage keys and execute webhooks.

3. **Admin Role**: Reserve for trusted administrators who need full system access. Limit the number of admin keys.

### Rate Limiting

To prevent abuse, consider implementing rate limiting on API endpoints:
- Viewer: 100 requests/hour
- Operator: 1000 requests/hour
- Admin: Unlimited

### Audit Logging

All API key operations should be logged for security auditing:
- Key generation (who, when, what role)
- Key usage (which key, what endpoint, when)
- Key revocation (who revoked, which key, when)
- Failed authentication attempts

## Usage Examples

### Example 1: Viewer accessing their own keys

```bash
curl -H "Authorization: Bearer mira_viewer_key_123" \
     https://api.mira.example.com/api/keys
```

### Example 2: Operator generating a new viewer key

```bash
curl -X POST \
     -H "Authorization: Bearer mira_operator_key_456" \
     -H "Content-Type: application/json" \
     -d '{"name": "New Viewer Key", "role": "viewer", "expires_in_days": 90}' \
     https://api.mira.example.com/api/keys
```

### Example 3: Admin revoking a compromised key

```bash
curl -X DELETE \
     -H "Authorization: Bearer mira_admin_key_789" \
     https://api.mira.example.com/api/keys/compromised_key_id
```

### Example 4: Operator executing a webhook

```bash
curl -X POST \
     -H "Authorization: Bearer mira_operator_key_456" \
     -H "Content-Type: application/json" \
     -d '{"event": "push", "repository": "my-repo"}' \
     https://api.mira.example.com/webhook/github
```

## Error Responses

### 401 Unauthorized

Missing or invalid API key:
```json
{
  "error": "Invalid or missing API key"
}
```

### 403 Forbidden

Insufficient permissions:
```json
{
  "error": "Permission denied"
}
```

### 404 Not Found

Resource not found:
```json
{
  "error": "Key not found"
}
```

### 500 Internal Server Error

Server error:
```json
{
  "error": "Internal server error"
}
```

## Implementation Details

The RBAC system is implemented using:

1. **`mira/core/rbac.py`**: Role and permission definitions, RBAC manager
2. **`mira/core/api_key_manager.py`**: API key generation, validation, and storage
3. **`mira/core/api_webhook_handler.py`**: Flask routes with RBAC decorators

### Role Hierarchy

Roles are hierarchical, with higher roles inheriting permissions from lower roles:

```
Admin (level 3)
  ├─ All Operator permissions
  └─ Additional: REVOKE_KEYS, CRUD_KEYS

Operator (level 2)
  ├─ All Viewer permissions
  └─ Additional: LIST_ALL_KEYS, GENERATE_KEYS, EXECUTE_WEBHOOKS

Viewer (level 1)
  └─ Base: LIST_OWN_KEYS, READ_WEBHOOKS
```

## Migration Guide

### Upgrading from Basic Authentication

If you're upgrading from a system without RBAC:

1. Generate admin API keys for existing administrators
2. Assign appropriate roles to existing users
3. Update client applications to include API keys in requests
4. Migrate existing authentication tokens to new API key format
5. Revoke old authentication credentials

## Testing

Comprehensive tests are available in:
- `mira/tests/test_rbac.py` - RBAC permission tests
- `mira/tests/test_api_keys.py` - API key management tests

Run tests with:
```bash
python -m unittest discover mira/tests
```

## Support

For questions or issues with API key management:
1. Check the error response for details
2. Review the audit logs for authentication issues
3. Contact your system administrator for role changes
4. Submit an issue on GitHub for bugs or feature requests
