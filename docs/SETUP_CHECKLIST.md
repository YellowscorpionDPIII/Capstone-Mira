# GCP Deployment Setup Checklist

Use this checklist to set up and verify your GitHub Actions CI/CD pipeline with GCP deployment.

## Prerequisites ✓

- [ ] Google Cloud Platform account created
- [ ] Billing enabled on GCP account
- [ ] GitHub repository admin access
- [ ] `gcloud` CLI installed locally (for initial setup)
- [ ] Basic understanding of Docker and CI/CD concepts

## Phase 1: GCP Project Setup

### 1.1 Create and Configure Project
- [ ] Create GCP project (or select existing one)
- [ ] Note your Project ID: `________________`
- [ ] Set project as default in gcloud CLI
- [ ] Choose deployment region (e.g., us-central1): `________________`

### 1.2 Enable Required APIs
- [ ] Cloud Run API
- [ ] Artifact Registry API
- [ ] Cloud Build API
- [ ] Secret Manager API
- [ ] IAM Credentials API
- [ ] Security Token Service API

**Command:**
```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com iamcredentials.googleapis.com sts.googleapis.com
```

### 1.3 Create Artifact Registry Repository
- [ ] Create Docker repository named `mira-repo`
- [ ] Verify repository is accessible

**Command:**
```bash
gcloud artifacts repositories create mira-repo --repository-format=docker --location=YOUR_REGION --description="Docker repository for Mira application"
```

## Phase 2: Authentication Setup

Choose ONE authentication method:

### Option A: Workload Identity Federation (Recommended) ✓

#### 2.1 Create Service Account
- [ ] Create service account: `github-actions-deployer`
- [ ] Note service account email: `________________`

#### 2.2 Grant IAM Permissions
- [ ] Grant `roles/run.admin`
- [ ] Grant `roles/artifactregistry.writer`
- [ ] Grant `roles/secretmanager.secretAccessor`
- [ ] Grant `roles/iam.serviceAccountUser`

#### 2.3 Configure Workload Identity Federation
- [ ] Create Workload Identity Pool: `github-pool`
- [ ] Create Workload Identity Provider: `github-provider`
- [ ] Configure attribute mapping
- [ ] Set repository condition (YOUR_GITHUB_USERNAME/Capstone-Mira)
- [ ] Allow service account impersonation
- [ ] Note Workload Identity Provider name: `________________`

### Option B: Service Account Key (Alternative)

- [ ] Create service account
- [ ] Grant required permissions
- [ ] Generate service account key
- [ ] Download key JSON file
- [ ] Store key securely (never commit to git!)

## Phase 3: Secret Manager Setup

### 3.1 Create Application Secrets
- [ ] Create `trello-api-key` secret
- [ ] Create `trello-api-token` secret
- [ ] Create `jira-api-token` secret
- [ ] Create `github-token` secret
- [ ] Create `airtable-api-key` secret
- [ ] Create `google-docs-credentials` secret
- [ ] Create `webhook-secret-key` secret

### 3.2 Grant Secret Access
- [ ] Grant service account access to all secrets

**Command Example:**
```bash
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:github-actions-deployer@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Phase 4: GitHub Repository Configuration

### 4.1 Add Repository Secrets

Navigate to: Repository → Settings → Secrets and variables → Actions

**For Workload Identity Federation:**
- [ ] Add `GCP_PROJECT_ID`: Your GCP project ID
- [ ] Add `GCP_REGION`: Your deployment region
- [ ] Add `GCP_WORKLOAD_IDENTITY_PROVIDER`: Full provider path
- [ ] Add `GCP_SERVICE_ACCOUNT`: Service account email

**For Service Account Key:**
- [ ] Add `GCP_PROJECT_ID`: Your GCP project ID
- [ ] Add `GCP_REGION`: Your deployment region
- [ ] Add `GCP_SA_KEY`: Full JSON content

### 4.2 Optional: Configure Branch Protection
- [ ] Enable branch protection on main/master
- [ ] Require status checks before merging
- [ ] Require branches to be up to date
- [ ] Add "test" job as required check

## Phase 5: Initial Deployment

### 5.1 Trigger First Deployment
- [ ] Push code to main/master branch
- [ ] Monitor GitHub Actions workflow
- [ ] Verify "test" job passes
- [ ] Verify "build-and-deploy" job starts
- [ ] Check Docker image builds successfully
- [ ] Verify image pushes to Artifact Registry
- [ ] Confirm Cloud Run deployment succeeds

### 5.2 Verify Deployment
- [ ] Access Cloud Run URL (from workflow output)
- [ ] Test health endpoint: `YOUR_URL/health`
- [ ] Verify response: `{"status": "healthy", "service": "mira"}`
- [ ] Check application functionality

## Phase 6: Monitoring Setup

### 6.1 Configure Monitoring
- [ ] Set up Cloud Run dashboard
- [ ] Configure error alerting
- [ ] Set up log-based metrics
- [ ] Create uptime checks

### 6.2 Test Monitoring
- [ ] View logs in Cloud Console
- [ ] Use gcloud to view logs
- [ ] Verify health checks work
- [ ] Test alert notifications

## Phase 7: Documentation and Handoff

### 7.1 Team Documentation
- [ ] Share GCP project details with team
- [ ] Document where secrets are stored
- [ ] Create runbook for common issues
- [ ] Document rollback procedures

### 7.2 Knowledge Transfer
- [ ] Review deployment process with team
- [ ] Demonstrate how to view logs
- [ ] Show how to manually trigger workflow
- [ ] Explain rollback process

## Verification Commands

After setup, run these commands to verify:

```bash
# Check service is running
gcloud run services describe mira-app --region=YOUR_REGION

# View recent logs
gcloud run services logs read mira-app --region=YOUR_REGION --limit=50

# List revisions
gcloud run revisions list --service=mira-app --region=YOUR_REGION

# Check Docker images
gcloud artifacts docker images list YOUR_REGION-docker.pkg.dev/PROJECT_ID/mira-repo
```

## Troubleshooting

If deployment fails, check:

- [ ] All GitHub secrets are configured correctly
- [ ] GCP service account has required permissions
- [ ] All required GCP APIs are enabled
- [ ] Secrets exist in Secret Manager
- [ ] Workload Identity Federation is configured correctly
- [ ] Repository name matches in attribute condition
- [ ] GitHub Actions workflow syntax is valid
- [ ] Docker builds successfully locally

## Security Checklist

- [ ] Using Workload Identity Federation (no service account keys)
- [ ] Secrets stored in Secret Manager (not in code)
- [ ] Service account has minimum required permissions
- [ ] Branch protection enabled on main/master
- [ ] Audit logging enabled
- [ ] Health checks configured
- [ ] Non-root user in Docker container
- [ ] Dependencies regularly updated

## Cost Monitoring

- [ ] Set up billing alerts
- [ ] Review Cloud Run metrics
- [ ] Monitor Artifact Registry storage
- [ ] Set up budget notifications
- [ ] Configure lifecycle policies for old images

## Maintenance Schedule

- [ ] Weekly: Review deployment logs
- [ ] Monthly: Update base Docker image
- [ ] Quarterly: Rotate secrets
- [ ] Quarterly: Review IAM permissions
- [ ] Annually: Security audit

## Success Criteria

✅ All items above checked
✅ Application deploys automatically on push
✅ Tests pass before deployment
✅ Health endpoint returns 200
✅ Logs are accessible
✅ Team can view and manage deployment
✅ Monitoring and alerts configured
✅ Documentation complete

## Support Resources

- **Comprehensive Guide**: `docs/GCP_DEPLOYMENT.md`
- **Quick Reference**: `docs/CICD_QUICK_REFERENCE.md`
- **Implementation Details**: `docs/IMPLEMENTATION_SUMMARY.md`
- **GitHub Actions Logs**: Repository → Actions tab
- **GCP Console**: https://console.cloud.google.com
- **Cloud Run Dashboard**: Cloud Run → Services → mira-app

## Notes

Use this space for project-specific notes:

```
Project ID: ___________________________
Region: ________________________________
Service URL: ___________________________
Team Contact: __________________________
Setup Date: ____________________________
```

---

**Last Updated**: December 2024
**Document Version**: 1.0
