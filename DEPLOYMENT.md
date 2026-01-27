# Deployment Guide

This guide covers deploying the Mira platform to production with all necessary configurations.

## Prerequisites

- Google Cloud SDK (`gcloud`) installed and configured
- Kubernetes cluster (for HPA configuration) or Cloud Run enabled
- Docker installed (for building images)
- Python 3.9+ installed
- Node.js 18+ (for n8n workflow validation)

## Quick Deployment

### 1. Deploy to Google Cloud Platform

The `deploy_gcp.sh` script handles deployment with secret rotation and rollback capabilities.

```bash
# Set environment variables
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
export CLOUD_RUN_SERVICE="mira-service"

# Deploy
./deploy_gcp.sh deploy
```

**Features:**
- Automatic secret rotation using `gcloud secrets versions access`
- Compliance scanning with Risk Assessor agent
- Automatic rollback on deployment failure
- Health check verification

### 2. Manual Rollback

If you need to rollback to a previous version:

```bash
./deploy_gcp.sh rollback <previous-image-tag>
```

Example:
```bash
./deploy_gcp.sh rollback 20231210-143000
```

### 3. Rotate Secrets Only

To rotate secrets without deploying:

```bash
./deploy_gcp.sh rotate-secrets
```

## Kubernetes HPA Configuration

For Kubernetes deployments with Horizontal Pod Autoscaling:

```bash
# Apply HPA configuration
kubectl apply -f k8s-hpa-config.yaml

# Verify HPA status
kubectl get hpa mira-hpa

# Check scaling events
kubectl describe hpa mira-hpa
```

**HPA Parameters:**
- **Min Instances:** 2
- **Max Instances:** 10
- **Concurrency:** 80 concurrent requests per pod
- **CPU Target:** 70% utilization
- **Memory Target:** 80% utilization

## Cloud Run Configuration

For Cloud Run deployments:

```bash
# Apply Cloud Run configuration
gcloud run services replace cloudrun-config.yaml \
  --project=$GCP_PROJECT_ID \
  --region=$GCP_REGION
```

**Cloud Run Parameters:**
- **Min Instances:** 2
- **Max Instances:** 10
- **Container Concurrency:** 80 requests

## Secret Management

The deployment script expects the following secrets to be configured in Google Cloud Secret Manager:

- `api-key`: API authentication key
- `database-password`: Database connection password
- `jwt-secret`: JWT signing secret

To create a secret:

```bash
# Create a new secret
echo -n "your-secret-value" | gcloud secrets create api-key \
  --project=$GCP_PROJECT_ID \
  --data-file=-

# Add a new version (for rotation)
echo -n "new-secret-value" | gcloud secrets versions add api-key \
  --project=$GCP_PROJECT_ID \
  --data-file=-
```

## Compliance Scanning

The deployment pipeline automatically runs compliance scanning using the Risk Assessor agent. To run manually:

```bash
python3 -c "
from governance.risk_assessor import RiskAssessor
assessor = RiskAssessor()
result = assessor.assess({
    'deployment': {
        'service': 'mira-service',
        'timestamp': '2023-12-10T14:30:00Z'
    }
})
print(result)
"
```

To bypass compliance scanning (not recommended for production):

```bash
SKIP_COMPLIANCE=true ./deploy_gcp.sh deploy
```

## n8n Workflow Validation

Workflows are automatically validated in the CI pipeline. To validate locally:

```bash
# Install n8n CLI
npm install -g n8n

# Validate a workflow
n8n workflow:validate workflows/your-workflow.json
```

## Performance Benchmarking with Locust

Test system performance and capacity:

```bash
# Install locust
pip install locust

# Run with web UI
locust -f locustfile.py --host=http://your-service-url

# Run headless for CI/CD
locust -f locustfile.py --host=http://your-service-url \
  --headless --users 100 --spawn-rate 10 --run-time 5m
```

**Performance Targets:**
- **Throughput:** 1,000+ requests/min
- **Revenue Simulation:** $50k-$5M traffic patterns
- **Response Time:** <500ms p95
- **Error Rate:** <1%

### Load Testing Scenarios

The Locust configuration includes multiple user classes:

1. **MiraUser**: Standard user behavior (70% of load)
   - Project planning
   - Risk assessment
   - Status reporting
   - Workflow orchestration

2. **HighVolumeUser**: High-frequency API usage (30% of load)
   - Rapid-fire requests
   - Simulates peak traffic

3. **RevenueTargetShape**: Revenue-based load patterns
   - Gradual ramp from $50k to $5M traffic levels
   - Realistic traffic patterns

## Monitoring and Logging

### View Deployment Logs

```bash
# View Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=mira-service" \
  --project=$GCP_PROJECT_ID \
  --limit=50 \
  --format=json

# View local deployment logs
cat deployment.log
```

### Monitor HPA Scaling

```bash
# Watch HPA scaling in real-time
kubectl get hpa mira-hpa --watch

# View pod metrics
kubectl top pods -l app=mira
```

## Troubleshooting

### Deployment Fails

1. Check the `deployment.log` file for error messages
2. Verify GCP credentials: `gcloud auth list`
3. Ensure project ID is correct: `gcloud config get-value project`
4. Check service status: `gcloud run services describe mira-service`

### Automatic Rollback Doesn't Work

1. Verify previous image exists: `gcloud container images list`
2. Check rollback logs in `deployment.log`
3. Manual rollback: `./deploy_gcp.sh rollback <tag>`

### Secret Rotation Issues

1. Verify secret exists: `gcloud secrets list`
2. Check secret versions: `gcloud secrets versions list <secret-name>`
3. Verify IAM permissions for secret access

### HPA Not Scaling

1. Check metrics server: `kubectl get deployment metrics-server -n kube-system`
2. Verify resource requests are set in pod spec
3. Check HPA events: `kubectl describe hpa mira-hpa`

## CI/CD Integration

The GitHub Actions workflow (`.github/workflows/test.yml`) automatically:

1. Runs tests on all Python versions (3.9-3.12)
2. Validates n8n workflows
3. Checks code coverage (80% threshold)

To trigger a deployment from CI/CD, add these steps to your workflow:

```yaml
- name: Deploy to GCP
  env:
    GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
    GCP_SA_KEY: ${{ secrets.GCP_SA_KEY }}
  run: |
    echo $GCP_SA_KEY | base64 -d > gcp-key.json
    gcloud auth activate-service-account --key-file=gcp-key.json
    ./deploy_gcp.sh deploy
```

## Best Practices

1. **Always test in staging first**: Deploy to staging environment before production
2. **Monitor metrics**: Set up alerts for error rates, latency, and resource usage
3. **Regular secret rotation**: Rotate secrets at least quarterly
4. **Keep rollback images**: Maintain at least 3 previous image versions
5. **Load testing**: Run performance tests before major releases
6. **Compliance checks**: Never skip compliance scanning in production

## Support

For issues or questions:
- Check the main [README.md](README.md)
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- See [DOCUMENTATION.md](DOCUMENTATION.md) for API reference
