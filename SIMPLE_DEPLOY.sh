#!/bin/bash

# AI Assurance Lab - Simple Deployment Script
# Uses Docker locally to build, then deploys to AppRunner

set -e

REGION="us-east-1"
ACCOUNT_ID="004878717866"
SERVICE_NAME="ai-assurance-lab"
REPO_NAME="ai-assurance-lab"

echo "════════════════════════════════════════════════════════════"
echo "🚀 AI ASSURANCE LAB - SIMPLE DEPLOYMENT"
echo "════════════════════════════════════════════════════════════"
echo ""

# Step 1: Ensure ECR repo exists
echo "Step 1: Checking ECR repository..."
aws ecr describe-repositories \
  --repository-names $REPO_NAME \
  --region $REGION 2>/dev/null || \
aws ecr create-repository \
  --repository-name $REPO_NAME \
  --region $REGION

echo "✅ ECR repository ready"

# Step 2: Build Docker image locally
echo ""
echo "Step 2: Building Docker image locally..."
docker build -t $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest .
echo "✅ Docker image built"

# Step 3: Login to ECR and push
echo ""
echo "Step 3: Pushing image to ECR..."
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest
echo "✅ Image pushed to ECR"

# Step 4: Create or update AppRunner service
echo ""
echo "Step 4: Creating/updating AppRunner service..."

SERVICE_ARN=$(aws apprunner list-services \
  --region $REGION \
  --query "ServiceSummaryList[?ServiceName=='$SERVICE_NAME'].ServiceArn" \
  --output text 2>/dev/null || echo "")

if [ -z "$SERVICE_ARN" ]; then
  echo "  Creating new AppRunner service..."
  
  # Create new service
  SERVICE_RESPONSE=$(aws apprunner create-service \
    --service-name $SERVICE_NAME \
    --source-configuration ImageRepository='{ImageIdentifier='$ACCOUNT_ID'.dkr.ecr.'$REGION'.amazonaws.com/'$REPO_NAME':latest,ImageRepositoryType=ECR,ImageConfiguration={Port=8080}}' \
    --instance-role-arn "arn:aws:iam::$ACCOUNT_ID:role/ai-assurance-lab-apprunner-role" \
    --region $REGION \
    --output json)
  
  SERVICE_ARN=$(echo "$SERVICE_RESPONSE" | jq -r '.Service.ServiceArn')
  echo "  Service ARN: $SERVICE_ARN"
else
  echo "  Service exists, updating..."
  
  aws apprunner update-service \
    --service-arn "$SERVICE_ARN" \
    --source-configuration ImageRepository='{ImageIdentifier='$ACCOUNT_ID'.dkr.ecr.'$REGION'.amazonaws.com/'$REPO_NAME':latest,ImageRepositoryType=ECR,ImageConfiguration={Port=8080}}' \
    --region $REGION > /dev/null
fi

echo "✅ AppRunner service configured"

# Step 5: Wait for service to be ready
echo ""
echo "Step 5: Waiting for AppRunner service to be RUNNING..."
MAX_WAIT=300
ELAPSED=0
STATUS="OPERATION_IN_PROGRESS"

while [ "$STATUS" != "RUNNING" ] && [ $ELAPSED -lt $MAX_WAIT ]; do
  STATUS=$(aws apprunner describe-service \
    --service-arn "$SERVICE_ARN" \
    --region $REGION \
    --query 'Service.Status' \
    --output text)
  
  echo "  Status: $STATUS"
  
  if [ "$STATUS" = "RUNNING" ]; then
    break
  fi
  
  sleep 10
  ELAPSED=$((ELAPSED + 10))
done

if [ "$STATUS" != "RUNNING" ]; then
  echo "⚠️  Service took too long to start. Check AWS console."
else
  echo "✅ Service is RUNNING"
fi

# Step 6: Get service URL
echo ""
echo "Step 6: Getting service URL..."
SERVICE_URL=$(aws apprunner describe-service \
  --service-arn "$SERVICE_ARN" \
  --region $REGION \
  --query 'Service.ServiceUrl' \
  --output text)

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ DEPLOYMENT COMPLETE!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "🌐 Lab URL: https://$SERVICE_URL"
echo ""
echo "NEXT STEPS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Create students.csv with student email addresses"
echo "2. Run: bash CREATE_STUDENTS_ONLY.sh students.csv"
echo "3. Share the Lab URL with students"
echo ""
echo "SAVE THIS URL: https://$SERVICE_URL"
echo "════════════════════════════════════════════════════════════"
echo ""

# Save deployment info
cat > DEPLOYMENT_INFO.txt << INFO
AI Assurance Lab Deployment Information
========================================
Date: $(date)
Region: $REGION
Service Name: $SERVICE_NAME
Service ARN: $SERVICE_ARN
Lab URL: https://$SERVICE_URL

Next Steps:
1. Create students.csv
2. Run: bash CREATE_STUDENTS_ONLY.sh students.csv
3. Share Lab URL with students

To delete this deployment (save costs):
  aws apprunner delete-service --service-arn "$SERVICE_ARN" --region us-east-1

INFO

echo "Deployment info saved to: DEPLOYMENT_INFO.txt"
