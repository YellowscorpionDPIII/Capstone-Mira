# GCP Deployment Guide

This guide provides step-by-step instructions for setting up continuous deployment of the Mira application to Google Cloud Platform (GCP) using GitHub Actions.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [GCP Setup](#gcp-setup)
3. [GitHub Repository Configuration](#github-repository-configuration)
4. [Deployment Workflow](#deployment-workflow)
5. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
6. [Security Best Practices](#security-best-practices)

## Prerequisites

Before setting up deployment, ensure you have:

- A Google Cloud Platform account
- A GitHub repository with admin access
- GCP CLI (`gcloud`) installed locally (for initial setup)
- Appropriate billing enabled on your GCP project

## GCP Setup

### 1. Create a GCP Project

```bash
# Create a new project (or use an existing one)
export PROJECT_ID="your-project-id"
gcloud projects create $PROJECT_ID --name="Mira Application"

# Set the project as default
gcloud config set project $PROJECT_ID
```

### 2. Enable Required APIs

```bash
# Enable necessary GCP services
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com
```

### 3. Create Artifact Registry Repository

```bash
# Set your region (e.g., us-central1, us-east1, europe-west1)
export REGION="us-central1"

# Create Docker repository in Artifact Registry
gcloud artifacts repositories create mira-repo \
  --repository-format=docker \
  --location=$REGION \
  --description="Docker repository for Mira application"
```

### 4. Set Up Service Account (Option A: Recommended - Workload Identity Federation)

Workload Identity Federation is the recommended approach as it doesn't require managing service account keys.

```bash
# Create a service account for GitHub Actions
gcloud iam service-accounts create github-actions-deployer \
  --display-name="GitHub Actions Deployer" \
  --description="Service account for GitHub Actions to deploy to Cloud Run"

# Grant necessary permissions to the service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Create Workload Identity Pool
gcloud iam workload-identity-pools create github-pool \
  --location="global" \
  --display-name="GitHub Actions Pool"

# Get the Workload Identity Pool ID
export WORKLOAD_IDENTITY_POOL_ID=$(gcloud iam workload-identity-pools describe github-pool \
  --location="global" \
  --format="value(name)")

# Create Workload Identity Provider
# Replace YOUR_GITHUB_USERNAME with your actual GitHub username or organization name
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='YOUR_GITHUB_USERNAME/Capstone-Mira'"

# Allow GitHub Actions to impersonate the service account
# Replace YOUR_GITHUB_USERNAME with your actual GitHub username or organization name
gcloud iam service-accounts add-iam-policy-binding \
  github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_POOL_ID}/attribute.repository/YOUR_GITHUB_USERNAME/Capstone-Mira"

# Get the Workload Identity Provider name (for GitHub Secrets)
gcloud iam workload-identity-pools providers describe github-provider \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --format="value(name)"
```

### 5. Set Up Service Account (Option B: Service Account Key - Less Secure)

If you cannot use Workload Identity Federation, you can use a service account key:

```bash
# Create a service account
gcloud iam service-accounts create github-actions-deployer \
  --display-name="GitHub Actions Deployer"

# Grant necessary permissions (same as above)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Create and download service account key
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com

# Display the key content (you'll need to copy this to GitHub Secrets)
cat key.json
```

**Important:** Store the key.json file securely and never commit it to version control. Delete it after adding to GitHub Secrets.

### 6. Create Secrets in Google Secret Manager

Store your application secrets in Google Secret Manager:

```bash
# Create secrets for your integrations
echo -n "your-trello-api-key" | gcloud secrets create trello-api-key --data-file=-
echo -n "your-trello-api-token" | gcloud secrets create trello-api-token --data-file=-
echo -n "your-jira-api-token" | gcloud secrets create jira-api-token --data-file=-
echo -n "your-github-token" | gcloud secrets create github-token --data-file=-
echo -n "your-airtable-api-key" | gcloud secrets create airtable-api-key --data-file=-
echo -n "your-webhook-secret-key" | gcloud secrets create webhook-secret-key --data-file=-

# For Google Docs credentials, upload the JSON file
gcloud secrets create google-docs-credentials --data-file=path/to/credentials.json

# Grant the service account access to secrets
for secret in trello-api-key trello-api-token jira-api-token github-token airtable-api-key google-docs-credentials webhook-secret-key; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done
```

## GitHub Repository Configuration

### Required Repository Secrets

Navigate to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret.

#### For Workload Identity Federation (Option A - Recommended):

Add the following secrets:

1. **GCP_PROJECT_ID**: Your GCP project ID
   ```
   your-project-id
   ```

2. **GCP_REGION**: Your deployment region
   ```
   us-central1
   ```

3. **GCP_WORKLOAD_IDENTITY_PROVIDER**: Full provider name from step 4
   ```
   projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider
   ```

4. **GCP_SERVICE_ACCOUNT**: Service account email
   ```
   github-actions-deployer@your-project-id.iam.gserviceaccount.com
   ```

#### For Service Account Key (Option B):

Add the following secrets:

1. **GCP_PROJECT_ID**: Your GCP project ID
2. **GCP_REGION**: Your deployment region
3. **GCP_SA_KEY**: Content of your service account key JSON file (entire JSON content)

### Optional: Configure Branch Protection

For production deployments, consider setting up branch protection:

1. Go to Settings → Branches → Add rule
2. Branch name pattern: `main` (or `master`)
3. Enable:
   - Require status checks to pass before merging
   - Require branches to be up to date before merging
   - Select the "test" job as a required check

## Deployment Workflow

The deployment workflow (`.github/workflows/deploy-gcp.yml`) runs automatically:

### Triggers

- **Push to main/master**: Triggers full deployment
- **Pull Request**: Runs tests only (no deployment)
- **Manual**: Can be triggered via "Actions" tab → "Deploy to GCP" → "Run workflow"

### Workflow Steps

1. **Test**: Runs tests on Python 3.9, 3.10, 3.11, 3.12
2. **Build**: Creates Docker image with application
3. **Push**: Uploads image to Google Artifact Registry
4. **Deploy**: Deploys to Google Cloud Run
5. **Smoke Test**: Verifies deployment is accessible

### Accessing Application Secrets

The application automatically receives secrets from Google Secret Manager as environment variables:

- `TRELLO_API_KEY`
- `TRELLO_API_TOKEN`
- `JIRA_API_TOKEN`
- `GITHUB_TOKEN`
- `AIRTABLE_API_KEY`
- `GOOGLE_DOCS_CREDENTIALS`
- `WEBHOOK_SECRET_KEY`

Update your `mira/config/settings.py` to read from environment variables:

```python
import os
import json

def get_config(config_path=None):
    config = {}
    
    # Load from environment variables
    if os.getenv('TRELLO_API_KEY'):
        config['integrations'] = config.get('integrations', {})
        config['integrations']['trello'] = {
            'enabled': True,
            'api_key': os.getenv('TRELLO_API_KEY'),
            'api_token': os.getenv('TRELLO_API_TOKEN'),
        }
    
    # Similar for other integrations...
    
    return config
```

## Monitoring and Troubleshooting

### View Logs

```bash
# View Cloud Run logs
gcloud run services logs read mira-app --region=$REGION

# Tail logs in real-time
gcloud run services logs tail mira-app --region=$REGION
```

### Check Service Status

```bash
# Get service details
gcloud run services describe mira-app --region=$REGION

# List all revisions
gcloud run revisions list --service=mira-app --region=$REGION
```

### Common Issues

#### 1. Authentication Errors

- Verify service account has correct permissions
- Check that Workload Identity Provider is correctly configured
- Ensure GitHub repository name matches in attribute condition

#### 2. Image Build Failures

- Check Dockerfile syntax
- Verify all dependencies are in requirements.txt
- Review GitHub Actions logs for build errors

#### 3. Deployment Failures

- Verify secrets exist in Secret Manager
- Check Cloud Run service quotas
- Ensure region is correctly specified

#### 4. Application Errors

- Check Cloud Run logs: `gcloud run services logs read mira-app`
- Verify environment variables are set correctly
- Test locally with Docker: `docker build -t mira . && docker run -p 5000:5000 mira`

### Rollback

If a deployment fails, rollback to a previous revision:

```bash
# List revisions
gcloud run revisions list --service=mira-app --region=$REGION

# Rollback to specific revision
gcloud run services update-traffic mira-app \
  --region=$REGION \
  --to-revisions=mira-app-00001-abc=100
```

## Security Best Practices

### 1. Use Workload Identity Federation

Prefer Workload Identity Federation over service account keys to avoid managing long-lived credentials.

### 2. Principle of Least Privilege

Grant only the minimum permissions required:
- `roles/run.admin` for Cloud Run deployment
- `roles/artifactregistry.writer` for pushing images
- `roles/secretmanager.secretAccessor` for accessing secrets

### 3. Rotate Secrets Regularly

```bash
# Add a new version to an existing secret
echo -n "new-secret-value" | gcloud secrets versions add SECRET_NAME --data-file=-

# Disable old versions
gcloud secrets versions disable VERSION_NUMBER --secret=SECRET_NAME
```

### 4. Enable VPC Service Controls

For production environments, consider enabling VPC Service Controls to restrict data exfiltration.

### 5. Monitor Access

Enable audit logging:

```bash
# View audit logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=mira-app" \
  --limit=50 \
  --format=json
```

### 6. Network Security

- Use Cloud Armor for DDoS protection
- Implement IP allowlisting if needed
- Enable Cloud Run Authentication for sensitive endpoints

## Cost Optimization

### Cloud Run Pricing

- Charges based on CPU and memory usage
- `--min-instances=0`: Scales to zero when not in use
- `--max-instances=10`: Limits concurrent instances

### Artifact Registry

- Stores Docker images
- Consider setting up lifecycle policies to delete old images

```bash
# Create lifecycle policy to delete images older than 30 days
cat > policy.json << EOF
{
  "rules": [{
    "action": {"type": "Delete"},
    "condition": {
      "olderThan": "2592000s"
    }
  }]
}
EOF

gcloud artifacts repositories set-cleanup-policies mira-repo \
  --location=$REGION \
  --policy=policy.json
```

## Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Google Artifact Registry Documentation](https://cloud.google.com/artifact-registry/docs)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [GitHub Actions for GCP](https://github.com/google-github-actions)

## Support

For issues or questions:
1. Check GitHub Actions logs
2. Review Cloud Run logs: `gcloud run services logs read mira-app`
3. Open an issue on GitHub
4. Contact the development team

---

**Last Updated**: December 2024
