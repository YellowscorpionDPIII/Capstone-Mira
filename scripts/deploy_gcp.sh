#!/bin/bash
# Deploy Mira platform to Google Cloud Platform
# Usage: ./scripts/deploy_gcp.sh --env=<staging|production>

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="staging"
PROJECT_ID=""
REGION="us-central1"
SERVICE_NAME="mira-platform"

# Parse command line arguments
for arg in "$@"; do
    case $arg in
        --env=*)
            ENVIRONMENT="${arg#*=}"
            shift
            ;;
        --project=*)
            PROJECT_ID="${arg#*=}"
            shift
            ;;
        --region=*)
            REGION="${arg#*=}"
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --env=<staging|production>  Environment to deploy to (default: staging)"
            echo "  --project=<project-id>      GCP project ID"
            echo "  --region=<region>           GCP region (default: us-central1)"
            echo "  --help                      Display this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown argument: $arg${NC}"
            exit 1
            ;;
    esac
done

# Validate environment
if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    echo -e "${RED}Error: Environment must be 'staging' or 'production'${NC}"
    exit 1
fi

echo -e "${GREEN}=== Deploying Mira Platform to GCP ===${NC}"
echo -e "Environment: ${YELLOW}$ENVIRONMENT${NC}"
echo -e "Region: ${YELLOW}$REGION${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not found. Please install Google Cloud SDK.${NC}"
    exit 1
fi

# Get project ID if not specified
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}Error: No GCP project configured. Use --project=<project-id> or set default project.${NC}"
        exit 1
    fi
fi

echo -e "Project ID: ${YELLOW}$PROJECT_ID${NC}"

# Confirm deployment
echo -e "${YELLOW}Are you sure you want to deploy to $ENVIRONMENT? (y/n)${NC}"
read -r confirmation
if [[ "$confirmation" != "y" ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# Set service name with environment suffix
SERVICE_NAME="$SERVICE_NAME-$ENVIRONMENT"

echo -e "${GREEN}Step 1: Running tests...${NC}"
python -m pytest mira/tests/ --benchmark-disable --cov=mira/agents --cov=mira/core --cov-fail-under=95
if [ $? -ne 0 ]; then
    echo -e "${RED}Tests failed! Aborting deployment.${NC}"
    exit 1
fi
echo -e "${GREEN}Tests passed!${NC}"

echo -e "${GREEN}Step 2: Running CodeQL security scan...${NC}"
if command -v codeql &> /dev/null; then
    echo "Running CodeQL database creation and analysis..."
    if [ -d "codeql-db" ]; then
        rm -rf codeql-db
    fi
    codeql database create codeql-db --language=python --source-root=. || {
        echo -e "${YELLOW}Warning: CodeQL database creation failed. Ensure code quality manually.${NC}"
    }
    if [ -d "codeql-db" ]; then
        codeql database analyze codeql-db --format=sarif-latest --output=results.sarif || {
            echo -e "${YELLOW}Warning: CodeQL analysis completed with issues. Review results.sarif${NC}"
        }
        if [ -f "results.sarif" ]; then
            echo -e "${GREEN}CodeQL scan completed. Review results.sarif for findings.${NC}"
        fi
    fi
else
    echo -e "${YELLOW}Warning: CodeQL not found locally.${NC}"
    echo -e "${YELLOW}Security scans must pass in CI/CD pipeline before production deployment.${NC}"
    echo -e "${YELLOW}For staging deployment, ensure manual security review is completed.${NC}"
fi

echo -e "${GREEN}Step 3: Building Docker image...${NC}"
IMAGE_TAG="gcr.io/$PROJECT_ID/$SERVICE_NAME:$(git rev-parse --short HEAD)"
docker build -t "$IMAGE_TAG" .
if [ $? -ne 0 ]; then
    echo -e "${RED}Docker build failed!${NC}"
    exit 1
fi
echo -e "${GREEN}Docker image built: $IMAGE_TAG${NC}"

echo -e "${GREEN}Step 4: Pushing image to Google Container Registry...${NC}"
docker push "$IMAGE_TAG"
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to push image!${NC}"
    exit 1
fi
echo -e "${GREEN}Image pushed successfully${NC}"

echo -e "${GREEN}Step 5: Deploying to Cloud Run...${NC}"
gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_TAG" \
    --platform managed \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --allow-unauthenticated \
    --set-env-vars "ENVIRONMENT=$ENVIRONMENT" \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 300

if [ $? -ne 0 ]; then
    echo -e "${RED}Deployment failed!${NC}"
    exit 1
fi

echo -e "${GREEN}Step 6: Getting service URL...${NC}"
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --format 'value(status.url)')

echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo -e "Service URL: ${YELLOW}$SERVICE_URL${NC}"
echo -e "Health check: ${YELLOW}$SERVICE_URL/health${NC}"
echo ""
echo -e "${GREEN}Testing health endpoint...${NC}"
sleep 5
curl -f "$SERVICE_URL/health" || echo -e "${YELLOW}Warning: Health check failed${NC}"

echo ""
echo -e "${GREEN}Deployment Summary:${NC}"
echo -e "  Environment: $ENVIRONMENT"
echo -e "  Service: $SERVICE_NAME"
echo -e "  Image: $IMAGE_TAG"
echo -e "  URL: $SERVICE_URL"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo -e "  1. Verify webhooks: curl -X POST $SERVICE_URL/webhook/n8n -H 'Content-Type: application/json' -H 'X-Operator-Key: <your-key>' -d '{\"test\":\"data\"}'"
echo -e "  2. Monitor logs: gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\" --limit 50 --project $PROJECT_ID"
echo -e "  3. View metrics: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/metrics?project=$PROJECT_ID"
