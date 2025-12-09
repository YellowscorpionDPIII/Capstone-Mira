# Development and Deployment Workflow

This document describes the complete development, testing, and deployment workflow for the Mira platform.

## Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Google Cloud SDK (for deployment)
- CodeQL CLI (for security scanning)

## Development Workflow

### Phase 1: Local Development

1. **Setup environment**
   ```bash
   pip install -r requirements.txt
   pip install -e ".[dev]"
   ```

2. **Run tests with coverage**
   ```bash
   python -m pytest mira/tests/ --benchmark-disable
   ```

3. **Ensure 95%+ test coverage**
   The project requires 95% test coverage for approval:
   ```bash
   python -m pytest mira/tests/ --benchmark-disable --cov=mira/agents --cov=mira/core --cov-fail-under=95
   ```

### Phase 2: Local Testing with Docker

1. **Start all services**
   ```bash
   docker-compose up
   ```
   This starts:
   - Mira application (port 5000)
   - n8n workflow automation (port 5678)
   - Redis (port 6379)

2. **Generate operator key for webhooks**
   ```bash
   python scripts/generate_operator_key.py
   ```
   Save the generated key for webhook authentication.

3. **Run load tests**
   ```bash
   locust -f load_test.py --host=http://localhost:5000
   ```
   Then open http://localhost:8089 in your browser to configure and run load tests.

### Phase 3: n8n Integration Verification

1. **Access n8n interface**
   Open http://localhost:5678 (credentials: admin/admin)

2. **Test webhook with curl**
   ```bash
   curl -X POST http://localhost:5000/webhook/n8n \
     -H 'Content-Type: application/json' \
     -H 'X-Operator-Key: <your-generated-key>' \
     -d '{"test": "data", "workflowId": "test123"}'
   ```

3. **Verify webhook received**
   Check logs:
   ```bash
   docker-compose logs mira-app
   ```

### Phase 4: Security Scanning

1. **Run CodeQL analysis**
   ```bash
   codeql database create codeql-db --language=python
   codeql database analyze codeql-db --format=sarif-latest --output=results.sarif
   ```

2. **Check for vulnerabilities**
   All security checks must pass before deployment.

### Phase 5: Staging Deployment

1. **Configure GCP credentials**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Deploy to staging**
   ```bash
   ./scripts/deploy_gcp.sh --env=staging
   ```

3. **Verify deployment**
   ```bash
   curl https://your-staging-url/health
   ```

4. **Test staging webhook**
   ```bash
   curl -X POST https://your-staging-url/webhook/n8n \
     -H 'Content-Type: application/json' \
     -H 'X-Operator-Key: <your-key>' \
     -d '{"test": "staging"}'
   ```

## Continuous Integration

The GitHub Actions workflow automatically:
- Runs tests on multiple Python versions (3.9, 3.10, 3.11, 3.12)
- Enforces 95% test coverage threshold
- Reports coverage to Codecov

## Key Files

- `docker-compose.yml` - Local development environment
- `Dockerfile` - Application container definition
- `load_test.py` - Locust load testing scenarios
- `scripts/deploy_gcp.sh` - GCP deployment script
- `scripts/generate_operator_key.py` - Operator key generation utility
- `.github/workflows/test.yml` - CI/CD pipeline

## Webhook Endpoints

- `/health` - Health check endpoint
- `/webhook/github` - GitHub webhook events
- `/webhook/trello` - Trello webhook events
- `/webhook/jira` - Jira webhook events
- `/webhook/n8n` - n8n workflow events

All webhook endpoints require either:
- `X-Operator-Key` header with valid operator key
- `X-Hub-Signature-256` header with valid HMAC signature

## Environment Variables

### Docker Compose
- `WEBHOOK_SECRET_KEY` - Secret for webhook signature verification
- `OPERATOR_KEYS` - Comma-separated list of valid operator keys

### n8n
- `N8N_BASIC_AUTH_USER` - n8n username (default: admin)
- `N8N_BASIC_AUTH_PASSWORD` - n8n password (default: admin)
- `WEBHOOK_URL` - Mira webhook base URL

## Troubleshooting

### Test Coverage Below 95%
If coverage is below threshold:
1. Review coverage report: `open htmlcov/index.html`
2. Add tests for uncovered code
3. Re-run: `pytest --cov=mira/agents --cov=mira/core`

### Docker Compose Issues
```bash
# Stop all containers
docker-compose down

# Remove volumes and restart
docker-compose down -v
docker-compose up --build
```

### Load Test Failures
- Check if services are running: `docker-compose ps`
- Verify network connectivity: `docker-compose logs`
- Reduce load test intensity if services are overwhelmed

### Webhook Authentication Failures
- Verify operator key is correct
- Check if key exists in `config/operator_keys.txt`
- Regenerate key if needed: `python scripts/generate_operator_key.py`

## Best Practices

1. **Always run tests before committing**: Ensure 95%+ coverage
2. **Test locally with Docker**: Verify integration before deployment
3. **Generate unique operator keys**: One per integration/environment
4. **Review security scans**: Address all CodeQL findings
5. **Monitor staging**: Verify staging before production deployment
6. **Keep secrets secure**: Never commit operator keys or secrets to git

## Production Deployment

For production deployment:
```bash
./scripts/deploy_gcp.sh --env=production --project=YOUR_PROJECT_ID
```

⚠️ **Warning**: Production deployment requires:
- All tests passing with 95%+ coverage
- Security scans passing
- Successful staging deployment and verification
- Manual approval from team lead
