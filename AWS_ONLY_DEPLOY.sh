#!/bin/bash

# AI Assurance Lab - 100% AWS-Native Deployment (No Docker Desktop Required)
# Uses AWS CodeBuild to build and push Docker image, then deploys to AppRunner

set -e

REGION="us-east-1"
ACCOUNT_ID="004878717866"
PROJECT_NAME="ai-assurance-lab-build"
SERVICE_NAME="ai-assurance-lab"
PROJECT_DIR="$(pwd)"

echo "════════════════════════════════════════════════════════════"
echo "🚀 100% AWS-NATIVE DEPLOYMENT"
echo "════════════════════════════════════════════════════════════"
echo "No Docker Desktop required - everything runs in AWS"
echo ""

# Step 1: Verify AWS credentials
echo "Step 1: Verifying AWS credentials..."
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
if [ "$ACCOUNT" != "$ACCOUNT_ID" ]; then
  echo "❌ Wrong AWS account! Expected $ACCOUNT_ID, got $ACCOUNT"
  exit 1
fi
echo "✅ AWS credentials verified"

# Step 2: Create/verify CodeBuild IAM role
echo ""
echo "Step 2: Setting up CodeBuild IAM role..."

ROLE_NAME="ai-assurance-lab-codebuild-role"

# Check if role exists
if aws iam get-role --role-name $ROLE_NAME --region $REGION 2>/dev/null | grep -q "Arn"; then
  echo "  (Role already exists)"
else
  echo "  Creating role..."
  
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
    --role-name $ROLE_NAME \
    --assume-role-policy-document file:///tmp/trust.json \
    --region $REGION > /dev/null
  
  sleep 2
fi

# Attach policies
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
        "ecr:CompleteLayerUpload",
        "ecr:DescribeRepositories",
        "ecr:DescribeImages"
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
      "Resource": "*"
    }
  ]
}
POLICY

aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name CodeBuildPolicy \
  --policy-document file:///tmp/policy.json \
  --region $REGION 2>/dev/null || true

sleep 1
echo "✅ CodeBuild IAM role ready"

# Step 3: Delete existing CodeBuild project and recreate
echo ""
echo "Step 3: Setting up CodeBuild project..."

aws codebuild delete-project --name $PROJECT_NAME --region $REGION 2>/dev/null || true
sleep 3

# Create buildspec content
cat > /tmp/buildspec.json << 'BSPEC'
version: 0.2

phases:
  pre_build:
    commands:
      - echo "Logging in to Amazon ECR..."
      - aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 004878717866.dkr.ecr.us-east-1.amazonaws.com
      - REPOSITORY_URI=004878717866.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab
      - IMAGE_TAG=latest

  build:
    commands:
      - echo "Building Docker image..."
      - docker build -t $REPOSITORY_URI:$IMAGE_TAG .

  post_build:
    commands:
      - echo "Pushing Docker image to ECR..."
      - docker push $REPOSITORY_URI:$IMAGE_TAG
      - echo "Build completed!"

BSPEC

# Create with NO_SOURCE and inline buildspec
BUILDSPEC_JSON=$(cat /tmp/buildspec.json | jq -Rs .)

aws codebuild create-project \
  --name $PROJECT_NAME \
  --description "AI Assurance Lab Docker Build" \
  --source type=NO_SOURCE,buildspec="$BUILDSPEC_JSON" \
  --artifacts type=NO_ARTIFACTS \
  --environment type=LINUX_CONTAINER,image=aws/codebuild/standard:7.0,computeType=BUILD_GENERAL1_MEDIUM,privilegedMode=true \
  --service-role "arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME" \
  --region $REGION > /dev/null 2>&1

sleep 2
echo "✅ CodeBuild project ready"

# Step 4: Prepare source code
echo ""
echo "Step 4: Preparing source code for build..."

# Create buildspec if it doesn't exist
cat > buildspec.yml << 'BUILDSPEC'
version: 0.2

phases:
  pre_build:
    commands:
      - echo "Logging in to Amazon ECR..."
      - aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 004878717866.dkr.ecr.us-east-1.amazonaws.com
      - REPOSITORY_URI=004878717866.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab
      - IMAGE_TAG=latest

  build:
    commands:
      - echo "Building Docker image..."
      - docker build -t $REPOSITORY_URI:$IMAGE_TAG .

  post_build:
    commands:
      - echo "Pushing Docker image to ECR..."
      - docker push $REPOSITORY_URI:$IMAGE_TAG
      - echo "Build completed successfully!"

BUILDSPEC

# Zip source code
cd "$PROJECT_DIR"
echo "  Zipping source code..."
rm -f source.zip
zip -r source.zip . \
  -x "venv/*" \
  ".git/*" \
  "__pycache__/*" \
  "*.pyc" \
  ".egg-info/*" \
  ".pytest_cache/*" \
  ".DS_Store" \
  ".cursor/*" \
  "deployment.log" \
  "*.log" \
  > /dev/null 2>&1 || true

echo "✅ Source code prepared"

# Step 5: Upload to S3
echo ""
echo "Step 5: Uploading source to S3..."

BUCKET_NAME="ai-assurance-lab-build-$(date +%s)"
echo "  Creating S3 bucket: $BUCKET_NAME"
aws s3 mb "s3://$BUCKET_NAME" --region $REGION 2>/dev/null || true

sleep 1

echo "  Uploading source.zip..."
aws s3 cp source.zip "s3://$BUCKET_NAME/source.zip" --region $REGION

echo "✅ Source uploaded to S3"

# Step 6: Trigger CodeBuild
echo ""
echo "Step 6: Starting CodeBuild (Docker build in AWS)..."

BUILD_RESPONSE=$(aws codebuild start-build \
  --project-name $PROJECT_NAME \
  --source-location-override "s3://$BUCKET_NAME/source.zip" \
  --region $REGION \
  --output json)

BUILD_ID=$(echo "$BUILD_RESPONSE" | jq -r '.build.id')
echo "  Build ID: $BUILD_ID"
echo "  Monitoring build progress..."

# Step 7: Wait for build to complete
echo ""
echo "Step 7: Waiting for CodeBuild to complete (5-10 minutes)..."
echo "  Monitor in AWS Console:"
echo "  https://console.aws.amazon.com/codesuite/codebuild/projects/$PROJECT_NAME/history"
echo ""

MAX_WAIT=900
ELAPSED=0
BUILD_STATUS="IN_PROGRESS"
LAST_STATUS=""

while [ "$BUILD_STATUS" = "IN_PROGRESS" ] && [ $ELAPSED -lt $MAX_WAIT ]; do
  BUILD_STATUS=$(aws codebuild batch-get-builds \
    --ids $BUILD_ID \
    --region $REGION \
    --query 'builds[0].buildStatus' \
    --output text 2>/dev/null || echo "UNKNOWN")
  
  if [ "$BUILD_STATUS" != "$LAST_STATUS" ]; then
    echo "  Status: $BUILD_STATUS ($((ELAPSED/60))m)"
    LAST_STATUS="$BUILD_STATUS"
  fi
  
  if [ "$BUILD_STATUS" != "IN_PROGRESS" ]; then
    break
  fi
  
  sleep 30
  ELAPSED=$((ELAPSED + 30))
done

if [ "$BUILD_STATUS" != "SUCCEEDED" ]; then
  echo "❌ Build failed! Status: $BUILD_STATUS"
  echo ""
  echo "View build logs:"
  echo "  aws logs tail /aws/codebuild/$PROJECT_NAME --follow --region us-east-1"
  exit 1
fi

echo "✅ CodeBuild completed successfully!"

# Step 8: Create/update AppRunner service
echo ""
echo "Step 8: Deploying to AppRunner..."

SERVICE_ARN=$(aws apprunner list-services \
  --region $REGION \
  --query "ServiceSummaryList[?ServiceName=='$SERVICE_NAME'].ServiceArn" \
  --output text 2>/dev/null || echo "")

if [ -z "$SERVICE_ARN" ]; then
  echo "  Creating new AppRunner service..."
  
  SERVICE_RESPONSE=$(aws apprunner create-service \
    --service-name $SERVICE_NAME \
    --source-configuration "ImageRepository={ImageIdentifier=004878717866.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab:latest,ImageRepositoryType=ECR,ImageConfiguration={Port=8080}}" \
    --instance-role-arn "arn:aws:iam::$ACCOUNT_ID:role/ai-assurance-lab-apprunner-role" \
    --region $REGION \
    --output json)
  
  SERVICE_ARN=$(echo "$SERVICE_RESPONSE" | jq -r '.Service.ServiceArn')
else
  echo "  Updating AppRunner service..."
  
  aws apprunner update-service \
    --service-arn "$SERVICE_ARN" \
    --source-configuration "ImageRepository={ImageIdentifier=004878717866.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab:latest,ImageRepositoryType=ECR,ImageConfiguration={Port=8080}}" \
    --region $REGION > /dev/null 2>&1 || true
fi

echo "✅ AppRunner service configured"

# Step 9: Wait for AppRunner to be ready
echo ""
echo "Step 9: Starting AppRunner service (3-5 minutes)..."

MAX_WAIT=300
ELAPSED=0
APP_STATUS="OPERATION_IN_PROGRESS"
LAST_STATUS=""

while [ "$APP_STATUS" != "RUNNING" ] && [ $ELAPSED -lt $MAX_WAIT ]; do
  APP_STATUS=$(aws apprunner describe-service \
    --service-arn "$SERVICE_ARN" \
    --region $REGION \
    --query 'Service.Status' \
    --output text 2>/dev/null || echo "UNKNOWN")
  
  if [ "$APP_STATUS" != "$LAST_STATUS" ]; then
    echo "  Status: $APP_STATUS ($((ELAPSED/60))m)"
    LAST_STATUS="$APP_STATUS"
  fi
  
  if [ "$APP_STATUS" = "RUNNING" ]; then
    break
  fi
  
  sleep 15
  ELAPSED=$((ELAPSED + 15))
done

echo "✅ AppRunner service is RUNNING"

# Step 10: Get service URL
echo ""
echo "Step 10: Getting service URL..."

SERVICE_URL=$(aws apprunner describe-service \
  --service-arn "$SERVICE_ARN" \
  --region $REGION \
  --query 'Service.ServiceUrl' \
  --output text 2>/dev/null || echo "")

# Final summary
echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ DEPLOYMENT COMPLETE!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "🌐 Lab URL:"
echo ""
echo "   https://$SERVICE_URL"
echo ""
echo "════════════════════════════════════════════════════════════"
echo ""
echo "NEXT STEPS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Create students.csv with student emails:"
echo ""
echo "   email,first_name,last_name"
echo "   alice@example.com,Alice,Smith"
echo "   bob@example.com,Bob,Jones"
echo "   ... (40 total)"
echo ""
echo "2. Create student accounts:"
echo ""
echo "   bash CREATE_STUDENTS_ONLY.sh students.csv"
echo ""
echo "3. Share Lab URL with students:"
echo ""
echo "   https://$SERVICE_URL"
echo ""
echo "════════════════════════════════════════════════════════════"
echo ""

# Save deployment info
cat > DEPLOYMENT_INFO.txt << INFO
AI Assurance Lab - Deployment Information
==========================================

Deployment Date: $(date)
Region: $REGION
Service Name: $SERVICE_NAME
Service ARN: $SERVICE_ARN
Lab URL: https://$SERVICE_URL

Build Information:
  CodeBuild Project: $PROJECT_NAME
  Build ID: $BUILD_ID
  Build Status: $BUILD_STATUS
  ECR Image: 004878717866.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab:latest

Architecture:
  - CodeBuild: Built Docker image in AWS
  - Amazon ECR: Stored Docker image
  - AppRunner: Running the lab application
  - DynamoDB: Storing student credentials
  - Cognito: Managing student authentication

NEXT STEPS:
1. Create students.csv with student email addresses
2. Run: bash CREATE_STUDENTS_ONLY.sh students.csv
3. Share the Lab URL with students

For Subsequent Labs:
  - Run: bash RESET_USERS.sh new_students.csv (3 minutes, $0-5)
  - See: RESET_USERS_BETWEEN_LABS.md

Cost (4-hour lab, 40 students):
  - AppRunner: $0.26
  - DynamoDB: $5-10
  - Bedrock (Claude): $20-30
  - Total: ~$25-40 per lab
  - Per student: ~$0.60-$1.00

To delete (stop costs):
  aws apprunner delete-service --service-arn "$SERVICE_ARN" --region us-east-1
  Note: DynamoDB and Cognito data preserved for future labs

S3 Cleanup (optional):
  aws s3 rm s3://$BUCKET_NAME --recursive
  aws s3 rb s3://$BUCKET_NAME

════════════════════════════════════════════════════════════════════════════
INFO

echo "✅ Deployment info saved to: DEPLOYMENT_INFO.txt"
echo ""
echo "All AWS infrastructure is fully managed and automated."
echo "No local Docker Desktop required!"
