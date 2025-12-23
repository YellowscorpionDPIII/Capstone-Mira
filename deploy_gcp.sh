#!/bin/bash

# deploy_gcp.sh - GCP Deployment Script with Secret Rotation and Rollback
# This script handles deployment to Google Cloud Platform with enhanced capabilities:
# - Secret rotation using gcloud secrets versions access
# - Cloud Run rollback functionality
# - Error handling and logging

set -e  # Exit on error

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-mira-project}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${CLOUD_RUN_SERVICE:-mira-service}"
IMAGE_NAME="${IMAGE_NAME:-gcr.io/$PROJECT_ID/mira}"
LOG_FILE="deployment.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

# Function to rotate secrets
rotate_secret() {
    local secret_name=$1
    log "Rotating secret: $secret_name"
    
    # Get the latest version of the secret
    local latest_version=$(gcloud secrets versions list "$secret_name" \
        --project="$PROJECT_ID" \
        --filter="state:ENABLED" \
        --sort-by="~created_time" \
        --limit=1 \
        --format="value(name)")
    
    if [ -z "$latest_version" ]; then
        log_error "No enabled versions found for secret: $secret_name"
        return 1
    fi
    
    # Access the latest secret version
    local secret_value=$(gcloud secrets versions access "$latest_version" \
        --secret="$secret_name" \
        --project="$PROJECT_ID")
    
    if [ $? -eq 0 ]; then
        log "Successfully accessed secret $secret_name version $latest_version"
        export "${secret_name}_VALUE=$secret_value"
        return 0
    else
        log_error "Failed to access secret: $secret_name"
        return 1
    fi
}

# Function to get current Cloud Run image tag
get_current_image() {
    local current_image=$(gcloud run services describe "$SERVICE_NAME" \
        --project="$PROJECT_ID" \
        --region="$REGION" \
        --format="value(spec.template.spec.containers[0].image)" 2>/dev/null)
    
    echo "$current_image"
}

# Function to rollback Cloud Run service
rollback_service() {
    local previous_image=$1
    
    if [ -z "$previous_image" ]; then
        log_error "No previous image specified for rollback"
        return 1
    fi
    
    log_warning "Initiating rollback to previous image: $previous_image"
    
    gcloud run services update "$SERVICE_NAME" \
        --project="$PROJECT_ID" \
        --region="$REGION" \
        --image="$previous_image" \
        --quiet
    
    if [ $? -eq 0 ]; then
        log "Rollback completed successfully"
        return 0
    else
        log_error "Rollback failed"
        return 1
    fi
}

# Function to deploy to Cloud Run
deploy_to_cloud_run() {
    local image_tag=$1
    
    log "Deploying to Cloud Run: $SERVICE_NAME"
    log "Image: $image_tag"
    
    # Store current image before deployment for potential rollback
    local previous_image=$(get_current_image)
    if [ -n "$previous_image" ]; then
        log "Previous image stored for rollback: $previous_image"
        export ROLLBACK_IMAGE="$previous_image"
    fi
    
    # Deploy to Cloud Run
    gcloud run deploy "$SERVICE_NAME" \
        --project="$PROJECT_ID" \
        --region="$REGION" \
        --image="$image_tag" \
        --platform=managed \
        --allow-unauthenticated \
        --quiet
    
    if [ $? -eq 0 ]; then
        log "Deployment successful"
        
        # Verify deployment health
        log "Verifying deployment health..."
        sleep 10  # Wait for service to stabilize
        
        local service_url=$(gcloud run services describe "$SERVICE_NAME" \
            --project="$PROJECT_ID" \
            --region="$REGION" \
            --format="value(status.url)")
        
        if [ -n "$service_url" ]; then
            log "Service URL: $service_url"
            
            # Optional: Add health check
            if command -v curl &> /dev/null; then
                http_status=$(curl -s -o /dev/null -w "%{http_code}" "$service_url" || echo "000")
                if [ "$http_status" -ge 200 ] && [ "$http_status" -lt 400 ]; then
                    log "Health check passed (HTTP $http_status)"
                else
                    log_warning "Health check returned HTTP $http_status"
                    log_warning "Consider rollback if service is not functioning correctly"
                fi
            fi
        fi
        
        return 0
    else
        log_error "Deployment failed"
        
        # Offer automatic rollback
        if [ -n "$ROLLBACK_IMAGE" ]; then
            log_warning "Attempting automatic rollback..."
            rollback_service "$ROLLBACK_IMAGE"
        fi
        
        return 1
    fi
}

# Function to run compliance scanning with Risk Assessor
run_compliance_scan() {
    log "Running compliance scanning with Risk Assessor agent..."
    
    # Check if Risk Assessor is available
    if [ -f "governance/risk_assessor.py" ]; then
        # Run risk assessment
        python3 -c "
import sys
sys.path.insert(0, '.')
from governance.risk_assessor import RiskAssessor
from datetime import datetime

assessor = RiskAssessor()
result = assessor.assess({
    'deployment': {
        'service': '$SERVICE_NAME',
        'image': '$IMAGE_NAME',
        'timestamp': datetime.now().isoformat()
    }
})

print(f'Compliance Score: {result.get(\"compliance_score\", \"N/A\")}')
print(f'Risk Level: {result.get(\"risk_level\", \"N/A\")}')

if result.get('risks'):
    print('\\nIdentified Risks:')
    for risk in result['risks']:
        print(f'  - {risk}')

if result.get('compliance_score', 1.0) < 0.8:
    print('\\nWARNING: Compliance score below threshold!')
    sys.exit(1)
"
        
        if [ $? -eq 0 ]; then
            log "Compliance scan passed"
            return 0
        else
            log_error "Compliance scan failed - Review risks before proceeding"
            return 1
        fi
    else
        log_warning "Risk Assessor not found, skipping compliance scan"
        return 0
    fi
}

# Main deployment flow
main() {
    log "=== Starting GCP Deployment ==="
    log "Project: $PROJECT_ID"
    log "Region: $REGION"
    log "Service: $SERVICE_NAME"
    
    # Rotate secrets before deployment
    log "=== Secret Rotation Phase ==="
    
    # Example secrets to rotate (customize based on your needs)
    SECRETS=("api-key" "database-password" "jwt-secret")
    
    for secret in "${SECRETS[@]}"; do
        if gcloud secrets describe "$secret" --project="$PROJECT_ID" &>/dev/null; then
            rotate_secret "$secret" || log_warning "Failed to rotate $secret, continuing..."
        else
            log_warning "Secret $secret does not exist, skipping..."
        fi
    done
    
    # Run compliance scanning
    log "=== Compliance Scanning Phase ==="
    run_compliance_scan
    if [ $? -ne 0 ]; then
        log_error "Compliance scan failed. Set SKIP_COMPLIANCE=true to bypass."
        if [ "$SKIP_COMPLIANCE" != "true" ]; then
            exit 1
        fi
    fi
    
    # Build and deploy
    log "=== Deployment Phase ==="
    
    # Use provided image or build new one
    if [ -z "$IMAGE_TAG" ]; then
        IMAGE_TAG="$IMAGE_NAME:$(date +%Y%m%d-%H%M%S)"
        log "No IMAGE_TAG provided, using: $IMAGE_TAG"
    else
        IMAGE_TAG="$IMAGE_NAME:$IMAGE_TAG"
    fi
    
    # Deploy to Cloud Run
    deploy_to_cloud_run "$IMAGE_TAG"
    
    if [ $? -eq 0 ]; then
        log "=== Deployment Completed Successfully ==="
        exit 0
    else
        log_error "=== Deployment Failed ==="
        exit 1
    fi
}

# Handle script arguments
case "${1:-deploy}" in
    deploy)
        main
        ;;
    rollback)
        ROLLBACK_TO="${2:-}"
        if [ -z "$ROLLBACK_TO" ]; then
            log_error "Usage: $0 rollback <image-tag>"
            exit 1
        fi
        rollback_service "$IMAGE_NAME:$ROLLBACK_TO"
        ;;
    rotate-secrets)
        log "Rotating all secrets..."
        SECRETS=("api-key" "database-password" "jwt-secret")
        for secret in "${SECRETS[@]}"; do
            if gcloud secrets describe "$secret" --project="$PROJECT_ID" &>/dev/null; then
                rotate_secret "$secret"
            fi
        done
        ;;
    *)
        echo "Usage: $0 {deploy|rollback <image-tag>|rotate-secrets}"
        exit 1
        ;;
esac
