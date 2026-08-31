# 🎓 AI Assurance Lab - Proctor Guide (Automated Setup)

**For: Workshop Organizers & Proctors**  
**Students: 40 (scalable to 100+)**  
**Setup Time: ~20 minutes**  
**Infrastructure: AWS (Production-Ready)**

---

## Quick Overview

This is a **production-ready AI Assurance Lab** for 40 students with:
- ✅ Secure email-based login (AWS Cognito)
- ✅ AI chat with Claude 3.5 Sonnet
- ✅ Per-user encrypted credential storage
- ✅ ThousandEyes & Meraki API integration
- ✅ Professional web interface

**All infrastructure is pre-configured. You only need to:**
1. Start Docker Desktop
2. Run one deployment script
3. Provide your student email spreadsheet
4. Run one student creation script

---

## Part 1: Pre-Lab Requirements (Verify These)

### Your Machine Requirements
- [ ] Mac with Docker Desktop installed
- [ ] AWS CLI configured (test: `aws sts get-caller-identity`)
- [ ] Python 3.11+ installed
- [ ] At least 10 GB free disk space
- [ ] Internet connection

### AWS Account
- [ ] AWS Account: `004878717866` (or your own)
- [ ] Credentials configured locally
- [ ] Bedrock Claude 3.5 Sonnet enabled in us-east-1

### Student Information
- [ ] List of 40 student email addresses
- [ ] Optional: First names and last names

---

## Part 2: Complete Setup (20 minutes total)

### Step 1: Start Docker Desktop (1 minute)

**On Mac:**
```bash
open /Applications/Docker.app
```

**Wait for the message:** "Docker Desktop is running"

**Verify Docker is ready:**
```bash
docker ps
# Should show: CONTAINER ID   IMAGE   COMMAND ...
```

### Step 2: Deploy to AWS (10 minutes)

Navigate to project directory:
```bash
cd "/Users/sceddy/Documents/AI Assurance MCP day"
```

Run the deployment script:
```bash
bash DEPLOY_SCRIPT.sh
```

**What it does:**
1. Builds Docker image locally
2. Pushes to ECR (Amazon's container registry)
3. Creates AppRunner service
4. Updates Cognito callback URLs
5. Gives you the service URL

**What you'll see:**
```
✓ Checking Docker...
✅ Docker is running

📦 Step 1: Building Docker image...
✅ Docker image built

🔐 Step 2: Login to ECR...
✅ ECR login successful

🏷️  Step 3: Tagging image for ECR...
✅ Image tagged

⬆️  Step 4: Pushing to ECR...
✅ Image pushed to ECR

🚀 Step 5: Creating AppRunner service...
✅ AppRunner service created

⏳ Waiting for service to become RUNNING...
✅ Service is RUNNING

🌐 Getting service URL...
✅ Service URL: https://xxxxx.us-east-1.apprunner.amazonaws.com
```

**⚠️ IMPORTANT:** Save the service URL! You'll give it to students.

### Step 3: Prepare Your Student List (5 minutes)

Create a CSV file with your students. **Two options:**

**Option A: Minimal (Just Emails)**
```csv
email
alice@example.com
bob@example.com
charlie@example.com
david@example.com
...
```

**Option B: With Names (Recommended)**
```csv
email,first_name,last_name
alice@example.com,Alice,Smith
bob@example.com,Bob,Jones
charlie@example.com,Charlie,Brown
david@example.com,David,Garcia
...
```

**File name:** Save as `students.csv` in the project directory

### Step 4: Create Student Accounts (2 minutes)

Run the student creation script:
```bash
bash CREATE_STUDENTS_ONLY.sh students.csv
```

**What it does:**
1. Reads all emails from your CSV
2. Creates Cognito account for each student
3. Sets temporary password for each
4. Marks email as verified
5. Prints success count

**Output:**
```
👥 Creating students from: students.csv
📊 Found 40 students in students.csv

  [  1/40] ✅ alice@example.com
  [  2/40] ✅ bob@example.com
  [  3/40] ✅ charlie@example.com
  ...
  [ 40/40] ✅ david@example.com

════════════════════════════════════════════════════════════
✅ Created: 40
⚠️  Failed/Existing: 0
📊 Total: 40
════════════════════════════════════════════════════════════
```

---

## Part 3: Send Login Instructions to Students

Send each student the lab URL and login info:

**Email Template:**
```
Subject: AI Assurance Lab - Login Instructions

Welcome to the AI Assurance Lab!

🌐 Lab URL: https://xxxxx.us-east-1.apprunner.amazonaws.com
(Replace xxxxx with your actual service URL)

📧 Your Email: alice@example.com

🔐 First Login:
   1. Visit the lab URL above
   2. Enter your email address
   3. Check your email for temporary password
   4. Log in and set a permanent password
   5. Go to ⚙️ Credentials page
   6. Add your ThousandEyes and Meraki API tokens
   7. Start using the lab!

📚 Lab Guide: [Attached or linked]

Questions? Contact the proctor.
```

---

## Part 4: Day-of-Lab Setup

### 60 Minutes Before Lab

**Verify everything is working:**
```bash
# Test login URL
# Visit: https://xxxxx.us-east-1.apprunner.amazonaws.com
# You should see Cognito login page

# Check AppRunner is running
aws apprunner list-services --region us-east-1
# Should show status: RUNNING

# Monitor logs
aws logs tail /aws/apprunner/ai-assurance-lab --follow --region us-east-1
# Should show minimal errors
```

**Test the app:**
1. Visit the service URL
2. Try logging in with a test account
3. Navigate to Credentials page
4. Try sending a chat message
5. Verify no major errors

### 30 Minutes Before Lab

**Student check-in:**
- [ ] Ask first 5-10 students if they can log in
- [ ] Help with password resets if needed
- [ ] Confirm they see the chat interface
- [ ] No urgent issues blocking them

**Environment check:**
- [ ] Network/WiFi working well
- [ ] Proctor contact method established (Slack, email, phone)
- [ ] Lab guide printed or available
- [ ] Support team ready

### During Lab

**Every 10 minutes:**
- Monitor AppRunner dashboard for errors
- Watch CloudWatch logs for issues
- Ask: "Everyone doing okay?"

**Every 30 minutes:**
- Check AppRunner metrics (CPU, memory)
- Verify database is responsive
- Note any patterns in errors

**Common Issues & Quick Fixes:**

| Issue | Quick Fix |
|-------|-----------|
| Student can't log in | Clear browser cache, try different browser, reset password |
| Chat not responding | Refresh page, wait 30 seconds, try again |
| Credentials won't save | Check DynamoDB status (usually works on second try) |
| Slow responses | Check AWS metrics, not necessarily an error |
| Student disconnected | Have them log back in (sessions auto-expire) |

### After Lab

**Optional: Capture Data**
```bash
# See which students added credentials
aws dynamodb scan \
  --table-name AIAssuranceLab-UserMCPCredentials \
  --projection-expression "email,#c,#u" \
  --expression-attribute-names '{"#c":"te_connected","#u":"updated_at"}' \
  --region us-east-1

# Download logs (last hour)
aws logs get-log-events \
  --log-group-name /aws/apprunner/ai-assurance-lab \
  --log-stream-name service-output \
  --region us-east-1 > lab_logs.json
```

**Optional: Cleanup**
```bash
# Leave running (low cost, keep for future use)
# OR delete to save costs

# Delete AppRunner service
aws apprunner delete-service \
  --service-arn <service-arn> \
  --region us-east-1

# Keep DynamoDB & Cognito (for future labs)
```

---

## Part 5: Troubleshooting

### "Docker is not running"
```bash
# Start Docker Desktop
open /Applications/Docker.app

# Wait 30 seconds
sleep 30

# Try again
bash DEPLOY_SCRIPT.sh
```

### "Docker build fails"
```bash
# Check Dockerfile
cd "/Users/sceddy/Documents/AI Assurance MCP day"
cat Dockerfile

# Try building manually
docker build -t ai-assurance-lab .

# Check for errors in output
```

### "ECR push fails"
```bash
# Verify AWS credentials
aws sts get-caller-identity
# Should show: "Account": "004878717866"

# Check ECR repo exists
aws ecr describe-repositories --region us-east-1
```

### "Student creation fails"
```bash
# Check CSV format
head students.csv
# Should show: email,first_name,last_name

# Verify first row is header
# Verify no blank lines

# Try creating one student manually
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_tOHJ64R7F \
  --username test@example.com \
  --temporary-password TempPass123! \
  --region us-east-1
```

### "AppRunner service won't start"
```bash
# Check service status
aws apprunner describe-service \
  --service-arn <arn> \
  --region us-east-1

# Check CloudWatch logs
aws logs tail /aws/apprunner/ai-assurance-lab --follow --region us-east-1

# Check IAM role has proper permissions
aws iam get-role --role-name ai-assurance-lab-apprunner-role
```

### "Students see blank page or errors"
```bash
# Check AppRunner logs
aws logs tail /aws/apprunner/ai-assurance-lab --follow --region us-east-1

# Check service is still running
aws apprunner list-services --region us-east-1 | grep RUNNING

# Restart AppRunner (if needed)
aws apprunner restart-service \
  --service-arn <arn> \
  --region us-east-1
```

---

## Part 6: Important Information

### Saved Configuration

**Cognito (Student Login):**
```
User Pool ID:     us-east-1_tOHJ64R7F
Client ID:        5uinug9dhgb1bk9ahibq3ndahc
Client Secret:    (saved in AWS Secrets Manager)
Domain:           ai-assurance-lab-1788202274.auth.us-east-1.amazoncognito.com
```

**Infrastructure:**
```
Database:         AIAssuranceLab-UserMCPCredentials (DynamoDB)
Repository:       ai-assurance-lab (ECR)
Service:          ai-assurance-lab (AppRunner)
IAM Role:         ai-assurance-lab-apprunner-role
Region:           us-east-1
```

**Encryption:**
```
Algorithm:        Fernet (symmetric AES-128)
Key Storage:      Environment variable (secure)
Per-User:         Unique derivation per student email
```

### Database Schema

**Table: AIAssuranceLab-UserMCPCredentials**
```
Partition Key:    email (String)

Attributes:
  email                (String) - Student email address
  thousandeyes_token   (String) - Encrypted API token
  meraki_token         (String) - Encrypted API token
  te_connected         (Boolean) - ThousandEyes status
  meraki_connected     (Boolean) - Meraki status
  created_at           (Number) - Unix timestamp (creation)
  updated_at           (Number) - Unix timestamp (last update)
```

### API Endpoints (For Reference)

**Student Login:**
```
GET  /                    - Login redirect
POST /auth/callback       - OAuth callback
GET  /logout              - Logout
```

**Credential Management:**
```
GET  /credentials                - Credential status page
GET  /api/credentials            - Get status (JSON)
POST /api/credentials/add        - Add/update credential
POST /api/credentials/test       - Test credential validity
POST /api/credentials/delete     - Delete credential
```

**Chat:**
```
GET  /lab                        - Chat interface
POST /api/chat                   - Send message + get AI response
```

---

## Part 7: Security & Data Protection

### Credential Encryption

Students' API tokens are:
- ✅ Encrypted using Fernet (military-grade)
- ✅ Stored in DynamoDB (encrypted at rest)
- ✅ Never logged or exposed
- ✅ Isolated per-student (no cross-access)
- ✅ Decrypted only when needed for API calls

### Student Privacy

- ✅ Emails verified in Cognito
- ✅ Sessions time out (auto-logout)
- ✅ HTTPS enforced (AppRunner)
- ✅ HttpOnly cookies (no JavaScript access)
- ✅ DynamoDB has auto-scaling (no resource exhaustion)

### No Hardcoded Secrets

All sensitive data is:
- ✅ In environment variables (not code)
- ✅ In AWS Secrets Manager (not Git)
- ✅ Never in logs
- ✅ Rotatable without code changes

---

## Part 8: Monitoring During Lab

### Dashboard Access

**AppRunner Dashboard:**
```
https://console.aws.amazon.com/apprunner/home?region=us-east-1
```

**CloudWatch Logs:**
```
https://console.aws.amazon.com/logs/
→ Log Groups → /aws/apprunner/ai-assurance-lab
```

**DynamoDB Table:**
```
https://console.aws.amazon.com/dynamodb/home?region=us-east-1
→ Tables → AIAssuranceLab-UserMCPCredentials
```

**Cognito User Pool:**
```
https://console.aws.amazon.com/cognito/v2/idp/user-pools
→ us-east-1_tOHJ64R7F → Users
```

### Key Metrics to Watch

| Metric | Healthy | Alert |
|--------|---------|-------|
| AppRunner CPU | < 70% | > 85% |
| AppRunner Memory | < 70% | > 85% |
| Response Time | < 2 sec | > 5 sec |
| Error Rate | < 1% | > 5% |
| DynamoDB Throttling | None | Any |

---

## Part 9: Cost Estimation

**For a 4-hour lab with 40 students:**

| Service | Cost |
|---------|------|
| AppRunner | ~$0.26 (compute) |
| DynamoDB | $5-10 (requests) |
| Bedrock Claude | $20-30 (API calls) |
| ECR | ~$0 (small image) |
| Cognito | Free (under limits) |
| **Total** | **~$25-40** |

**Very cost-effective!** Less than $1 per student for a full lab.

---

## Part 10: Support Resources

### Documentation Files

| File | Purpose |
|------|---------|
| `00_START_HERE_QUICK.txt` | Quick 3-step guide |
| `AUTOMATED_SETUP_GUIDE.md` | Detailed setup instructions |
| `SETUP_STATUS.md` | Current deployment status |
| `LAB_SETUP_CHECKLIST.md` | Full day-of-lab checklist |
| `AI-Assurance_Lab-Guide.html` | Student lab guide |
| `QUICK_REFERENCE.txt` | Quick API & schema reference |

### Useful Commands

**Check everything is working:**
```bash
# Verify Cognito
aws cognito-idp describe-user-pool --user-pool-id us-east-1_tOHJ64R7F --region us-east-1

# Verify AppRunner
aws apprunner list-services --region us-east-1

# Verify DynamoDB
aws dynamodb describe-table --table-name AIAssuranceLab-UserMCPCredentials --region us-east-1

# Check recent logs
aws logs tail /aws/apprunner/ai-assurance-lab --follow --region us-east-1 | head -50
```

### Contact & Escalation

1. **First-level support:** Check CloudWatch logs
2. **Second-level:** Check AppRunner service status
3. **Third-level:** Check Cognito & DynamoDB status
4. **Escalation:** AWS Support (if account has plan)

---

## Part 11: Lab Execution Checklist

### ✅ Pre-Lab (1 hour before)

```
[ ] Docker Desktop running
[ ] Test login at service URL works
[ ] Test credential management page loads
[ ] Test chat sends message
[ ] Check CloudWatch logs for errors
[ ] Verify AppRunner is healthy
[ ] Print student guide (optional)
[ ] Have contact method ready (Slack/email/phone)
```

### ✅ Lab Start

```
[ ] Welcome students
[ ] Explain lab objectives
[ ] Provide lab URL
[ ] Have them log in (watch for issues)
[ ] Direct to Credentials page
[ ] Show example API token format
[ ] Answer first questions
```

### ✅ During Lab (Every 10-30 min)

```
[ ] Monitor AppRunner metrics
[ ] Check CloudWatch logs
[ ] Ask students if they're okay
[ ] Respond to issues within 2 minutes
[ ] Keep students engaged
```

### ✅ Lab End

```
[ ] Announce closing time
[ ] Ask for feedback (optional)
[ ] Thank students
[ ] Note any technical issues
[ ] Optional: Collect logs
```

---

## Part 12: Success Criteria

Your lab is successful if:

- ✅ **100% login rate** - All 40 students can log in
- ✅ **Credential management works** - Students can add tokens without errors
- ✅ **Chat is responsive** - Responses in < 5 seconds
- ✅ **No data leaks** - Credentials isolated per-student
- ✅ **High uptime** - AppRunner stays healthy (99%+)
- ✅ **Student satisfaction** - Positive feedback on experience

---

## Quick Reference Card (Print This!)

```
LAB URL:                https://xxxxx.us-east-1.apprunner.amazonaws.com

COGNITO:                us-east-1_tOHJ64R7F
DYNAMODB:               AIAssuranceLab-UserMCPCredentials
REGION:                 us-east-1

CRITICAL COMMANDS:
  Deploy:               bash DEPLOY_SCRIPT.sh
  Create Students:      bash CREATE_STUDENTS_ONLY.sh students.csv
  Check Logs:           aws logs tail /aws/apprunner/ai-assurance-lab --follow
  Check Services:       aws apprunner list-services --region us-east-1
  Check DynamoDB:       aws dynamodb scan --table-name AIAssuranceLab-UserMCPCredentials

TROUBLESHOOTING:
  Restart AppRunner:    aws apprunner restart-service --service-arn <arn>
  Check Status:         aws apprunner describe-service --service-arn <arn>
  Student Reset Pwd:    aws cognito-idp admin-set-user-password --user-pool-id us-east-1_tOHJ64R7F --username email@example.com --password NewPass123! --permanent

SUPPORT:
  CloudWatch Logs:      https://console.aws.amazon.com/logs/
  AppRunner:            https://console.aws.amazon.com/apprunner/
  Cognito:              https://console.aws.amazon.com/cognito/
  DynamoDB:             https://console.aws.amazon.com/dynamodb/
```

---

## Appendix: Full Setup Timeline

| Phase | Time | Action |
|-------|------|--------|
| **Pre-Lab (1-2 days before)** | 30 min | Read guides, prepare student list |
| **Deployment Day** | 10 min | Start Docker, run deployment script |
| **Student Creation** | 2 min | Provide CSV, run student creation |
| **Testing (60 min before lab)** | 15 min | Test login, credentials, chat |
| **Lab (Day of)** | Flexible | Support students, monitor dashboard |
| **Total Setup Time** | **~20 min** | |

---

## Final Notes

This guide is designed for **complete automation**. You don't need to understand AWS deeply - the scripts handle all the complexity.

**If you encounter an issue:**
1. Check CloudWatch logs (usually tells you what's wrong)
2. Refer to the Troubleshooting section
3. Run the diagnostic commands
4. Contact AWS Support if needed

**For future labs:**
- Keep DynamoDB & Cognito (they don't cost much)
- Delete AppRunner service (costs more)
- Re-deploy AppRunner when needed
- All student data is preserved

---

**You're fully prepared. Good luck with your lab! 🎓**

