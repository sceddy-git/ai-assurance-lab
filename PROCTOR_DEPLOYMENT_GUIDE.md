# AI Assurance Lab - Proctor Guide (DEPRECATED - Use Automated Version)

⚠️ **IMPORTANT:** This guide is for reference only. Please use the **automated guide** instead:

👉 **[PROCTOR_GUIDE_AUTOMATED.md](PROCTOR_GUIDE_AUTOMATED.md)** ← **Read this instead!**

---

## What Changed

Everything is now **fully automated**. You no longer need to:
- Manually create Cognito User Pool
- Manually create DynamoDB table
- Manually create AppRunner service
- Manually manage environment variables

**All you do:**
1. Start Docker Desktop
2. Run: `bash DEPLOY_SCRIPT.sh`
3. Provide student CSV
4. Run: `bash CREATE_STUDENTS_ONLY.sh students.csv`
5. Done!

---

## Overview

This document covers everything you need to set up and run the AI Assurance Lab for 40 students. The application is production-ready and securely deploys to AWS AppRunner with encrypted, per-user credential storage.

---

## Part 1: Pre-Deployment Checklist (15 minutes)

### AWS Account Setup
- [ ] AWS Account active (Account ID: 004878717866)
- [ ] AWS CLI configured: `aws configure` (already done)
- [ ] IAM permissions for:
  - [ ] ECR (create/push images)
  - [ ] AppRunner (create services)
  - [ ] DynamoDB (read/write)
  - [ ] Bedrock (invoke models)
  - [ ] Cognito (manage user pools)

### AWS Services Status
- [ ] Bedrock enabled in us-east-1 (Claude 3.5 Sonnet)
- [ ] DynamoDB table created: ✅ `AIAssuranceLab-UserMCPCredentials`
- [ ] Cognito User Pool: ⏳ Needs creation

### Local Environment
- [ ] Docker installed and running
- [ ] Python 3.11+ installed
- [ ] Git configured (optional, for version control)

---

## Part 2: Deploy to AWS AppRunner (30 minutes)

### Step 1: Build and Push Docker Image

**Option A: Using Docker Desktop (Recommended)**

```bash
cd "/Users/sceddy/Documents/AI Assurance MCP day"

# Login to ECR
ACCOUNT_ID="004878717866"
REGION="us-east-1"
REPO_NAME="ai-assurance-lab"

aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build Docker image
docker build -t $REPO_NAME .

# Tag for ECR
docker tag $REPO_NAME:latest \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest

# Push to ECR
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest
```

**Option B: Using AWS CodeBuild (If Docker not available)**

Contact AWS support to create a CodeBuild project that builds the image from source.

### Step 2: Create Cognito User Pool

**In AWS Console:**

1. Go to: https://console.aws.amazon.com/cognito/v2/idp/user-pools
2. Click "Create user pool"
3. Configure:
   - **Name**: `AI-Assurance-Lab`
   - **Sign-in options**: Email
   - **User attribute verification**: Email (recommended)
   - Click "Next"
4. Configure password policy:
   - **Length**: 8 minimum
   - **Complexity**: Recommended (uppercase, numbers, special)
   - Click "Next"
5. MFA Configuration:
   - **MFA requirement**: Optional
   - Click "Next"
6. Review and create user pool
7. **Note the User Pool ID** (format: `us-east-1_XXXXXXXXX`)

### Step 3: Create Cognito App Client

In the User Pool created above:

1. Go to **App integration** → **App clients and analytics**
2. Click **Create app client**
3. Configure:
   - **App client name**: `ai-assurance-lab-web`
   - **App type**: Web
   - **Auth flows**: ALLOW_USER_PASSWORD_AUTH, ALLOW_REFRESH_TOKEN_AUTH
   - Click **Next**
4. Configure allowed redirect URIs:
   ```
   http://localhost:5000/auth/callback
   https://<YOUR-APPRUNNER-URL>/auth/callback
   ```
5. Sign-out URI:
   ```
   http://localhost:5000
   https://<YOUR-APPRUNNER-URL>
   ```
6. Create app client
7. **Note the Client ID and Client Secret** (Save these!)

### Step 4: Create AppRunner Service

**In AWS Console:**

1. Go to: https://console.aws.amazon.com/apprunner/home?region=us-east-1
2. Click **Create service**
3. **Source configuration**:
   - Source: Amazon ECR
   - ECR image URI: `004878717866.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab:latest`
   - Deployment triggers: Uncheck (manual deployments)
4. **Service name**: `ai-assurance-lab`
5. **Port**: `8080`
6. Click **Next**
7. **Configure environment variables**:
   ```
   COGNITO_DOMAIN=<YOUR-COGNITO-DOMAIN>
   COGNITO_CLIENT_ID=<YOUR-CLIENT-ID>
   COGNITO_CLIENT_SECRET=<YOUR-CLIENT-SECRET>
   COGNITO_REGION=us-east-1
   APP_URL=https://<YOUR-APPRUNNER-URL>
   BEDROCK_REGION=us-east-1
   DYNAMODB_TABLE=AIAssuranceLab-UserMCPCredentials
   DYNAMODB_REGION=us-east-1
   ENCRYPTION_KEY=_qQQ4RA6lWJLZx4hd6x5_2_iL5O2cy6TVKqMoxfr5lE=
   FLASK_ENV=production
   SECRET_KEY=7d59613052a7c5f7f8c98385cc01e3aa2a19bd58e100cfbfc40cf91e11f3f44e
   ```
8. **IAM role**: Create new role with permissions:
   - DynamoDB: `ai-assurance-lab-dynamodb-access`
   - Bedrock: `bedrock:InvokeModel`
9. Click **Create & deploy**

### Step 5: Get AppRunner URL

After deployment (2-3 minutes):

1. Go to AppRunner service details
2. Copy the **Default domain** (format: `https://xxxxx.us-east-1.apprunner.amazonaws.com`)
3. **Update Cognito callback URL** with this domain:
   - Go to Cognito User Pool → App clients
   - Edit the client
   - Add callback URL: `https://<YOUR-APPRUNNER-URL>/auth/callback`
   - Add sign-out URL: `https://<YOUR-APPRUNNER-URL>/logout`
   - Save

### Step 6: Test the Deployment

```bash
# Test service is accessible
curl https://<YOUR-APPRUNNER-URL>/

# Should redirect to Cognito login
```

---

## Part 3: Create Student Accounts (Varies - ~5 min per 10 students)

### Create Users in Cognito

**In AWS Console:**

1. Go to Cognito User Pool → **Users**
2. Click **Create user**
3. For each student:
   - **Email**: student@example.com
   - **Temporary password**: Auto-generated (they'll be forced to change on first login)
   - **Mark email as verified**: Yes
   - **Send invitation**: Yes (email sent automatically)
4. Or **Bulk import** via CSV

### Batch Create Users (Recommended)

Create a CSV file `students.csv`:
```csv
email,given_name,family_name
alice.smith@example.com,Alice,Smith
bob.jones@example.com,Bob,Jones
charlie.brown@example.com,Charlie,Brown
...
```

Then use AWS CLI:
```bash
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username alice.smith@example.com \
  --message-action SUPPRESS \
  --temporary-password TempPass123! \
  --user-attributes Name=email,Value=alice.smith@example.com
```

Or create a script in Python:
```python
import boto3

cognito = boto3.client('cognito-idp')
user_pool_id = 'us-east-1_XXXXXXXXX'

students = [
    ('alice.smith@example.com', 'Alice', 'Smith'),
    ('bob.jones@example.com', 'Bob', 'Jones'),
    # ... 38 more students
]

for email, first, last in students:
    cognito.admin_create_user(
        UserPoolId=user_pool_id,
        Username=email,
        TemporaryPassword='TempPass123!',
        MessageAction='SUPPRESS',
        UserAttributes=[
            {'Name': 'email', 'Value': email},
            {'Name': 'given_name', 'Value': first},
            {'Name': 'family_name', 'Value': last},
        ]
    )
    print(f"Created: {email}")
```

### Send Login Instructions

Send each student:

```
Welcome to the AI Assurance Lab!

Login URL: https://<YOUR-APPRUNNER-URL>

Your email: [student@example.com]
Temporary password: [sent via email]

On first login:
1. You'll be prompted to set a new password
2. You'll be redirected to the lab chat
3. Go to "⚙️ Credentials" to add your API tokens

Lab Guide: [Attach AI-Assurance_Lab-Guide.html or provide link]
```

---

## Part 4: Day-of-Lab Setup (30 minutes before lab)

### 1 Hour Before Lab

- [ ] Test the app: Visit https://<YOUR-APPRUNNER-URL>
- [ ] Verify Cognito login works
- [ ] Test credential management (add test tokens)
- [ ] Test chat with Claude (verify Bedrock access)
- [ ] Check DynamoDB table is accessible

### 30 Minutes Before Lab

- [ ] Send login link to all students
- [ ] Have students log in and set passwords
- [ ] Verify 40 students can access the app
- [ ] Check AppRunner service is healthy (green status)

### Lab Troubleshooting

**If students can't log in:**
1. Check Cognito User Pool is active
2. Verify their account exists
3. Check callback URL is correct
4. Have them clear browser cache and cookies

**If credentials won't save:**
1. Check DynamoDB table exists: `AIAssuranceLab-UserMCPCredentials`
2. Verify IAM role has DynamoDB permissions
3. Check ENCRYPTION_KEY is set
4. Check CloudWatch logs in AppRunner

**If chat doesn't work:**
1. Verify Bedrock is enabled in us-east-1
2. Check Bedrock model access (Claude 3.5 Sonnet)
3. Verify IAM permissions for bedrock:InvokeModel

---

## Part 5: Student Workflow (During Lab)

### What Each Student Does

1. **Login**
   - Email: student@example.com
   - Password: (set during first login)

2. **Add Credentials** (in "⚙️ Credentials" page)
   - ThousandEyes API token (from their account)
   - Meraki API token (from their dashboard)
   - Test connectivity

3. **Chat with Claude**
   - Ask questions about their network
   - Claude will use their stored credentials
   - Can view ThousandEyes alerts, Meraki devices, etc.

### Student Security

Each student's credentials are:
- ✅ Encrypted in DynamoDB (application-level encryption)
- ✅ Isolated per-user (Student A cannot access Student B's tokens)
- ✅ Never exposed to frontend
- ✅ Revocable anytime

---

## Part 6: Monitoring & Support (During Lab)

### Monitor AppRunner Service

```bash
# Check service status
aws apprunner describe-service \
  --service-arn arn:aws:apprunner:us-east-1:004878717866:service/ai-assurance-lab/... \
  --region us-east-1

# View logs (real-time)
aws apprunner describe-service-logs \
  --service-arn ... --region us-east-1
```

### Monitor Student Activity

```bash
# Check DynamoDB for credential storage
aws dynamodb scan \
  --table-name AIAssuranceLab-UserMCPCredentials \
  --region us-east-1 \
  --projection-expression "email,#c,#u" \
  --expression-attribute-names '{"#c":"te_connected","#u":"updated_at"}'
```

### Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| "Invalid token" when testing credentials | Student pasted wrong token | Have them check token in their API dashboard |
| "Connection timeout" | Network issue or invalid API endpoint | Check ThousandEyes/Meraki API status |
| Slow chat responses | Bedrock rate limiting or model overload | Wait 30 seconds and retry |
| Credential not saving | DynamoDB issue | Check CloudWatch logs |
| 404 errors | AppRunner service crashed | Restart service in AWS Console |

---

## Part 7: Post-Lab Cleanup (Optional)

### Keep Data (For Assessment)

If you want to keep conversation data:
```bash
# Export DynamoDB table
aws dynamodb export-table-to-pointin-time \
  --table-arn arn:aws:dynamodb:us-east-1:004878717866:table/AIAssuranceLab-UserMCPCredentials
```

### Shutdown (If Temporary)

To pause the lab (cost-saving):
```bash
# Delete AppRunner service
aws apprunner delete-service \
  --service-arn arn:aws:apprunner:us-east-1:004878717866:service/ai-assurance-lab/... \
  --region us-east-1
```

To restart:
```bash
# Re-deploy using AppRunner console
# All data in DynamoDB is preserved
```

### Full Cleanup (Delete Everything)

```bash
# Delete AppRunner service
aws apprunner delete-service --service-arn ... --region us-east-1

# Delete Cognito User Pool
aws cognito-idp delete-user-pool --user-pool-id us-east-1_XXXXXXXXX --region us-east-1

# Delete DynamoDB table
aws dynamodb delete-table --table-name AIAssuranceLab-UserMCPCredentials --region us-east-1

# Delete ECR repository
aws ecr delete-repository --repository-name ai-assurance-lab --force --region us-east-1
```

---

## Part 8: Reference Information

### Application URLs

| Purpose | URL |
|---------|-----|
| Lab Homepage | https://<YOUR-APPRUNNER-URL> |
| Chat Interface | https://<YOUR-APPRUNNER-URL>/lab |
| Credential Management | https://<YOUR-APPRUNNER-URL>/credentials |
| API Endpoint | https://<YOUR-APPRUNNER-URL>/api/chat |

### Key Credentials (Save These!)

```
Cognito User Pool ID: us-east-1_XXXXXXXXX
Cognito Client ID: XXXXXXXXXXXXXX
Cognito Client Secret: XXXXXXXXXXXXXX
AppRunner URL: https://xxxxx.us-east-1.apprunner.amazonaws.com
```

### DynamoDB Table Schema

```
Table: AIAssuranceLab-UserMCPCredentials
Partition Key: email (String)

Attributes:
  email (String) - Student email
  thousandeyes_token (String) - Encrypted token
  meraki_token (String) - Encrypted token
  te_connected (Boolean) - ThousandEyes status
  meraki_connected (Boolean) - Meraki status
  created_at (Number) - Unix timestamp
  updated_at (Number) - Unix timestamp
```

### Environment Variables

All configured in AppRunner:

```
COGNITO_DOMAIN=your-pool.auth.us-east-1.amazoncognito.com
COGNITO_CLIENT_ID=your-client-id
COGNITO_CLIENT_SECRET=your-client-secret
COGNITO_REGION=us-east-1
APP_URL=https://your-apprunner-url
BEDROCK_REGION=us-east-1
DYNAMODB_TABLE=AIAssuranceLab-UserMCPCredentials
DYNAMODB_REGION=us-east-1
ENCRYPTION_KEY=_qQQ4RA6lWJLZx4hd6x5_2_iL5O2cy6TVKqMoxfr5lE=
FLASK_ENV=production
SECRET_KEY=7d59613052a7c5f7f8c98385cc01e3aa2a19bd58e100cfbfc40cf91e11f3f44e
```

---

## Part 9: Support & Documentation

### For Detailed Information

- **README.md** - Complete setup and API reference
- **QUICKSTART.md** - 5-minute setup guide
- **IMPLEMENTATION_SUMMARY.md** - Technical architecture
- **AI-Assurance_Lab-Guide.html** - Student lab guide

### Troubleshooting Resources

- CloudWatch Logs: `AppRunner` → Service logs
- DynamoDB: Check table exists and has data
- Cognito: Verify User Pool status
- Bedrock: Check model availability in us-east-1

### Contact

For issues:
1. Check CloudWatch logs first
2. Review this guide's troubleshooting section
3. Verify AWS service status at https://status.aws.amazon.com

---

## Quick Checklist for Lab Day

```
⏱️  60 Minutes Before:
  [ ] Test login (visit URL, sign in with test account)
  [ ] Add test credentials (ThousandEyes, Meraki)
  [ ] Test chat with Claude
  [ ] Verify AppRunner is healthy (green status)

⏱️  30 Minutes Before:
  [ ] Send login link to all 40 students
  [ ] Have students begin logging in
  [ ] Monitor successful logins
  [ ] Have backup credentials ready (in case of issues)

⏱️  Lab Time:
  [ ] Monitor AppRunner dashboard
  [ ] Check CloudWatch logs for errors
  [ ] Have tech support contact ready
  [ ] Take notes on any issues for post-lab analysis

⏱️  After Lab:
  [ ] Review logs for errors
  [ ] Note engagement metrics
  [ ] Optionally export DynamoDB data
  [ ] Plan cleanup/shutdown
```

---

## Success Criteria

Lab is successful if:
- ✅ All 40 students can log in
- ✅ Students can add credentials without errors
- ✅ Chat works for students with valid credentials
- ✅ No credential leakage between students
- ✅ AppRunner stays stable throughout lab (< 2% error rate)

---

**You're all set!** The application is production-ready and secured for 40 students. Follow this guide and your lab will run smoothly. 🚀

