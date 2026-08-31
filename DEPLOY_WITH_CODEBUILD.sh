#!/bin/bash

# AI Assurance Lab - Deploy with AWS CodeBuild (No Docker Desktop Required)
# This script builds the Docker image using AWS CodeBuild and deploys to AppRunner

set -e

REGION="us-east-1"
ACCOUNT_ID="004878717866"
PROJECT_NAME="ai-assurance-lab-build"
SERVICE_NAME="ai-assurance-lab"
PROJECT_DIR="$(pwd)"

echo "════════════════════════════════════════════════════════════"
echo "🚀 AWS CodeBuild Deployment (AWS-Native, No Docker Required)"
echo "════════════════════════════════════════════════════════════"
echo ""

# Step 1: Create/verify IAM roles
echo "Step 1: Setting up IAM roles..."

# CodeBuild role
CODEBUILD_ROLE="arn:aws:iam::$ACCOUNT_ID:role/ai-assurance-lab-codebuild-role"

# Check if role exists
if ! aws iam get-role --role-name ai-assurance-lab-codebuild-role --region $REGION 2>/dev/null | grep -q "AROAQCIWLKOVDYTWKNZ2V"; then
  echo "  (Creating CodeBuild role)"
  
  # Trust policy
  cat > /tmp/trust.json << 'TRUST'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
TRUST
  
  aws iam create-role \
    --role-name ai-assurance-lab-codebuild-role \
    --assume-role-policy-document file:///tmp/trust.json \
    --region $REGION 2>/dev/null || true
  
  sleep 2
  
  # Policies
  cat > /tmp/policy.json << 'POLICY'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::ai-assurance-lab-build-*",
        "arn:aws:s3:::ai-assurance-lab-build-*/*"
      ]
    }
  ]
}
POLICY

  aws iam put-role-policy \
    --role-name ai-assurance-lab-codebuild-role \
    --policy-name CodeBuildPolicy \
    --policy-document file:///tmp/policy.json \
    --region $REGION 2>/dev/null || true
fi

echo "✅ IAM roles ready"

# Step 2: Create CodeBuild project
echo ""
echo "Step 2: Creating CodeBuild project..."

# Delete if exists
aws codebuild delete-project --name $PROJECT_NAME --region $REGION 2>/dev/null || true
sleep 2

# Create buildspec.yml first (will be zipped with source)
cat > buildspec.yml << 'BUILDSPEC'
version: 0.2

phases:
  pre_build:
    commands:
      - echo "Logging in to Amazon ECR..."
      - aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 004878717866.dkr.ecr.us-east-1.amazonaws.com
      - REPOSITORY_URI=004878717866.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab
      - COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)
      - IMAGE_TAG=${COMMIT_HASH:=latest}

  build:
    commands:
      - echo "Building the Docker image on `date`"
      - docker build -t $REPOSITORY_URI:latest .
      - docker tag $REPOSITORY_URI:latest $REPOSITORY_URI:$IMAGE_TAG

  post_build:
    commands:
      - echo "Pushing the Docker images on `date`"
      - docker push $REPOSITORY_URI:latest
      - docker push $REPOSITORY_URI:$IMAGE_TAG
      - echo "Writing image definitions file..."
      - printf '[{"name":"ai-assurance-lab","imageUri":"%s"}]' $REPOSITORY_URI:$IMAGE_TAG > imagedefinitions.json

artifacts:
  files: imagedefinitions.json
BUILDSPEC

# Create project with NO_SOURCE initially, then we'll use S3
# Actually, use S3 with dummy location that we'll override with source-location-override
aws codebuild create-project \
  --name $PROJECT_NAME \
  --description "Build AI Assurance Lab Docker image" \
  --source type=S3,location="s3://dummy-bucket/dummy.zip" \
  --artifacts type=NO_ARTIFACTS \
  --environment type=LINUX_CONTAINER,image=aws/codebuild/standard:7.0,computeType=BUILD_GENERAL1_MEDIUM,privilegedMode=true \
  --service-role "$CODEBUILD_ROLE" \
  --region $REGION 2>&1 || echo "Project may already exist"

echo "✅ CodeBuild project ready"

# Step 3: Upload source and trigger build
echo ""
echo "Step 3: Building Docker image with CodeBuild..."

# Create S3 bucket for source
BUCKET_NAME="ai-assurance-lab-build-$(date +%s)"
aws s3 mb "s3://$BUCKET_NAME" --region $REGION

# Zip source code
echo "  Zipping source code..."
cd "$PROJECT_DIR"
zip -r source.zip . \
  -x "venv/*" \
  ".git/*" \
  "__pycache__/*" \
  "*.pyc" \
  "*.egg-info/*" \
  ".pytest_cache/*" \
  ".DS_Store" \
  ".cursor/*" \
  "deployment.log" \
  "*.egg-info/*" > /dev/null 2>&1 || true

# Upload to S3
echo "  Uploading source to S3..."
aws s3 cp source.zip "s3://$BUCKET_NAME/" --region $REGION

# Trigger build with override
echo "  Starting CodeBuild..."
BUILD_RESPONSE=$(aws codebuild start-build \
  --project-name $PROJECT_NAME \
  --source-location-override "s3://$BUCKET_NAME/source.zip" \
  --region $REGION \
  --output json)

BUILD_ID=$(echo "$BUILD_RESPONSE" | jq -r '.build.id')
BUILD_ARN=$(echo "$BUILD_RESPONSE" | jq -r '.build.arn')

echo "  Build started: $BUILD_ID"
echo "  Monitor progress at:"
echo "  https://console.aws.amazon.com/codesuite/codebuild/projects/$PROJECT_NAME/history"

# Step 4: Wait for build to complete
echo ""
echo "Step 4: Waiting for build to complete (5-10 minutes)..."

MAX_WAIT=600
ELAPSED=0
BUILD_STATUS="IN_PROGRESS"

while [ "$BUILD_STATUS" = "IN_PROGRESS" ] && [ $ELAPSED -lt $MAX_WAIT ]; do
  BUILD_STATUS=$(aws codebuild batch-get-builds \
    --ids $BUILD_ID \
    --region $REGION \
    --query 'builds[0].buildStatus' \
    --output text 2>/dev/null || echo "UNKNOWN")
  
  echo "  Status: $BUILD_STATUS"
  
  if [ "$BUILD_STATUS" != "IN_PROGRESS" ]; then
    break
  fi
  
  sleep 30
  ELAPSED=$((ELAPSED + 30))
done

if [ "$BUILD_STATUS" != "SUCCEEDED" ]; then
  echo "❌ Build failed or timed out. Status: $BUILD_STATUS"
  echo ""
  echo "View build logs:"
  echo "  aws logs tail /aws/codebuild/$PROJECT_NAME --follow --region us-east-1"
  exit 1
fi

echo "✅ Build succeeded!"

# Step 5: Create/update AppRunner service
echo ""
echo "Step 5: Deploying to AppRunner..."

SERVICE_ARN=$(aws apprunner list-services \
  --region $REGION \
  --query "ServiceSummaryList[?ServiceName=='$SERVICE_NAME'].ServiceArn" \
  --output text 2>/dev/null || echo "")

if [ -z "$SERVICE_ARN" ]; then
  echo "  Creating AppRunner service..."
  
  SERVICE_RESPONSE=$(aws apprunner create-service \
    --service-name $SERVICE_NAME \
    --source-configuration ImageRepository='{ImageIdentifier=004878717866.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab:latest,ImageRepositoryType=ECR,ImageConfiguration={Port=8080}}' \
    --instance-role-arn "arn:aws:iam::$ACCOUNT_ID:role/ai-assurance-lab-apprunner-role" \
    --region $REGION \
    --output json)
  
  SERVICE_ARN=$(echo "$SERVICE_RESPONSE" | jq -r '.Service.ServiceArn')
else
  echo "  Updating AppRunner service..."
  
  aws apprunner update-service \
    --service-arn "$SERVICE_ARN" \
    --source-configuration ImageRepository='{ImageIdentifier=004878717866.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab:latest,ImageRepositoryType=ECR,ImageConfiguration={Port=8080}}' \
    --region $REGION > /dev/null 2>&1 || true
fi

echo "✅ AppRunner service configured"

# Step 6: Wait for AppRunner to be ready
echo ""
echo "Step 6: Waiting for AppRunner service to be RUNNING (5 minutes)..."

MAX_WAIT=300
ELAPSED=0
APP_STATUS="OPERATION_IN_PROGRESS"

while [ "$APP_STATUS" != "RUNNING" ] && [ $ELAPSED -lt $MAX_WAIT ]; do
  APP_STATUS=$(aws apprunner describe-service \
    --service-arn "$SERVICE_ARN" \
    --region $REGION \
    --query 'Service.Status' \
    --output text 2>/dev/null || echo "UNKNOWN")
  
  echo "  Status: $APP_STATUS"
  
  if [ "$APP_STATUS" = "RUNNING" ]; then
    break
  fi
  
  sleep 15
  ELAPSED=$((ELAPSED + 15))
done

if [ "$APP_STATUS" != "RUNNING" ]; then
  echo "⚠️  Service is taking longer than expected. Continuing..."
fi

# Step 7: Get service URL
echo ""
echo "Step 7: Getting service URL..."

SERVICE_URL=$(aws apprunner describe-service \
  --service-arn "$SERVICE_ARN" \
  --region $REGION \
  --query 'Service.ServiceUrl' \
  --output text 2>/dev/null || echo "")

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ DEPLOYMENT COMPLETE!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "🌐 Lab URL:"
echo "   https://$SERVICE_URL"
echo ""
echo "NEXT STEPS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Create students.csv file with student emails"
echo "   Format: email,first_name,last_name"
echo ""
echo "2. Create student accounts:"
echo "   bash CREATE_STUDENTS_ONLY.sh students.csv"
echo ""
echo "3. Share Lab URL with students:"
echo "   https://$SERVICE_URL"
echo ""
echo "════════════════════════════════════════════════════════════"
echo ""

# Save deployment info
cat > DEPLOYMENT_INFO.txt << INFO
AI Assurance Lab Deployment Information
========================================
Deployment Date: $(date)
Region: $REGION
Service Name: $SERVICE_NAME
Service ARN: $SERVICE_ARN
Lab URL: https://$SERVICE_URL

Build Information:
  Project: $PROJECT_NAME
  Build ID: $BUILD_ID
  Status: $BUILD_STATUS

Next Steps:
1. Create students.csv with student emails
2. Run: bash CREATE_STUDENTS_ONLY.sh students.csv
3. Share the Lab URL with students

Cleanup (if needed):
  aws apprunner delete-service --service-arn "$SERVICE_ARN" --region us-east-1

S3 Cleanup (if needed):
  aws s3 rm s3://$BUCKET_NAME --recursive
  aws s3 rb s3://$BUCKET_NAME

INFO

echo "✅ Deployment info saved to: DEPLOYMENT_INFO.txt"

# Cleanup S3 bucket used for build (optional - keeping for now in case needed)
echo ""
echo "Build artifacts S3 bucket: s3://$BUCKET_NAME"
echo "(You can manually delete this S3 bucket to save costs)"
