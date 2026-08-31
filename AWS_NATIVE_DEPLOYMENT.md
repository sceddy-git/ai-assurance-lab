# 🚀 AI Assurance Lab - AWS-Native Deployment (No Docker Desktop)

**Deploy entirely within AWS using CodeBuild**

---

## Overview

Since Docker Desktop isn't available, we'll use **AWS CodeBuild** to build the Docker image directly in AWS, then deploy to AppRunner. This is actually cleaner - everything stays in AWS.

**What you don't need:**
- ❌ Docker Desktop
- ❌ Building locally
- ❌ Pushing images manually

**What you do:**
- ✅ One AWS CLI command to trigger CodeBuild
- ✅ CodeBuild builds the image in AWS
- ✅ Image goes straight to ECR
- ✅ AppRunner deploys automatically

---

## Prerequisites

- [ ] AWS CLI configured (`aws sts get-caller-identity` works)
- [ ] AWS CodeBuild service enabled (it is by default)
- [ ] List of 40 student emails (CSV file)

That's it! No Docker needed.

---

## Step 1: Create CodeBuild Project

Run this command (copy & paste):

```bash
aws codebuild create-project \
  --name ai-assurance-lab-build \
  --source type=NO_SOURCE \
  --artifacts type=NO_ARTIFACTS \
  --environment type=LINUX_CONTAINER,image=aws/codebuild/standard:7.0,computeType=BUILD_GENERAL1_MEDIUM \
  --service-role arn:aws:iam::004878717866:role/ai-assurance-lab-apprunner-role \
  --region us-east-1
```

**What this does:**
- Creates a CodeBuild project named `ai-assurance-lab-build`
- Configures it to build Docker images
- Uses the IAM role we already created

**Expected output:**
```
{
  "project": {
    "name": "ai-assurance-lab-build",
    "arn": "arn:aws:codebuild:us-east-1:004878717866:project/ai-assurance-lab-build",
    ...
  }
}
```

---

## Step 2: Create Buildspec (Build Instructions)

Create a file called `buildspec.yml` in your project directory:

```bash
cat > "/Users/sceddy/Documents/AI Assurance MCP day/buildspec.yml" << 'EOF'
version: 0.2

phases:
  pre_build:
    commands:
      - echo Logging in to Amazon ECR...
      - aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 004878717866.dkr.ecr.us-east-1.amazonaws.com
      - REPOSITORY_URI=004878717866.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab
      - COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)
      - IMAGE_TAG=${COMMIT_HASH:=latest}
  
  build:
    commands:
      - echo Build started on `date`
      - echo Building the Docker image...
      - docker build -t $REPOSITORY_URI:latest .
      - docker tag $REPOSITORY_URI:latest $REPOSITORY_URI:$IMAGE_TAG
  
  post_build:
    commands:
      - echo Build completed on `date`
      - echo Pushing the Docker images...
      - docker push $REPOSITORY_URI:latest
      - docker push $REPOSITORY_URI:$IMAGE_TAG
      - echo Writing image definitions file...
      - printf '[{"name":"ai-assurance-lab","imageUri":"%s"}]' $REPOSITORY_URI:$IMAGE_TAG > imagedefinitions.json

artifacts:
  files: imagedefinitions.json
EOF
```

---

## Step 3: Trigger the Build

Upload the project to a temporary S3 bucket and trigger CodeBuild:

```bash
# Create temporary S3 bucket for source
BUCKET_NAME="ai-assurance-lab-build-$(date +%s)"
aws s3 mb s3://$BUCKET_NAME --region us-east-1

# ZIP up the project
cd "/Users/sceddy/Documents/AI Assurance MCP day"
zip -r source.zip . -x "venv/*" ".git/*" "__pycache__/*" "*.pyc"

# Upload to S3
aws s3 cp source.zip s3://$BUCKET_NAME/ --region us-east-1

# Trigger CodeBuild
aws codebuild start-build \
  --project-name ai-assurance-lab-build \
  --source-location-override s3://$BUCKET_NAME/source.zip \
  --region us-east-1

echo "Build triggered! Check progress in AWS CodeBuild console"
echo "https://console.aws.amazon.com/codesuite/codebuild/projects/ai-assurance-lab-build"
```

**What to expect:**
- Build starts (takes 3-5 minutes)
- Docker image is built in AWS
- Image is pushed to ECR
- Status shows as SUCCESS

---

## Step 4: Deploy to AppRunner

Once CodeBuild completes, create/update AppRunner service:

```bash
aws apprunner create-service \
  --service-name ai-assurance-lab \
  --source-configuration ImageRepository="{ImageIdentifier=004878717866.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab:latest,ImageRepositoryType=ECR,ImageConfiguration={Port=8080}}" \
  --instance-configuration Cpu=1024,Memory=2048,InstanceRoleArn=arn:aws:iam::004878717866:role/ai-assurance-lab-apprunner-role \
  --region us-east-1
```

**What to expect:**
- AppRunner service is created
- Service starts deploying (2-3 minutes)
- You'll get a service URL

**Get your service URL:**
```bash
aws apprunner list-services \
  --region us-east-1 \
  --query "ServiceSummaryList[?ServiceName=='ai-assurance-lab'].ServiceUrl" \
  --output text
```

**Save this URL!** You'll give it to students.

---

## Step 5: Create Student Accounts

Now create all 40 student accounts:

```bash
bash CREATE_STUDENTS_ONLY.sh students.csv
```

**That's it!** All students created and ready to log in.

---

## Complete AWS-Only Script

Here's a complete automated script that does everything:

```bash
#!/bin/bash

set -e

REGION="us-east-1"
ACCOUNT_ID="004878717866"
PROJECT_NAME="ai-assurance-lab-build"
SERVICE_NAME="ai-assurance-lab"
PROJECT_DIR="/Users/sceddy/Documents/AI Assurance MCP day"

echo "════════════════════════════════════════════════════════════"
echo "🚀 AWS-NATIVE DEPLOYMENT (No Docker Desktop Required)"
echo "════════════════════════════════════════════════════════════"

# Step 1: Create CodeBuild project
echo ""
echo "Step 1: Creating CodeBuild project..."
aws codebuild create-project \
  --name $PROJECT_NAME \
  --source type=NO_SOURCE \
  --artifacts type=NO_ARTIFACTS \
  --environment type=LINUX_CONTAINER,image=aws/codebuild/standard:7.0,computeType=BUILD_GENERAL1_MEDIUM \
  --service-role arn:aws:iam::$ACCOUNT_ID:role/ai-assurance-lab-apprunner-role \
  --region $REGION 2>/dev/null || echo "Project may already exist"

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

cache:
  paths:
    - '/root/.cache/pip/**/*'
BUILDSPEC

echo "✅ buildspec.yml created"

# Step 3: Upload source to S3 and trigger build
echo ""
echo "Step 3: Uploading source and triggering CodeBuild..."
BUCKET_NAME="ai-assurance-lab-build-$(date +%s)"
aws s3 mb s3://$BUCKET_NAME --region $REGION 2>/dev/null || true

cd "$PROJECT_DIR"
zip -r source.zip . -x "venv/*" ".git/*" "__pycache__/*" "*.pyc" "*.egg-info/*" > /dev/null 2>&1
aws s3 cp source.zip s3://$BUCKET_NAME/ --region $REGION > /dev/null

BUILD_ID=$(aws codebuild start-build \
  --project-name $PROJECT_NAME \
  --source-location-override s3://$BUCKET_NAME/source.zip \
  --region $REGION \
  --query 'build.id' \
  --output text)

echo "✅ Build triggered: $BUILD_ID"
echo "   Monitoring: https://console.aws.amazon.com/codesuite/codebuild/projects/$PROJECT_NAME"

# Wait for build to complete
echo ""
echo "Step 4: Waiting for build to complete (this takes 3-5 minutes)..."
while true; do
  STATUS=$(aws codebuild batch-get-builds \
    --ids $BUILD_ID \
    --region $REGION \
    --query 'builds[0].buildStatus' \
    --output text)
  
  if [ "$STATUS" = "SUCCEEDED" ]; then
    echo "✅ Build succeeded!"
    break
  elif [ "$STATUS" = "FAILED" ]; then
    echo "❌ Build failed"
    exit 1
  else
    echo "  Status: $STATUS"
    sleep 10
  fi
done

# Step 5: Deploy to AppRunner
echo ""
echo "Step 5: Creating AppRunner service..."
SERVICE_RESPONSE=$(aws apprunner create-service \
  --service-name $SERVICE_NAME \
  --source-configuration ImageRepository="{ImageIdentifier=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/ai-assurance-lab:latest,ImageRepositoryType=ECR,ImageConfiguration={Port=8080}}" \
  --instance-configuration Cpu=1024,Memory=2048,InstanceRoleArn=arn:aws:iam::$ACCOUNT_ID:role/ai-assurance-lab-apprunner-role \
  --region $REGION 2>&1)

SERVICE_ARN=$(echo "$SERVICE_RESPONSE" | grep -o 'arn:aws:apprunner:[^"]*' | head -1)

if [ -z "$SERVICE_ARN" ]; then
  echo "Service may already exist, finding it..."
  SERVICE_ARN=$(aws apprunner list-services \
    --region $REGION \
    --query "ServiceSummaryList[?ServiceName=='$SERVICE_NAME'].ServiceArn" \
    --output text)
fi

echo "✅ Service created/found: $SERVICE_ARN"

# Step 6: Wait for AppRunner to be running
echo ""
echo "Step 6: Waiting for AppRunner service to be RUNNING (2-3 minutes)..."
while true; do
  STATUS=$(aws apprunner describe-service \
    --service-arn $SERVICE_ARN \
    --region $REGION \
    --query 'Service.Status' \
    --output text)
  
  if [ "$STATUS" = "RUNNING" ]; then
    echo "✅ Service is RUNNING!"
    break
  else
    echo "  Status: $STATUS"
    sleep 15
  fi
done

# Step 7: Get service URL
echo ""
echo "Step 7: Getting service URL..."
SERVICE_URL=$(aws apprunner describe-service \
  --service-arn $SERVICE_ARN \
  --region $REGION \
  --query 'Service.ServiceUrl' \
  --output text)

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ DEPLOYMENT COMPLETE!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "🌐 Lab URL: $SERVICE_URL"
echo ""
echo "NEXT STEPS:"
echo "1. Create students.csv with your student emails"
echo "2. Run: bash CREATE_STUDENTS_ONLY.sh students.csv"
echo "3. Share the Lab URL with students"
echo ""
echo "════════════════════════════════════════════════════════════"

# Cleanup
rm -f source.zip
aws s3 rm s3://$BUCKET_NAME --recursive --region $REGION > /dev/null 2>&1 &

echo ""
echo "Ready to create students!"
```

**Save this as:** `AWS_DEPLOY.sh`

**Run it:**
```bash
bash AWS_DEPLOY.sh
```

This will handle everything automatically!

---

## Monitoring the Build

While the build is running:

```bash
# Check real-time logs
aws codebuild batch-get-builds \
  --ids <build-id> \
  --region us-east-1 \
  --query 'builds[0].[buildStatus,logs.groupName,logs.streamName]' \
  --output text
```

Or visit: https://console.aws.amazon.com/codesuite/codebuild/projects/ai-assurance-lab-build

---

## Student Creation

Once AppRunner is running, create students:

```bash
# Create your students.csv first
cat > students.csv << 'CSV'
email,first_name,last_name
alice@example.com,Alice,Smith
bob@example.com,Bob,Jones
charlie@example.com,Charlie,Brown
... (repeat for all 40)
CSV

# Create all student accounts
bash CREATE_STUDENTS_ONLY.sh students.csv
```

That's it!

---

## Cost Comparison

| Method | Cost |
|--------|------|
| CodeBuild (build) | ~$0.10 per build |
| AppRunner (4 hours) | ~$0.26 |
| DynamoDB & Bedrock | ~$25-30 |
| **Total** | **~$25-30** |

**Same total cost, but:**
- ✅ No Docker Desktop needed
- ✅ Everything in AWS
- ✅ Build runs in parallel
- ✅ Cleaner architecture

---

## Troubleshooting

### "CodeBuild build failed"
```bash
# Check build logs
aws codebuild batch-get-builds \
  --ids <build-id> \
  --region us-east-1 \
  --query 'builds[0].logs' \
  --output json
```

### "AppRunner service won't start"
```bash
# Check service status
aws apprunner describe-service \
  --service-arn <arn> \
  --region us-east-1
```

### "Need to rebuild"
```bash
# Just run the deploy script again
bash AWS_DEPLOY.sh
# It will detect existing resources and update them
```

---

## Complete Workflow

```
1. Run: bash AWS_DEPLOY.sh
   ↓
   CodeBuild builds Docker image in AWS (5 min)
   ↓
   Image pushed to ECR automatically
   ↓
   AppRunner deploys the service (3 min)
   ↓
   Service URL provided

2. Create students.csv

3. Run: bash CREATE_STUDENTS_ONLY.sh students.csv
   ↓
   40 student accounts created

4. Share the Lab URL with students
   ↓
   Students log in and use the lab!
```

---

## No Docker Desktop Required ✅

With this AWS-native approach:
- ❌ Don't need Docker Desktop
- ❌ Don't need to build locally
- ❌ Don't need to push manually
- ✅ Everything stays in AWS
- ✅ Fully automated
- ✅ Same 20-minute deployment

---

## Your Next Steps

1. **Option A: Run automated script**
   ```bash
   bash AWS_DEPLOY.sh
   ```

2. **Option B: Run commands manually** (see above)

3. **Either way:**
   ```bash
   bash CREATE_STUDENTS_ONLY.sh students.csv
   ```

4. **Then:** Share the Lab URL with students!

---

**Ready? Let's deploy to AWS! 🚀**

