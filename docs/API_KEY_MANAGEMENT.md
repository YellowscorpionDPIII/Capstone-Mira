# API Key Management Guide

## Overview

This guide covers all aspects of API key and authentication management for the Mira Multi-Agent Workflow Platform, including webhook authentication, integration API keys, JWT-based HITL (Human-in-the-Loop) approval system, and Redis state management.

## Table of Contents

1. [Webhook API Authentication](#webhook-api-authentication)
2. [Integration API Keys](#integration-api-keys)
3. [JWT-Based HITL Approval System](#jwt-based-hitl-approval-system)
4. [Redis State Management](#redis-state-management)
5. [API Key Rotation](#api-key-rotation)
6. [Security Best Practices](#security-best-practices)
7. [Environment Configuration](#environment-configuration)
8. [Troubleshooting](#troubleshooting)

---

## Webhook API Authentication

Mira's webhook API supports multiple authentication methods to secure incoming webhook requests from external services like n8n, GitHub, Trello, and Jira.

### Authentication Methods

#### 1. HMAC-SHA256 Signature Verification (Recommended)

Used for GitHub-style webhook authentication with signature verification.

**Configuration:**
```bash
export MIRA_WEBHOOK_SECRET="your-super-secret-webhook-key"
```

**How it works:**
- Client generates HMAC-SHA256 signature of the request body
- Signature is sent in `X-Hub-Signature-256` header
- Mira verifies the signature matches the expected value

**Example Header:**
```
X-Hub-Signature-256: sha256=abc123def456...
```

**Python Implementation (Client Side):**
```python
import hmac
import hashlib
import requests

secret = "your-super-secret-webhook-key"
payload = {"type": "generate_plan", "data": {...}}
body = json.dumps(payload).encode()

signature = "sha256=" + hmac.new(
    secret.encode(),
    body,
    hashlib.sha256
).hexdigest()

response = requests.post(
    "http://localhost:5000/webhook/n8n",
    json=payload,
    headers={"X-Hub-Signature-256": signature}
)
```

#### 2. API Key (Header-based)

Simple API key authentication via custom header.

**Configuration:**
```bash
export MIRA_API_KEY="mira_key_abc123xyz789"
```

**Example Header:**
```
X-API-Key: mira_key_abc123xyz789
```

#### 3. Bearer Token

OAuth2-style bearer token authentication.

**Configuration:**
```bash
export MIRA_BEARER_TOKEN="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Example Header:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 4. No Authentication (Development Only)

For local development and testing, authentication can be disabled.

**⚠️ WARNING:** Never use this in production environments.

```bash
export MIRA_WEBHOOK_AUTH_ENABLED="false"
```

### Webhook Endpoints

#### POST /webhook/{service}

Process webhook from external service.

**Parameters:**
- `service` (path): Service name (n8n, github, trello, jira, custom)

**Request Body:**
```json
{
  "type": "generate_plan",
  "data": {
    "name": "Project Alpha",
    "goals": ["Goal 1", "Goal 2"],
    "duration_weeks": 12
  }
}
```

**Response (Success):**
```json
{
  "status": "processed",
  "service": "n8n",
  "data": {
    "project_id": "proj_123",
    "milestones": [...]
  }
}
```

**Response (Error):**
```json
{
  "error": "Invalid signature",
  "status": "error",
  "service": "n8n"
}
```

#### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "mira-webhook",
  "handlers": ["n8n", "github", "trello", "jira"]
}
```

#### GET /api/services

List all registered webhook services.

**Response:**
```json
{
  "services": ["n8n", "github", "trello", "jira"],
  "count": 4
}
```

#### GET /docs

Interactive OpenAPI documentation (Swagger UI).

Access at: `http://localhost:5000/docs`

---

## Integration API Keys

Mira integrates with multiple external services. Each integration requires its own API credentials.

### Trello Integration

**Required Configuration:**
```bash
export MIRA_TRELLO_API_KEY="your_trello_api_key"
export MIRA_TRELLO_API_TOKEN="your_trello_token"
export MIRA_TRELLO_BOARD_ID="board_id_123"
```

**Obtaining Trello Credentials:**
1. Visit: https://trello.com/app-key
2. Copy your API Key
3. Generate a Token (follow the link on the page)
4. Get your board ID from the board URL

**Configuration in JSON:**
```json
{
  "integrations": {
    "trello": {
      "enabled": true,
      "api_key": "${MIRA_TRELLO_API_KEY}",
      "api_token": "${MIRA_TRELLO_API_TOKEN}",
      "board_id": "${MIRA_TRELLO_BOARD_ID}"
    }
  }
}
```

### Jira Integration

**Required Configuration:**
```bash
export MIRA_JIRA_URL="https://your-domain.atlassian.net"
export MIRA_JIRA_EMAIL="your-email@company.com"
export MIRA_JIRA_API_TOKEN="your_jira_api_token"
export MIRA_JIRA_PROJECT_KEY="PROJ"
```

**Obtaining Jira Credentials:**
1. Visit: https://id.atlassian.com/manage-profile/security/api-tokens
2. Create API token
3. Use your email and API token for authentication

**Configuration in JSON:**
```json
{
  "integrations": {
    "jira": {
      "enabled": true,
      "url": "${MIRA_JIRA_URL}",
      "email": "${MIRA_JIRA_EMAIL}",
      "api_token": "${MIRA_JIRA_API_TOKEN}",
      "project_key": "${MIRA_JIRA_PROJECT_KEY}"
    }
  }
}
```

### GitHub Integration

**Required Configuration:**
```bash
export MIRA_GITHUB_TOKEN="ghp_your_personal_access_token"
export MIRA_GITHUB_REPO_OWNER="username"
export MIRA_GITHUB_REPO_NAME="repository"
```

**Obtaining GitHub Token:**
1. Go to: https://github.com/settings/tokens
2. Generate new token (classic)
3. Select scopes: `repo`, `workflow`

**Configuration in JSON:**
```json
{
  "integrations": {
    "github": {
      "enabled": true,
      "token": "${MIRA_GITHUB_TOKEN}",
      "repo_owner": "${MIRA_GITHUB_REPO_OWNER}",
      "repo_name": "${MIRA_GITHUB_REPO_NAME}"
    }
  }
}
```

### Airtable Integration

**Required Configuration:**
```bash
export MIRA_AIRTABLE_API_KEY="keyXXXXXXXXXXXXXX"
export MIRA_AIRTABLE_BASE_ID="appXXXXXXXXXXXXXX"
```

**Obtaining Airtable Credentials:**
1. Visit: https://airtable.com/account
2. Generate API key
3. Get base ID from your base URL

**Configuration in JSON:**
```json
{
  "integrations": {
    "airtable": {
      "enabled": true,
      "api_key": "${MIRA_AIRTABLE_API_KEY}",
      "base_id": "${MIRA_AIRTABLE_BASE_ID}"
    }
  }
}
```

### Google Docs Integration

**Required Configuration:**
```bash
export MIRA_GOOGLE_CREDENTIALS_FILE="/path/to/credentials.json"
export MIRA_GOOGLE_DOC_ID="document_id_here"
```

**Obtaining Google Credentials:**
1. Visit: https://console.cloud.google.com/
2. Create a project
3. Enable Google Docs API
4. Create service account
5. Download credentials JSON

**Configuration in JSON:**
```json
{
  "integrations": {
    "google_docs": {
      "enabled": true,
      "credentials_file": "${MIRA_GOOGLE_CREDENTIALS_FILE}",
      "doc_id": "${MIRA_GOOGLE_DOC_ID}"
    }
  }
}
```

---

## JWT-Based HITL Approval System

The Human-in-the-Loop (HITL) approval system uses JWT tokens for secure authentication and authorization.

### JWT Configuration

**Required Environment Variables:**
```bash
export MIRA_JWT_SECRET_KEY="your-super-secret-jwt-key-change-in-prod"
export MIRA_JWT_ALGORITHM="HS256"
export MIRA_JWT_ACCESS_TOKEN_EXPIRE_MINUTES="30"
```

### User Roles

- **hitl_reviewer**: Can approve/reject workflows
- **admin**: Full access to all operations
- **viewer**: Read-only access

### Generating JWT Tokens

**Python Example:**
```python
from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-super-secret-jwt-key-change-in-prod"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(user_id: str, roles: list):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": user_id,
        "roles": roles,
        "exp": expire
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Generate token for HITL reviewer
token = create_access_token("reviewer@company.com", ["hitl_reviewer"])
print(f"Bearer {token}")
```

### HITL API Endpoints

#### POST /approve/{workflow_id}

Approve a high-risk workflow.

**Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Request Body:**
```json
{
  "workflow_id": "workflow_abc123",
  "reviewer_notes": "Approved after review",
  "action": "approve"
}
```

**Response:**
```json
{
  "status": "approved",
  "workflow_id": "workflow_abc123",
  "timestamp": "2025-12-09T13:44:25.000Z",
  "reviewer_id": "reviewer@company.com"
}
```

#### POST /reject/{workflow_id}

Reject a workflow and trigger rollback.

**Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Request Body:**
```json
{
  "workflow_id": "workflow_abc123",
  "reviewer_notes": "Rejected due to compliance concerns",
  "action": "reject"
}
```

**Response:**
```json
{
  "status": "rejected",
  "workflow_id": "workflow_abc123",
  "timestamp": "2025-12-09T13:44:25.000Z",
  "reviewer_id": "reviewer@company.com"
}
```

#### GET /status/{workflow_id}

Check HITL status for a workflow.

**Response:**
```json
{
  "status": "approved",
  "approved_by": "reviewer@company.com",
  "approved_at": "2025-12-09T13:44:25.000Z",
  "notes": "Approved after review",
  "risk_score": {
    "financial": 0.3,
    "compliance": 0.9,
    "explainability": 0.8
  }
}
```

#### GET /pending

List pending HITL requests.

**Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```json
[
  {
    "workflow_id": "workflow_abc123",
    "risk": {
      "financial": "15000",
      "compliance": "0.6",
      "total": "0.85"
    }
  }
]
```

### Risk Assessment Thresholds

Configured in `config/governance.yaml`:

```yaml
risk_thresholds:
  financial: 10000      # USD threshold for high risk
  compliance: 0.8       # Compliance score (0-1)
  explainability: 0.7   # AI explainability threshold (0-1)
  total: 0.75           # Composite risk score threshold
```

Workflows exceeding these thresholds require HITL approval.

---

## Redis State Management

Mira uses Redis for stateful workflow tracking and HITL queue management.

### Redis Configuration

**Environment Variables:**
```bash
export MIRA_REDIS_HOST="localhost"
export MIRA_REDIS_PORT="6379"
export MIRA_REDIS_DB="0"
export MIRA_REDIS_PASSWORD=""  # Optional
```

**Configuration in YAML:**
```yaml
redis:
  host: "localhost"
  port: 6379
  db: 0
  password: ""  # Optional
```

### Redis Key Patterns

#### Workflow State
```
workflow:{workflow_id} -> Hash of workflow data
workflow:{workflow_id}:status -> String: "pending", "approved", "rejected"
```

#### HITL Queue
```
hitl:{workflow_id} -> String: task_id (pending approval)
```

#### Risk Assessment
```
risk:{workflow_id} -> Hash of risk scores
```

#### Audit Log
```
audit_log -> List of JSON audit entries
```

### Redis Commands for Management

**List all pending HITL requests:**
```bash
redis-cli KEYS "hitl:*"
```

**Get workflow status:**
```bash
redis-cli HGETALL "workflow:workflow_abc123"
```

**View audit log:**
```bash
redis-cli LRANGE "audit_log" 0 -1
```

**Clear a workflow:**
```bash
redis-cli DEL "workflow:workflow_abc123"
redis-cli DEL "hitl:workflow_abc123"
redis-cli DEL "risk:workflow_abc123"
```

---

## API Key Rotation

Regular API key rotation is essential for security.

### Rotation Schedule

- **Production keys**: Rotate every 90 days
- **Development keys**: Rotate every 6 months
- **Compromised keys**: Rotate immediately

### Rotation Process

#### 1. Generate New Keys

**For Webhook Secret:**
```python
import secrets
new_secret = secrets.token_urlsafe(32)
print(f"New webhook secret: {new_secret}")
```

**For API Keys:**
```python
import secrets
new_key = f"mira_key_{secrets.token_urlsafe(16)}"
print(f"New API key: {new_key}")
```

#### 2. Update Configuration

```bash
# Backup old configuration
cp .env .env.backup

# Update with new keys
export MIRA_WEBHOOK_SECRET="new_secret_here"
export MIRA_API_KEY="new_key_here"
```

#### 3. Update External Services

Update webhook configurations in:
- n8n workflows
- GitHub webhook settings
- Trello webhook settings
- Jira webhook settings

#### 4. Test New Configuration

```bash
# Test health endpoint
curl http://localhost:5000/health

# Test authenticated endpoint
curl -X POST http://localhost:5000/webhook/n8n \
  -H "X-Hub-Signature-256: sha256=$(echo -n '{}' | openssl dgst -sha256 -hmac 'new_secret_here' | cut -d' ' -f2)" \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### 5. Revoke Old Keys

- Remove old keys from environment
- Update documentation
- Notify team members

### Automation Script

```bash
#!/bin/bash
# rotate_keys.sh - Automated key rotation

BACKUP_DIR="/secure/backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup current configuration
cp .env "$BACKUP_DIR/.env.backup"

# Generate new keys
NEW_WEBHOOK_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
NEW_API_KEY=$(python3 -c "import secrets; print(f'mira_key_{secrets.token_urlsafe(16)}')")

# Update .env file
sed -i "s/MIRA_WEBHOOK_SECRET=.*/MIRA_WEBHOOK_SECRET=$NEW_WEBHOOK_SECRET/" .env
sed -i "s/MIRA_API_KEY=.*/MIRA_API_KEY=$NEW_API_KEY/" .env

echo "Keys rotated successfully!"
echo "Backup saved to: $BACKUP_DIR"
echo "Please update external services with new credentials."
```

---

## Security Best Practices

### 1. Key Storage

**✅ DO:**
- Store keys in environment variables
- Use secrets management systems (AWS Secrets Manager, HashiCorp Vault)
- Encrypt configuration files at rest
- Use `.env` files (never commit to git)

**❌ DON'T:**
- Hardcode keys in source code
- Commit keys to version control
- Share keys in plain text (email, chat)
- Log API keys

### 2. Access Control

- Implement least privilege principle
- Use separate keys for dev/staging/prod
- Enable MFA for key management systems
- Regular access audits

### 3. Network Security

- Use HTTPS/TLS for all API communications
- Implement rate limiting
- Use IP whitelisting when possible
- Enable CORS properly

### 4. Monitoring

- Log all authentication attempts
- Monitor for unusual API usage
- Set up alerts for failed authentications
- Regular security audits

### 5. Key Hygiene

- Minimum key length: 32 characters
- Use cryptographically secure random generation
- Never reuse keys across environments
- Document all keys and their purposes

---

## Environment Configuration

### Complete .env Template

```bash
# Webhook API Configuration
MIRA_WEBHOOK_SECRET="your-super-secret-webhook-key"
MIRA_API_KEY="mira_key_abc123xyz789"
MIRA_BEARER_TOKEN=""
MIRA_WEBHOOK_AUTH_ENABLED="true"
MIRA_WEBHOOK_HOST="0.0.0.0"
MIRA_WEBHOOK_PORT="5000"

# JWT Configuration
MIRA_JWT_SECRET_KEY="your-super-secret-jwt-key-change-in-prod"
MIRA_JWT_ALGORITHM="HS256"
MIRA_JWT_ACCESS_TOKEN_EXPIRE_MINUTES="30"

# Redis Configuration
MIRA_REDIS_HOST="localhost"
MIRA_REDIS_PORT="6379"
MIRA_REDIS_DB="0"
MIRA_REDIS_PASSWORD=""

# Trello Integration
MIRA_TRELLO_API_KEY=""
MIRA_TRELLO_API_TOKEN=""
MIRA_TRELLO_BOARD_ID=""

# Jira Integration
MIRA_JIRA_URL=""
MIRA_JIRA_EMAIL=""
MIRA_JIRA_API_TOKEN=""
MIRA_JIRA_PROJECT_KEY=""

# GitHub Integration
MIRA_GITHUB_TOKEN=""
MIRA_GITHUB_REPO_OWNER=""
MIRA_GITHUB_REPO_NAME=""

# Airtable Integration
MIRA_AIRTABLE_API_KEY=""
MIRA_AIRTABLE_BASE_ID=""

# Google Docs Integration
MIRA_GOOGLE_CREDENTIALS_FILE=""
MIRA_GOOGLE_DOC_ID=""

# OpenAI Configuration (for AI agents)
OPENAI_API_KEY=""
```

### Docker Configuration

```yaml
# docker-compose.yml
version: '3.8'
services:
  mira-webhook:
    image: mira:latest
    environment:
      - MIRA_WEBHOOK_SECRET=${MIRA_WEBHOOK_SECRET}
      - MIRA_API_KEY=${MIRA_API_KEY}
      - MIRA_REDIS_HOST=redis
    ports:
      - "5000:5000"
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

---

## Troubleshooting

### Common Issues

#### 1. Invalid Signature Error

**Symptom:** 403 error with "Invalid signature" message

**Solution:**
```bash
# Verify secret key is set correctly
echo $MIRA_WEBHOOK_SECRET

# Test signature generation
python3 -c "
import hmac, hashlib, json
payload = {}
body = json.dumps(payload).encode()
secret = 'your-secret'
sig = 'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
print(sig)
"
```

#### 2. JWT Token Expired

**Symptom:** 401 error with "Invalid token" message

**Solution:**
- Generate a new token with longer expiration
- Check system time is synchronized (NTP)
- Verify JWT_SECRET_KEY matches between client and server

#### 3. Redis Connection Failed

**Symptom:** "Connection refused" error

**Solution:**
```bash
# Check Redis is running
redis-cli ping

# Check connection parameters
redis-cli -h localhost -p 6379 ping

# Start Redis if needed
redis-server
```

#### 4. Integration API Key Invalid

**Symptom:** 401/403 from external service

**Solution:**
- Verify API key is not expired
- Check key has required permissions
- Regenerate key if compromised
- Test key with service's API directly

### Debug Mode

Enable debug logging:
```bash
export MIRA_LOG_LEVEL="DEBUG"
export MIRA_LOG_API_KEYS="false"  # Never log actual keys
```

### Health Check

```bash
# Check all endpoints
curl http://localhost:5000/health
curl http://localhost:5000/api/services

# Test webhook endpoint
curl -X POST http://localhost:5000/webhook/test \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

---

## Additional Resources

- [Mira Architecture Documentation](../ARCHITECTURE.md)
- [Mira HITL Governance Roadmap](https://github.com/YellowscorpionDPIII/Capstone-Mira/wiki/HITL-Governance-Roadmap)
- [n8n Integration Guide](../n8n/README.md)
- [Load Testing Guide](../locust/README.md)

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/YellowscorpionDPIII/Capstone-Mira/issues
- Documentation: https://github.com/YellowscorpionDPIII/Capstone-Mira

---

**Last Updated:** December 2025  
**Version:** 1.0.0
