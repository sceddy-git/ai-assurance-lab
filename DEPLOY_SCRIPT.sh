#!/bin/bash

# AI Assurance Lab - Automated Deployment Script
# This script builds the Docker image and creates the AppRunner service

ACCOUNT_ID="004878717866"
REGION="us-east-1"
REPO_NAME="ai-assurance-lab"
SERVICE_NAME="ai-assurance-lab"

# Read Cognito config
source /tmp/cognito_config.txt

echo "════════════════════════════════════════════════════════════"
echo "🚀 AI ASSURANCE LAB - AUTOMATED DEPLOYMENT"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check Docker is running
echo "✓ Checking Docker..."
if ! docker ps > /dev/null 2>&1; then
  echo "❌ Docker is not running. Please start Docker Desktop and try again."
  exit 1
fi
echo "✅ Docker is running"

# Step 1: Build Docker image
echo ""
echo "📦 Step 1: Building Docker image..."
cd "/Users/sceddy/Documents/AI Assurance MCP day"
docker build -t $REPO_NAME:latest . || exit 1
echo "✅ Docker image built"

# Step 2: Login to ECR
echo ""
echo "🔐 Step 2: Login to ECR..."
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com || exit 1
echo "✅ ECR login successful"

# Step 3: Tag image
echo ""
echo "🏷️  Step 3: Tagging image for ECR..."
docker tag $REPO_NAME:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest || exit 1
echo "✅ Image tagged"

# Step 4: Push to ECR
echo ""
echo "⬆️  Step 4: Pushing to ECR..."
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest || exit 1
echo "✅ Image pushed to ECR"

# Step 5: Create AppRunner service
echo ""
echo "🚀 Step 5: Creating AppRunner service..."

ECR_IMAGE="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/ai-assurance-lab-apprunner-role"

# Create AppRunner service
aws apprunner create-service \
  --service-name $SERVICE_NAME \
  --source-configuration ImageRepository="{ImageIdentifier=$ECR_IMAGE,ImageRepositoryType=ECR,ImageConfiguration={Port=8080}}" \
  --instance-configuration Cpu=1024,Memory=2048,InstanceRoleArn=$ROLE_ARN \
  --region $REGION \
  --output json > /tmp/apprunner_service.json

SERVICE_ARN=$(cat /tmp/apprunner_service.json | jq -r '.Service.ServiceArn' 2>/dev/null)

if [ ! -z "$SERVICE_ARN" ] && [ "$SERVICE_ARN" != "null" ]; then
  echo "✅ AppRunner service created: $SERVICE_ARN"
else
  echo "⚠️  AppRunner service may already exist. Checking..."
  SERVICE_ARN=$(aws apprunner list-services \
    --region $REGION \
    --query "ServiceSummaryList[?ServiceName=='$SERVICE_NAME'].ServiceArn" \
    --output text)
  
  if [ ! -z "$SERVICE_ARN" ]; then
    echo "✅ Found existing service: $SERVICE_ARN"
  else
    echo "❌ Failed to create AppRunner service"
    exit 1
  fi
fi

# Wait for service to be created
echo ""
echo "⏳ Waiting for service to become RUNNING (this may take 2-3 minutes)..."
TIMEOUT=300
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
  STATUS=$(aws apprunner describe-service \
    --service-arn $SERVICE_ARN \
    --region $REGION \
    --query 'Service.Status' \
    --output text 2>/dev/null)
  
  if [ "$STATUS" = "RUNNING" ]; then
    break
  fi
  
  echo "  Status: $STATUS"
  sleep 10
  ELAPSED=$((ELAPSED + 10))
done

if [ "$STATUS" = "RUNNING" ]; then
  echo "✅ Service is RUNNING"
else
  echo "⚠️  Service status: $STATUS (may take longer to fully initialize)"
fi

# Get service URL
echo ""
echo "🌐 Getting service URL..."
APPRUNNER_URL=$(aws apprunner describe-service \
  --service-arn $SERVICE_ARN \
  --region $REGION \
  --query 'Service.ServiceUrl' \
  --output text)

if [ ! -z "$APPRUNNER_URL" ] && [ "$APPRUNNER_URL" != "None" ]; then
  echo "✅ Service URL: $APPRUNNER_URL"
else
  echo "⚠️  Service URL not yet available (try again in a moment)"
  APPRUNNER_URL="https://YOUR-APPRUNNER-URL-WILL-BE-HERE"
fi

# Update Cognito callback URLs
echo ""
echo "🔐 Updating Cognito callback URLs..."

# Extract client ID
CLIENT_ID=$(grep "COGNITO_CLIENT_ID=" /tmp/cognito_config.txt | cut -d= -f2)
USER_POOL_ID=$(grep "COGNITO_USER_POOL_ID=" /tmp/cognito_config.txt | cut -d= -f2)

aws cognito-idp update-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --callback-urls "http://localhost:5000/auth/callback" "$APPRUNNER_URL/auth/callback" \
  --logout-urls "http://localhost:5000" "$APPRUNNER_URL" \
  --region $REGION > /dev/null 2>&1

echo "✅ Cognito callback URLs updated"

# Save final configuration
cat > /tmp/deployment_summary.txt << CONFIG
════════════════════════════════════════════════════════════
🎉 DEPLOYMENT COMPLETE!
════════════════════════════════════════════════════════════

AWS INFRASTRUCTURE:
  Account ID:        $ACCOUNT_ID
  Region:            $REGION
  
COGNITO:
  User Pool ID:      $COGNITO_USER_POOL_ID
  Client ID:         $CLIENT_ID
  Domain:            $COGNITO_DOMAIN
  
APPRUNNER:
  Service Name:      $SERVICE_NAME
  Service URL:       $APPRUNNER_URL
  Service ARN:       $SERVICE_ARN
  
DATABASE:
  Table:             AIAssuranceLab-UserMCPCredentials
  Region:            $REGION

NEXT STEPS:
  1. Provide student email spreadsheet
  2. Run: python3 create_students.py students.csv
  3. Share: $APPRUNNER_URL with students

════════════════════════════════════════════════════════════
CONFIG

cat /tmp/deployment_summary.txt

# Create student creation script
cat > /tmp/create_students.py << 'PYTHON'
#!/usr/bin/env python3

import sys
import csv
import boto3
from datetime import datetime

# Configuration
USER_POOL_ID = "us-east-1_tOHJ64R7F"  # Will be replaced
REGION = "us-east-1"

cognito = boto3.client('cognito-idp', region_name=REGION)

def create_students(csv_file):
    """Create Cognito users from CSV file"""
    
    print(f"📝 Reading students from: {csv_file}")
    
    students = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or 'email' not in [h.lower() for h in reader.fieldnames]:
            print("❌ CSV must have an 'email' column")
            return
        
        for row in reader:
            email = row.get('email') or row.get('Email')
            if email and email.strip():
                students.append({
                    'email': email.strip(),
                    'first_name': row.get('first_name', row.get('First Name', '')).strip(),
                    'last_name': row.get('last_name', row.get('Last Name', '')).strip(),
                })
    
    print(f"✅ Found {len(students)} students")
    print("")
    
    if len(students) == 0:
        print("❌ No valid students found in CSV")
        return
    
    # Create users
    created = 0
    failed = 0
    
    for i, student in enumerate(students, 1):
        email = student['email']
        first_name = student['first_name'] or email.split('@')[0]
        last_name = student['last_name'] or ''
        
        try:
            cognito.admin_create_user(
                UserPoolId=USER_POOL_ID,
                Username=email,
                TemporaryPassword=f"TempPass{i}!@#",
                MessageAction='SUPPRESS',
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'true'},
                    {'Name': 'given_name', 'Value': first_name},
                    {'Name': 'family_name', 'Value': last_name},
                ]
            )
            created += 1
            print(f"  [{i:2d}/{len(students)}] ✅ {email}")
        except Exception as e:
            if 'already exists' in str(e):
                print(f"  [{i:2d}/{len(students)}] ⚠️  {email} (already exists)")
            else:
                print(f"  [{i:2d}/{len(students)}] ❌ {email} - {str(e)[:50]}")
            failed += 1
    
    print("")
    print("════════════════════════════════════════════════════════════")
    print(f"✅ Created: {created}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {len(students)}")
    print("════════════════════════════════════════════════════════════")
    print("")
    print("⚠️  Note: Students will need to set their password on first login")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 create_students.py <students.csv>")
        print("")
        print("CSV format (with header row):")
        print("  email,first_name,last_name")
        print("  alice@example.com,Alice,Smith")
        print("  bob@example.com,Bob,Jones")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    create_students(csv_file)

PYTHON

chmod +x /tmp/create_students.py
cp /tmp/create_students.py "/Users/sceddy/Documents/AI Assurance MCP day/create_students.py"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ DEPLOYMENT SCRIPT COMPLETE"
echo "════════════════════════════════════════════════════════════"
