# Manual AWS Deployment Guide

Due to CodeBuild configuration issues, here's a manual step-by-step guide to deploy the lab using AWS CLI commands.

## Prerequisites

- AWS CLI configured
- AWS credentials with proper permissions
- Dockerfile present in project directory

## Steps

### Step 1: Build Docker Image Locally

If you have Docker running:
```bash
docker build -t ai-assurance-lab:latest .
```

### Step 2: Push to Amazon ECR

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 004878717866.dkr.ecr.us-east-1.amazonaws.com

# Tag image
docker tag ai-assurance-lab:latest 004878717866.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab:latest

# Push to ECR
docker push 004878717866.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab:latest
```

### Step 3: Create AppRunner Service

If the service doesn't exist:
```bash
aws apprunner create-service \
  --service-name ai-assurance-lab \
  --source-configuration ImageRepository='{ImageIdentifier=004878717866.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab:latest,ImageRepositoryType=ECR,ImageConfiguration={Port=8080}}' \
  --instance-role-arn arn:aws:iam::004878717866:role/ai-assurance-lab-apprunner-role \
  --region us-east-1
```

If the service exists:
```bash
aws apprunner update-service \
  --service-arn <your-service-arn> \
  --source-configuration ImageRepository='{ImageIdentifier=004878717866.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab:latest,ImageRepositoryType=ECR,ImageConfiguration={Port=8080}}' \
  --region us-east-1
```

### Step 4: Monitor Deployment

```bash
# Get service status
aws apprunner describe-service \
  --service-arn <your-service-arn> \
  --region us-east-1 \
  --query 'Service.{Status:Status,ServiceUrl:ServiceUrl}'

# Wait for status to be RUNNING
```

### Step 5: Get Service URL

```bash
aws apprunner describe-service \
  --service-arn <your-service-arn> \
  --region us-east-1 \
  --query 'Service.ServiceUrl' \
  --output text
```

## Finding Your Service ARN

```bash
aws apprunner list-services \
  --region us-east-1 \
  --query "ServiceSummaryList[?ServiceName=='ai-assurance-lab'].ServiceArn" \
  --output text
```

## After Deployment

Once you have the Lab URL:

1. Create `students.csv` with student emails
2. Run: `bash CREATE_STUDENTS_ONLY.sh students.csv`
3. Share Lab URL with students

## Troubleshooting

### Docker not pushing to ECR
- Ensure ECR repository exists: `aws ecr describe-repositories --repository-names ai-assurance-lab --region us-east-1`
- Check credentials: `aws sts get-caller-identity`
- Try authenticating again: `aws ecr get-login-password --region us-east-1 | docker login ...`

### AppRunner service won't start
- Check logs: `aws logs tail /aws/apprunner/ai-assurance-lab --follow --region us-east-1`
- Verify image exists in ECR: `aws ecr describe-images --repository-name ai-assurance-lab --region us-east-1`
- Check IAM role permissions: `aws iam get-role --role-name ai-assurance-lab-apprunner-role --region us-east-1`
