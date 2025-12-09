# Deployment Architecture Overview

This document provides visual and conceptual overview of the CI/CD deployment architecture.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GitHub Repository                                │
│  ┌──────────────┐          ┌──────────────┐                             │
│  │   Developer  │          │  Pull Request │                             │
│  │  Push Code   │──────────│   (PR Tests)  │                             │
│  └──────────────┘          └───────┬───────┘                             │
│         │                          │                                     │
│         │ Push to main/master      │ Test Only                           │
│         ▼                          ▼                                     │
│  ┌──────────────────────────────────────┐                               │
│  │    GitHub Actions Workflow           │                               │
│  │  (.github/workflows/deploy-gcp.yml)  │                               │
│  └──────────────────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────┘
         │                          │
         │                          │
         ▼                          ▼
┌─────────────────┐        ┌─────────────────┐
│   Test Job      │        │   Test Job      │
│ ┌─────────────┐ │        │ ┌─────────────┐ │
│ │ Python 3.9  │ │        │ │ Python 3.9  │ │
│ │ Python 3.10 │ │        │ │ Python 3.10 │ │
│ │ Python 3.11 │ │        │ │ Python 3.11 │ │
│ │ Python 3.12 │ │        │ │ Python 3.12 │ │
│ └─────────────┘ │        │ └─────────────┘ │
└────────┬────────┘        └─────────────────┘
         │                         │
         │ All Tests Pass          │ Tests Only
         ▼                         │ (No Deploy)
┌─────────────────┐                │
│ Build & Deploy  │                │
│      Job        │                │
└────────┬────────┘                ▼
         │                    ┌──────────┐
         ▼                    │   End    │
┌─────────────────────────────────────────────────────────────────────────┐
│                    Google Cloud Platform (GCP)                           │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  1. Authentication                                              │    │
│  │     ┌─────────────────────────────────────────────────────┐    │    │
│  │     │  Workload Identity Federation                        │    │    │
│  │     │  (No service account keys needed!)                   │    │    │
│  │     └─────────────────────────────────────────────────────┘    │    │
│  └────────────────────────────────────────────────────────────────┘    │
│         │                                                                │
│         ▼                                                                │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  2. Build Docker Image                                          │    │
│  │     ┌──────────┐                                               │    │
│  │     │Dockerfile│ → Python 3.11 + Flask + Mira App              │    │
│  │     └──────────┘                                               │    │
│  └────────────────────────────────────────────────────────────────┘    │
│         │                                                                │
│         ▼                                                                │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  3. Google Artifact Registry                                    │    │
│  │     ┌───────────────────────────────────────────────────┐      │    │
│  │     │  mira-repo/mira-app:latest                        │      │    │
│  │     │  mira-repo/mira-app:abc123 (commit SHA)           │      │    │
│  │     └───────────────────────────────────────────────────┘      │    │
│  └────────────────────────────────────────────────────────────────┘    │
│         │                                                                │
│         ▼                                                                │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  4. Google Secret Manager                                       │    │
│  │     ┌───────────────────────────────────────────────────┐      │    │
│  │     │  • trello-api-key                                 │      │    │
│  │     │  • trello-api-token                               │      │    │
│  │     │  • jira-api-token                                 │      │    │
│  │     │  • github-token                                   │      │    │
│  │     │  • airtable-api-key                               │      │    │
│  │     │  • google-docs-credentials                        │      │    │
│  │     │  • webhook-secret-key                             │      │    │
│  │     └───────────────────────────────────────────────────┘      │    │
│  └────────────────────────────────────────────────────────────────┘    │
│         │                                                                │
│         ▼                                                                │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  5. Google Cloud Run                                            │    │
│  │     ┌───────────────────────────────────────────────────┐      │    │
│  │     │           Mira Application                        │      │    │
│  │     │  ┌─────────────────────────────────────────┐      │      │    │
│  │     │  │  • Auto-scaling (0-10 instances)        │      │      │    │
│  │     │  │  • Port 5000 (webhook server)           │      │      │    │
│  │     │  │  • Health check: /health                │      │      │    │
│  │     │  │  • CPU: 1, Memory: 512Mi                │      │      │    │
│  │     │  │  • Secrets injected as env vars         │      │      │    │
│  │     │  └─────────────────────────────────────────┘      │      │    │
│  │     └───────────────────────────────────────────────────┘      │    │
│  │                         │                                       │    │
│  │                         ▼                                       │    │
│  │     ┌───────────────────────────────────────────────────┐      │    │
│  │     │  Public URL: https://mira-app-xxx.run.app         │      │    │
│  │     └───────────────────────────────────────────────────┘      │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         External Services                                │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐           │
│  │   Trello  │  │   Jira    │  │  GitHub   │  │ Airtable  │           │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘           │
│        │              │              │              │                   │
│        └──────────────┴──────────────┴──────────────┘                   │
│                       │                                                  │
│                       ▼ Webhooks                                         │
│        ┌──────────────────────────────────────┐                         │
│        │  POST /webhook/{service}             │                         │
│        │  (Signature verification enabled)     │                         │
│        └──────────────────────────────────────┘                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Deployment Flow Step-by-Step

### 1. Developer Push
```
Developer → Git Push → GitHub Repository (main/master branch)
```

### 2. GitHub Actions Triggered
```
Push Event → Workflow Trigger → Two Jobs Start
```

### 3. Test Job (Parallel Execution)
```
┌─ Python 3.9  ─┐
├─ Python 3.10 ─┤  → Install deps → Run tests → Report results
├─ Python 3.11 ─┤
└─ Python 3.12 ─┘
```

### 4. Build & Deploy Job (After Tests Pass)
```
a. Authenticate to GCP
   - Use Workload Identity Federation
   - No service account keys needed
   - Short-lived tokens

b. Build Docker Image
   - Use Dockerfile
   - Tag with commit SHA
   - Tag with 'latest'

c. Push to Artifact Registry
   - Regional storage
   - Lifecycle policies apply
   - Version control

d. Deploy to Cloud Run
   - Pull image from registry
   - Inject secrets from Secret Manager
   - Configure resources (CPU, memory)
   - Set auto-scaling rules
   - Enable health checks

e. Verify Deployment
   - Run smoke test
   - Check health endpoint
   - Output service URL
```

### 5. Application Running
```
Cloud Run Service → Load Balancer → HTTPS → Public URL
                  ↓
           Health Checks (every 30s)
                  ↓
           Auto-scaling (0-10 instances)
                  ↓
           Receive Webhooks from External Services
```

## Data Flow

### Request Flow (Webhook)
```
External Service (Trello/Jira/GitHub)
    ↓
POST /webhook/{service}
    ↓
Cloud Run Load Balancer
    ↓
Mira App Container
    ↓
Signature Verification (if configured)
    ↓
Webhook Handler
    ↓
Orchestrator Agent
    ↓
Specialized Agents (Plan/Risk/Status)
    ↓
Process and Respond
```

### Secret Access Flow
```
Application Needs Secret
    ↓
Request Environment Variable
    ↓
Cloud Run injects from Secret Manager
    ↓
Secret Manager IAM check
    ↓
Return secret value
    ↓
Application uses secret
```

## Security Boundaries

```
┌──────────────────────────────────────────────────┐
│          GitHub Repository (Public/Private)       │
│  • Code is version controlled                    │
│  • NO secrets stored in code                     │
│  • Secrets in GitHub Secrets (encrypted)         │
└────────────────┬─────────────────────────────────┘
                 │ TLS
                 ▼
┌──────────────────────────────────────────────────┐
│          Google Cloud Platform                    │
│  ┌────────────────────────────────────────────┐ │
│  │ Workload Identity Federation              │ │
│  │  • No long-lived credentials              │ │
│  │  • Token-based authentication             │ │
│  └────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────┐ │
│  │ Secret Manager                             │ │
│  │  • Encrypted at rest                       │ │
│  │  • Access control via IAM                  │ │
│  │  • Audit logging                           │ │
│  └────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────┐ │
│  │ Cloud Run                                  │ │
│  │  • Non-root container user                 │ │
│  │  • HTTPS only                              │ │
│  │  • Network isolation                       │ │
│  └────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

## Scaling Behavior

```
Traffic Level          Instances    Behavior
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
No requests            0            Scale to zero (cost = $0)
Low traffic            1-2          Auto-scale up
Medium traffic         3-5          Auto-scale up
High traffic           6-10         Cap at max instances
Very high traffic      10           Reject new requests
                                    (consider increasing max)
```

## Cost Structure

```
Component              Pricing Model              Typical Cost
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cloud Run              CPU + Memory per second    $0-5/month
                      (Free tier: 2M requests)    (low traffic)

Artifact Registry      Storage per GB/month       $0.10/GB/month
                      (First 0.5 GB free)         

Secret Manager         Per 10K accesses           $0.06/10K accesses
                      (First 10K free)            

Networking            Data egress                 $0.12/GB
                      (First 1 GB free)           (Americas)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total                 Estimated                   $0-10/month
                                                  (typical usage)
```

## Monitoring Points

```
┌────────────────────────────────────────────────────┐
│               Monitoring & Logging                  │
│                                                     │
│  1. GitHub Actions                                 │
│     • Workflow execution logs                      │
│     • Test results                                 │
│     • Deployment status                            │
│                                                     │
│  2. Cloud Run Logs                                 │
│     • Application logs                             │
│     • Request logs                                 │
│     • Error logs                                   │
│                                                     │
│  3. Cloud Run Metrics                              │
│     • Request count                                │
│     • Request latency                              │
│     • Instance count                               │
│     • CPU/Memory utilization                       │
│                                                     │
│  4. Health Checks                                  │
│     • /health endpoint                             │
│     • Response time                                │
│     • Success rate                                 │
│                                                     │
│  5. Secret Manager Audit                           │
│     • Secret access logs                           │
│     • Permission changes                           │
│                                                     │
└────────────────────────────────────────────────────┘
```

## Disaster Recovery

```
Issue                   Recovery Method              RTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bad deployment         Rollback to previous          < 5 min
                      revision in Cloud Run

Deleted secret         Restore from version history  < 10 min

Service account        Restore IAM bindings          < 15 min
permission issue

Region outage          Deploy to different region    30-60 min
                      (requires configuration)

Complete GCP failure   Redeploy from GitHub          60-120 min
                      (requires new GCP setup)
```

## Development vs Production

```
Aspect              Development              Production
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Branch              feature/dev branches     main/master
Deployment          Manual or PR-based       Automatic on merge
Min Instances       0 (scale to zero)        0 or 1 (optional)
Max Instances       5                        10
Monitoring          Basic                    Full (alerts)
Secrets             Test/dev values          Production values
Domain              Default Cloud Run URL    Custom domain (optional)
```

## Key Benefits

✅ **Automated**: Push code → Automatic deployment
✅ **Secure**: No service account keys, secrets in Secret Manager
✅ **Scalable**: Auto-scaling from 0 to 10 instances
✅ **Cost-effective**: Pay only for actual usage
✅ **Observable**: Logs, metrics, and health checks
✅ **Reliable**: Automatic rollback on failure
✅ **Fast**: Typical deployment < 5 minutes
✅ **Maintainable**: Infrastructure as code

---

**For detailed setup instructions**: See `docs/GCP_DEPLOYMENT.md`
**For quick reference**: See `docs/CICD_QUICK_REFERENCE.md`
**For implementation details**: See `docs/IMPLEMENTATION_SUMMARY.md`
