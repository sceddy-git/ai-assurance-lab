#!/bin/bash

# AI Assurance Lab - AWS-Native Deployment (No Docker Desktop)
# This script builds the Docker image using AWS CodeBuild and deploys to AppRunner

set -e

REGION="us-east-1"
ACCOUNT_ID="004878717866"
PROJECT_NAME="ai-assurance-lab-build"
SERVICE_NAME="ai-assurance-lab"
PROJECT_DIR="/Users/sceddy/Documents/AI Assurance MCP day"

echo "════════════════════════════════════════════════════════════"
echo "🚀 AWS-NATIVE DEPLOYMENT (No Docker Desktop Required)"
echo "════════════════════════════════════════════════════════════"
echo ""

# Step 1: Create CodeBuild project
echo "Step 1: Setting up CodeBuild project..."

# First check if project exists
EXISTING_PROJECT=$(aws codebuild batch-get-projects --names $PROJECT_NAME --region $REGION --query 'projects[0].name' --output text 2>/dev/null)

if [ "$EXISTING_PROJECT" == "$PROJECT_NAME" ]; then
  echo "  (Project already exists)"
else
  # Create temporary S3 bucket for source
  TEMP_BUCKET="ai-assurance-lab-temp-$(date +%s)"
  echo "  Creating temporary S3 bucket: $TEMP_BUCKET"
  aws s3 mb "s3://$TEMP_BUCKET" --region $REGION 2>/dev/null || true
  
  # Create project with valid S3 source
  aws codebuild create-project \
    --name $PROJECT_NAME \
    --source type=S3,location="s3://$TEMP_BUCKET/dummy.zip" \
    --artifacts type=NO_ARTIFACTS \
    --environment type=LINUX_CONTAINER,image=aws/codebuild/standard:7.0,computeType=BUILD_GENERAL1_MEDIUM,privilegedMode=true \
    --service-role "arn:aws:iam::$ACCOUNT_ID:role/ai-assurance-lab-codebuild-role" \
    --region $REGION 2>/dev/null || echo "  (Could not create project)"
fi

echo "✅ CodeBuild project ready"

# Step 2: Create buildspec.yml
echo ""
echo "Step 2: Creating buildspec.yml..."
cat > "$PROJECT_DIR/buildspec.yml" << 'BUILDSPEC'
version: 0.2

phases:
  pre_build:
    commands:
      - echo Logging in to Amazon ECR...
      - aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 004878717866.dkr.ecr.us-east-1.amazonaws.com
      - REPOSITORY_URI=004878717866.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab
      - IMAGE_TAG=latest
  
  build:
    commands:
      - echo Build started on `date`
      - echo Building the Docker image...
      - docker build -t $REPOSITORY_URI:latest .
  
  post_build:
    commands:
      - echo Build completed on `date`
      - echo Pushing the Docker image...
      - docker push $REPOSITORY_URI:latest
      - echo "✅ Image pushed to ECR"

cache:
  paths:
    - '/root/.cache/pip/**/*'
BUILDSPEC

echo "✅ buildspec.yml created"

# Step 3: Upload source to S3 and trigger build
echo ""
echo "Step 3: Uploading project and triggering CodeBuild..."
BUCKET_NAME="ai-assurance-lab-build-$(date +%s)"
aws s3 mb s3://$BUCKET_NAME --region $REGION 2>/dev/null || true

cd "$PROJECT_DIR"

# Create a clean zip without unnecessary files
zip -r source.zip . \
  -x "venv/*" \
  ".git/*" \
  "__pycache__/*" \
  "*.pyc" \
  "*.egg-info/*" \
  ".pytest_cache/*" \
  ".DS_Store" \
  ".cursor/*" > /dev/null 2>&1

aws s3 cp source.zip s3://$BUCKET_NAME/ --region $REGION > /dev/null

# Trigger CodeBuild
BUILD_RESPONSE=$(aws codebuild start-build \
  --project-name $PROJECT_NAME \
  --source-location-override s3://$BUCKET_NAME/source.zip \
  --region $REGION \
  --output json)

BUILD_ID=$(echo "$BUILD_RESPONSE" | jq -r '.build.id')

echo "✅ Build triggered: $BUILD_ID"
echo "   Monitor at: https://console.aws.amazon.com/codesuite/codebuild/projects/$PROJECT_NAME/history"

# Step 4: Wait for build to complete
echo ""
echo "Step 4: Waiting for build to complete (this takes 3-5 minutes)..."
BUILD_COMPLETE=false
while [ "$BUILD_COMPLETE" = false ]; do
  BUILD_INFO=$(aws codebuild batch-get-builds \
    --ids $BUILD_ID \
    --region $REGION \
    --output json)
  
  STATUS=$(echo "$BUILD_INFO" | jq -r '.builds[0].buildStatus')
  
  case $STATUS in
    SUCCEEDED)
      echo "✅ Build succeeded!"
      BUILD_COMPLETE=true
      ;;
    FAILED)
      echo "❌ Build failed! Check logs:"
      echo "https://console.aws.amazon.com/codesuite/codebuild/projects/$PROJECT_NAME/history"
      exit 1
      ;;
    *)
      echo "  Current status: $STATUS"
      sleep 10
      ;;
  esac
done

# Step 5: Create or update AppRunner service
echo ""
echo "Step 5: Creating/updating AppRunner service..."

# Try to create service
SERVICE_RESPONSE=$(aws apprunner create-service \
  --service-name $SERVICE_NAME \
  --source-configuration "ImageRepository={ImageIdentifier=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/ai-assurance-lab:latest,ImageRepositoryType=ECR,ImageConfiguration={Port=8080}}" \
  --instance-configuration "Cpu=1024,Memory=2048,InstanceRoleArn=arn:aws:iam::$ACCOUNT_ID:role/ai-assurance-lab-apprunner-role" \
  --region $REGION 2>&1) || true

# Check if service was created or already exists
if echo "$SERVICE_RESPONSE" | grep -q "arn:aws:apprunner"; then
  SERVICE_ARN=$(echo "$SERVICE_RESPONSE" | grep -o 'arn:aws:apprunner:[^"]*' | head -1)
  echo "✅ Service created: $SERVICE_ARN"
else
  echo "✅ Service already exists, finding it..."
  SERVICE_ARN=$(aws apprunner list-services \
    --region $REGION \
    --query "ServiceSummaryList[?ServiceName=='$SERVICE_NAME'].ServiceArn" \
    --output text)
  echo "✅ Service found: $SERVICE_ARN"
fi

# Step 6: Wait for AppRunner to be running
echo ""
echo "Step 6: Waiting for AppRunner to be RUNNING (2-3 minutes)..."
SERVICE_RUNNING=false
ATTEMPTS=0
MAX_ATTEMPTS=36  # 36 * 10 seconds = 6 minutes

while [ "$SERVICE_RUNNING" = false ] && [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
  STATUS=$(aws apprunner describe-service \
    --service-arn $SERVICE_ARN \
    --region $REGION \
    --query 'Service.Status' \
    --output text)
  
  if [ "$STATUS" = "RUNNING" ]; then
    echo "✅ Service is RUNNING!"
    SERVICE_RUNNING=true
  else
    echo "  Current status: $STATUS ($(($ATTEMPTS * 10))s elapsed)"
    ATTEMPTS=$((ATTEMPTS + 1))
    sleep 10
  fi
done

if [ "$SERVICE_RUNNING" = false ]; then
  echo "⚠️  Service still starting (may take longer). Continuing..."
fi

# Step 7: Get service URL
echo ""
echo "Step 7: Getting service URL..."
SERVICE_URL=$(aws apprunner describe-service \
  --service-arn $SERVICE_ARN \
  --region $REGION \
  --query 'Service.ServiceUrl' \
  --output text)

# Final summary
echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ DEPLOYMENT COMPLETE!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "🌐 Lab URL:"
echo "   $SERVICE_URL"
echo ""
echo "NEXT STEPS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Create your student list (students.csv):"
echo "   Format:"
echo "     email,first_name,last_name"
echo "     alice@example.com,Alice,Smith"
echo "     bob@example.com,Bob,Jones"
echo "     (repeat for all 40 students)"
echo ""
echo "2. Create student accounts:"
echo "   bash CREATE_STUDENTS_ONLY.sh students.csv"
echo ""
echo "3. Share the Lab URL with students"
echo ""
echo "════════════════════════════════════════════════════════════"
echo ""

# Save deployment info
cat > "$PROJECT_DIR/DEPLOYMENT_INFO.txt" << DEPLOY_INFO
════════════════════════════════════════════════════════════
AI ASSURANCE LAB - DEPLOYMENT INFORMATION
════════════════════════════════════════════════════════════

LAB URL:
  $SERVICE_URL

SERVICE ARN:
  $SERVICE_ARN

BUILD ID:
  $BUILD_ID

REGION:
  $REGION

ACCOUNT ID:
  $ACCOUNT_ID

════════════════════════════════════════════════════════════
Generated: $(date)
════════════════════════════════════════════════════════════
DEPLOY_INFO

echo "💾 Deployment info saved to: DEPLOYMENT_INFO.txt"

# Cleanup
echo ""
echo "Cleaning up temporary files..."
rm -f "$PROJECT_DIR/source.zip"
aws s3 rm s3://$BUCKET_NAME --recursive --region $REGION > /dev/null 2>&1 &

echo ""
echo "🎉 Ready to create students!"
echo ""
echo "Run: bash CREATE_STUDENTS_ONLY.sh students.csv"
echo ""
