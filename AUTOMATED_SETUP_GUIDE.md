# 🚀 AI Assurance Lab - Automated Setup Guide

**One-command deployment + spreadsheet-based student creation**

---

## 📋 What You Need

1. **Docker Desktop** (installed and running)
2. **Python 3.11+** (for student creation)
3. **AWS CLI** (already configured)
4. **Student email spreadsheet** (CSV with email addresses)

---

## ✅ Current Status

- ✅ **Cognito User Pool created** (`us-east-1_tOHJ64R7F`)
- ✅ **App Client created** (`5uinug9dhgb1bk9ahibq3ndahc`)
- ✅ **IAM roles configured** (AppRunner has DynamoDB & Bedrock access)
- ✅ **DynamoDB table ready** (`AIAssuranceLab-UserMCPCredentials`)
- ⏳ **Docker image** (needs build & push)
- ⏳ **AppRunner service** (will be created after Docker push)
- ⏳ **Student accounts** (waiting for your spreadsheet)

---

## 🎯 Quick Start (3 Steps)

### Step 1: Build & Deploy to AWS (5 minutes)

**Make sure Docker Desktop is running, then:**

```bash
cd "/Users/sceddy/Documents/AI Assurance MCP day"
bash DEPLOY_SCRIPT.sh
```

This will:
1. Build the Docker image
2. Push to ECR
3. Create AppRunner service
4. Update Cognito callbacks
5. Give you the service URL

**Wait for output:**
```
✅ Service URL: https://xxxxx.us-east-1.apprunner.amazonaws.com
```

### Step 2: Prepare Student Spreadsheet

Create a CSV file with your students. Two options:

**Option A: Minimal (just emails)**
```csv
email
alice@example.com
bob@example.com
charlie@example.com
```

**Option B: With names**
```csv
email,first_name,last_name
alice@example.com,Alice,Smith
bob@example.com,Bob,Jones
charlie@example.com,Charlie,Brown
```

Save as: `students.csv`

### Step 3: Create All Student Accounts (2 minutes)

```bash
cd "/Users/sceddy/Documents/AI Assurance MCP day"
bash CREATE_STUDENTS_ONLY.sh students.csv
```

Or with Python:
```bash
python3 setup_and_deploy.py students.csv
```

This will:
1. Read all emails from your CSV
2. Create Cognito accounts for each
3. Set temporary passwords
4. Mark emails as verified
5. Print results

**Output:**
```
✅ Created: 40
⚠️  Failed/Existing: 0
📊 Total: 40
```

---

## 💻 Detailed Instructions

### Pre-Deployment Checklist

Before running the deployment script:

- [ ] Docker Desktop is installed
- [ ] Docker Desktop is running (`docker ps` works)
- [ ] AWS CLI is configured (`aws sts get-caller-identity` works)
- [ ] You have Python 3.11+
- [ ] You have your student email spreadsheet ready

### Deployment Steps

#### Step 1: Start Docker Desktop

1. Open Docker Desktop (from Applications)
2. Wait for "Docker Desktop is running" message
3. Verify with: `docker ps`

#### Step 2: Run Deployment Script

```bash
cd "/Users/sceddy/Documents/AI Assurance MCP day"
bash DEPLOY_SCRIPT.sh
```

**What happens:**
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

**Save this URL!** You'll give it to students.

#### Step 3: Test the App (Optional)

Visit the URL from Step 2:
- You should see Cognito login
- Try logging in with test account
- Navigate to `/lab` for chat interface

#### Step 4: Prepare Student CSV

Create `students.csv` with student emails:

```
email,first_name,last_name
alice.smith@example.com,Alice,Smith
bob.jones@example.com,Bob,Jones
charlie.brown@example.com,Charlie,Brown
... (repeat for all 40 students)
```

#### Step 5: Create Student Accounts

```bash
bash CREATE_STUDENTS_ONLY.sh students.csv
```

**Output shows:**
```
📊 Found 40 students in students.csv

  [  1/40] ✅ alice.smith@example.com
  [  2/40] ✅ bob.jones@example.com
  [  3/40] ✅ charlie.brown@example.com
  ...
  [ 40/40] ✅ ...@example.com

════════════════════════════════════════════════════════════
✅ Created: 40
⚠️  Failed/Existing: 0
📊 Total: 40
════════════════════════════════════════════════════════════
```

#### Step 6: Share With Students

Send each student:
```
Welcome to AI Assurance Lab!

Login URL: https://xxxxx.us-east-1.apprunner.amazonaws.com

Your email: alice.smith@example.com
Temporary password: Check your email or contact proctor

First login:
1. Enter your email and temporary password
2. Set a new permanent password
3. Go to ⚙️ Credentials to add your API tokens
4. Start using the lab!

Questions? Contact the proctor.
```

---

## 🔑 Saved Configuration

After deployment, these values are saved:

**From Cognito Setup:**
- User Pool ID: `us-east-1_tOHJ64R7F`
- Client ID: `5uinug9dhgb1bk9ahibq3ndahc`
- Client Secret: `8ci7qjvf21fgo6vs4no3d9es7ltem2gb76p247aakcvoid0a36s`
- Domain: `ai-assurance-lab-1788202274.auth.us-east-1.amazoncognito.com`

**From Deployment:**
- Service URL: (will be shown after deployment)
- Service ARN: (will be shown after deployment)
- AppRunner Role: `arn:aws:iam::004878717866:role/ai-assurance-lab-apprunner-role`

---

## 🆘 Troubleshooting

### "Docker is not running"

**Solution:** Start Docker Desktop
```bash
# On Mac:
open /Applications/Docker.app

# Then wait 30 seconds and try again
bash DEPLOY_SCRIPT.sh
```

### "Docker build fails"

**Solution:** Check Dockerfile
```bash
# Try building manually
cd "/Users/sceddy/Documents/AI Assurance MCP day"
docker build -t ai-assurance-lab .

# If it fails, check requirements.txt
cat requirements.txt
```

### "ECR push fails"

**Solution:** Check AWS credentials
```bash
aws sts get-caller-identity
# Should show your account: 004878717866
```

### "Student creation fails"

**Solution:** Check CSV format
```bash
# CSV must have 'email' column (lowercase)
head students.csv
# Should show: email,first_name,last_name
```

### "AppRunner service doesn't start"

**Solution:** Check CloudWatch logs
```bash
# In AWS Console:
# AppRunner → ai-assurance-lab → Logs
# Look for error messages
```

---

## 📊 What Gets Created

### AWS Infrastructure
- ✅ Cognito User Pool
- ✅ Cognito App Client
- ✅ ECR repository
- ✅ AppRunner service
- ✅ IAM roles & policies
- ✅ DynamoDB table (already created)

### Student Accounts
- ✅ One account per student
- ✅ Email verified
- ✅ Temporary password set
- ✅ First/last names from CSV

### Application
- ✅ Flask backend
- ✅ Chat interface
- ✅ Credential management
- ✅ Encryption & security

---

## 💰 Cost Estimate

For a 4-hour lab with 40 students:

| Service | Cost |
|---------|------|
| AppRunner | $0.26 |
| DynamoDB | $5-10 |
| Bedrock (Claude) | $20-30 |
| **Total** | **~$25-40** |

Very cost-effective!

---

## ✨ You're Done!

At this point:

1. ✅ Application deployed to AWS
2. ✅ Students can log in
3. ✅ Student accounts created
4. ✅ Ready for lab day

**What's left:**
- Share lab URL with students
- Have students add their API credentials
- Run the lab!

---

## 🎯 Lab Day Checklist

**Before Lab (60 minutes):**
- [ ] Test login with student account
- [ ] Verify credential management works
- [ ] Check AppRunner is running
- [ ] Check CloudWatch logs for errors

**During Lab:**
- [ ] Monitor AppRunner dashboard
- [ ] Support students as needed
- [ ] Check logs for issues

**After Lab:**
- [ ] Collect student feedback
- [ ] Review logs
- [ ] Shutdown services (optional)

---

## 📞 Support

If you encounter issues:

1. **Check CloudWatch logs:**
   ```bash
   aws logs tail /aws/apprunner/ai-assurance-lab --follow --region us-east-1
   ```

2. **Check AppRunner status:**
   ```bash
   aws apprunner list-services --region us-east-1
   ```

3. **Check Cognito:**
   ```bash
   aws cognito-idp list-users --user-pool-id us-east-1_tOHJ64R7F --region us-east-1
   ```

4. **Check DynamoDB:**
   ```bash
   aws dynamodb scan --table-name AIAssuranceLab-UserMCPCredentials --region us-east-1
   ```

---

## 🚀 Ready?

```bash
# Make sure Docker is running, then:
cd "/Users/sceddy/Documents/AI Assurance MCP day"
bash DEPLOY_SCRIPT.sh

# Then after deployment:
bash CREATE_STUDENTS_ONLY.sh students.csv
```

**Let's go!** 🎓

