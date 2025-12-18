# GitHub Actions CI/CD Quick Reference

Quick reference for managing the Mira deployment workflow.

## Required GitHub Secrets

Configure these secrets in your GitHub repository (Settings → Secrets and variables → Actions):

### Using Workload Identity Federation (Recommended):

| Secret Name | Description | Example |
|------------|-------------|---------|
| `GCP_PROJECT_ID` | Your GCP project ID | `mira-production-12345` |
| `GCP_REGION` | Deployment region | `us-central1` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Full WIF provider path | `projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `GCP_SERVICE_ACCOUNT` | Service account email | `github-actions-deployer@project-id.iam.gserviceaccount.com` |

### Using Service Account Key (Alternative):

| Secret Name | Description |
|------------|-------------|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_REGION` | Deployment region |
| `GCP_SA_KEY` | Full JSON content of service account key |

## Required GCP Permissions

The service account needs these IAM roles:

- `roles/run.admin` - Deploy to Cloud Run
- `roles/artifactregistry.writer` - Push Docker images
- `roles/secretmanager.secretAccessor` - Access secrets
- `roles/iam.serviceAccountUser` - Act as service account

## Required GCP Secrets

Create these secrets in Google Secret Manager:

| Secret Name | Description |
|------------|-------------|
| `trello-api-key` | Trello API key |
| `trello-api-token` | Trello API token |
| `jira-api-token` | Jira API token |
| `github-token` | GitHub personal access token |
| `airtable-api-key` | Airtable API key |
| `google-docs-credentials` | Google service account JSON |
| `webhook-secret-key` | Webhook verification secret |

## Workflow Triggers

| Trigger | Action |
|---------|--------|
| Push to `main`/`master` | Run tests + Deploy to production |
| Pull Request | Run tests only (no deployment) |
| Manual via Actions tab | Run tests + Deploy (if on main) |

## Quick Commands

### View deployment logs:
```bash
gcloud run services logs read mira-app --region=us-central1
```

### Check service status:
```bash
gcloud run services describe mira-app --region=us-central1
```

### List deployed revisions:
```bash
gcloud run revisions list --service=mira-app --region=us-central1
```

### Rollback to previous version:
```bash
gcloud run services update-traffic mira-app \
  --region=us-central1 \
  --to-revisions=REVISION_NAME=100
```

### View GitHub Actions runs:
```bash
# Via web: https://github.com/YOUR_GITHUB_USERNAME/Capstone-Mira/actions
# Replace YOUR_GITHUB_USERNAME with your actual GitHub username or organization name
```

## Deployment Configuration

The deployment is configured in `.github/workflows/deploy-gcp.yml`:

- **Service Name**: `mira-app`
- **Port**: `5000`
- **CPU**: `1`
- **Memory**: `512Mi`
- **Min Instances**: `0` (scales to zero)
- **Max Instances**: `10`
- **Timeout**: `300s`

## Troubleshooting

### Deployment fails with "Permission denied"
- Check service account has all required roles
- Verify Workload Identity Federation is configured correctly

### Tests pass but deployment doesn't trigger
- Ensure you're pushing to `main` or `master` branch
- Check workflow file syntax

### Application secrets not available
- Verify secrets exist in Google Secret Manager
- Check service account has `secretmanager.secretAccessor` role
- Ensure secret names match in workflow file

### Health check fails
- Verify port 5000 is exposed
- Check application logs: `gcloud run services logs read mira-app`

## Security Notes

✅ **Best Practices:**
- Use Workload Identity Federation instead of service account keys
- Rotate secrets regularly
- Enable audit logging
- Use minimum required permissions

❌ **Avoid:**
- Committing service account keys to repository
- Using overly permissive IAM roles
- Storing secrets in code or environment variables

## Cost Optimization

- **Min instances**: Set to `0` to scale to zero when not in use
- **Max instances**: Limit concurrent instances to control costs
- **Memory**: Use smallest size that meets requirements (512Mi)
- **Lifecycle policies**: Clean up old Docker images after 30 days

## Additional Resources

- [Full Deployment Guide](GCP_DEPLOYMENT.md)
- [Google Cloud Run Docs](https://cloud.google.com/run/docs)
- [GitHub Actions for GCP](https://github.com/google-github-actions)
