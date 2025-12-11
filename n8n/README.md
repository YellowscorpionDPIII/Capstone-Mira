# n8n Integration for Mira

This directory contains n8n node templates and configurations for integrating n8n workflows with the Mira Multi-Agent Workflow Platform.

## Overview

The Mira n8n integration allows you to trigger Mira workflows from n8n, enabling:
- Automated project plan generation
- Risk assessment automation
- Status report generation
- Multi-agent orchestration
- Integration with other n8n nodes (Slack, email, databases, etc.)

## Files

- **`nodes/mira_webhook_credential.json`**: Credential configuration for authenticating with Mira webhook API
- **`nodes/MiraWebhook.node.json`**: Node configuration for Mira webhook operations

## Installation

### 1. Create Credentials in n8n

1. Open n8n
2. Go to **Settings** → **Credentials** → **New**
3. Search for "Generic Credential"
4. Manually import the credential configuration from `mira_webhook_credential.json`

**Or manually configure:**
- **Name:** Mira Webhook API
- **API Base URL:** `http://your-mira-instance.com:5000`
- **Service Name:** `n8n`
- **Webhook Secret Key:** Your webhook secret (from Mira configuration)
- **Authentication Type:** `Signature (HMAC-SHA256)` (recommended)

### 2. Configure HTTP Request Node

Since Mira uses a standard webhook interface, you can use n8n's built-in HTTP Request node:

1. Add **HTTP Request** node to your workflow
2. Configure the node:
   - **Method:** POST
   - **URL:** `{{ $credentials.miraWebhookApi.baseUrl }}/webhook/{{ $credentials.miraWebhookApi.serviceName }}`
   - **Authentication:** Use the Mira Webhook API credential
   - **Body Content Type:** JSON
   - **Specify Body:** Using Fields Below

## Usage Examples

### Example 1: Generate Project Plan

**HTTP Request Node Configuration:**

```json
{
  "method": "POST",
  "url": "http://localhost:5000/webhook/n8n",
  "authentication": "genericCredentialType",
  "genericAuthType": "miraWebhookApi",
  "body": {
    "type": "generate_plan",
    "data": {
      "name": "{{ $json.projectName }}",
      "goals": "{{ $json.goals.split(',') }}",
      "duration_weeks": "{{ $json.duration }}"
    }
  },
  "options": {
    "timeout": 30000
  }
}
```

**Input Data:**
```json
{
  "projectName": "Website Redesign",
  "goals": "Improve UX,Increase conversion,Mobile optimization",
  "duration": 12
}
```

### Example 2: Assess Project Risks

**HTTP Request Node Configuration:**

```json
{
  "method": "POST",
  "url": "http://localhost:5000/webhook/n8n",
  "body": {
    "type": "assess_risks",
    "data": {
      "project_id": "{{ $json.projectId }}",
      "tasks": "{{ $json.tasks }}"
    }
  }
}
```

**Input Data:**
```json
{
  "projectId": "proj_123",
  "tasks": [
    "Database migration",
    "API integration",
    "Security audit"
  ]
}
```

### Example 3: Generate Status Report

**HTTP Request Node Configuration:**

```json
{
  "method": "POST",
  "url": "http://localhost:5000/webhook/n8n",
  "body": {
    "type": "generate_status",
    "data": {
      "project_id": "{{ $json.projectId }}",
      "week_number": "{{ $json.weekNumber }}",
      "completed_tasks": "{{ $json.completedTasks }}",
      "total_tasks": "{{ $json.totalTasks }}",
      "blockers": "{{ $json.blockers }}"
    }
  }
}
```

### Example 4: Full Workflow Orchestration

**HTTP Request Node Configuration:**

```json
{
  "method": "POST",
  "url": "http://localhost:5000/webhook/n8n",
  "body": {
    "type": "orchestrate",
    "data": {
      "workflow_type": "full_project_initialization",
      "project_name": "{{ $json.projectName }}",
      "goals": "{{ $json.goals }}",
      "duration_weeks": "{{ $json.duration }}",
      "integrations": ["trello", "jira", "github"]
    }
  }
}
```

## Complete n8n Workflow Example

### Automated Weekly Status Report

This workflow automatically generates weekly status reports:

```
[Cron Trigger (Every Monday 9 AM)]
    ↓
[Fetch Project Data (Airtable/Database)]
    ↓
[HTTP Request: Generate Status Report (Mira)]
    ↓
[Post to Slack]
    ↓
[Send Email Summary]
```

**Cron Node:**
- Trigger: `0 9 * * 1` (Every Monday at 9 AM)

**HTTP Request to Mira:**
```json
{
  "method": "POST",
  "url": "http://localhost:5000/webhook/n8n",
  "body": {
    "type": "generate_status",
    "data": {
      "project_id": "{{ $json.id }}",
      "week_number": "{{ $now.format('w') }}",
      "completed_tasks": "{{ $json.completed }}",
      "total_tasks": "{{ $json.total }}",
      "blockers": "{{ $json.blockers }}"
    }
  }
}
```

**Slack Node:**
```json
{
  "channel": "#project-updates",
  "text": "Weekly Status Report:\n{{ $json.data.summary }}"
}
```

## Authentication Methods

### 1. HMAC-SHA256 Signature (Recommended)

Most secure method, compatible with GitHub-style webhooks.

**Configuration:**
- Set `MIRA_WEBHOOK_SECRET` environment variable on Mira server
- Configure the same secret in n8n credential
- Signatures are automatically generated and verified

**Header:**
```
X-Hub-Signature-256: sha256=<hmac-sha256-hash>
```

### 2. API Key Header

Simple API key in custom header.

**Configuration:**
- Set `MIRA_API_KEY` environment variable on Mira server
- Configure in n8n HTTP Request node headers:
```json
{
  "headers": {
    "X-API-Key": "mira_key_abc123xyz789"
  }
}
```

### 3. Bearer Token

OAuth2-style bearer token.

**Configuration:**
```json
{
  "authentication": "headerAuth",
  "headerAuth": {
    "name": "Authorization",
    "value": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

## Response Handling

### Success Response (200)

```json
{
  "status": "processed",
  "service": "n8n",
  "data": {
    "project_id": "proj_123",
    "milestones": [...],
    "risks": [...]
  }
}
```

### Error Response (4xx/5xx)

```json
{
  "error": "Error message",
  "status": "error",
  "service": "n8n",
  "message": "Detailed error information"
}
```

**Error Handling in n8n:**

Add an **Error Trigger** node connected to your HTTP Request:
- On 403: Check authentication credentials
- On 404: Verify service name is correct
- On 500: Log error and retry with exponential backoff

## Testing

### Health Check

Test Mira server connectivity:

```json
{
  "method": "GET",
  "url": "http://localhost:5000/health"
}
```

Expected response:
```json
{
  "status": "healthy",
  "service": "mira-webhook",
  "handlers": ["n8n", "github", "trello", "jira"]
}
```

### Test Webhook

Send a simple test webhook:

```json
{
  "method": "POST",
  "url": "http://localhost:5000/webhook/n8n",
  "body": {
    "type": "test",
    "data": {
      "message": "Test from n8n"
    }
  }
}
```

## Troubleshooting

### Authentication Failed (403)

**Problem:** Invalid signature or API key

**Solution:**
- Verify webhook secret matches between n8n and Mira
- Check signature generation is correct
- Ensure API key is valid and not expired

### Service Not Found (404)

**Problem:** Unknown service or incorrect URL

**Solution:**
- Verify service name is `n8n` in URL
- Check URL format: `/webhook/{service}`
- Confirm Mira server is running

### Timeout Errors

**Problem:** Request taking too long

**Solution:**
- Increase timeout in HTTP Request node (default: 30000ms)
- Check Mira server performance
- Optimize workflow complexity

### Invalid Request (400)

**Problem:** Malformed request body

**Solution:**
- Verify JSON structure matches expected format
- Check required fields are present
- Validate data types (strings, numbers, arrays)

## Performance Optimization

### Batch Operations

Process multiple items in parallel using n8n's **Split In Batches** node:

```
[Trigger]
    ↓
[Fetch Multiple Projects]
    ↓
[Split In Batches (5 items)]
    ↓
[HTTP Request: Mira Webhook] (Parallel)
    ↓
[Aggregate Results]
```

### Caching

Use n8n's **Cache** node to avoid redundant API calls:

```
[Trigger]
    ↓
[Check Cache]
    ↓ (miss)
[HTTP Request: Mira]
    ↓
[Update Cache (TTL: 1 hour)]
```

### Error Retry Logic

Implement exponential backoff:

```
[HTTP Request: Mira]
    ↓ (error)
[Wait (exponential: 1s, 2s, 4s)]
    ↓
[Retry HTTP Request]
```

## Related Documentation

- [API Key Management Guide](../docs/API_KEY_MANAGEMENT.md)
- [Mira Architecture](../ARCHITECTURE.md)
- [Load Testing](../locust/README.md)

## Support

For issues or questions:
- GitHub Issues: https://github.com/YellowscorpionDPIII/Capstone-Mira/issues
- Documentation: https://github.com/YellowscorpionDPIII/Capstone-Mira
