# 🎓 AI Assurance Lab - Complete Proctor Setup Guide

**Simple, step-by-step guide for any proctor (no technical experience required)**

---

## 📋 Overview

This guide covers **everything** a proctor needs to set up and run the AI Assurance Lab for 40 students.

- ⏱️ **Setup Time: ~20 minutes**
- 💰 **Cost: $25-40 for 4-hour lab**
- ✅ **No Docker Desktop required**
- ✅ **Everything runs in AWS**
- ✅ **Fully automated**

---

## Part 1: Prerequisites (Verify You Have These)

### Before You Start

Check that you have:

- [ ] AWS CLI configured on your computer
  ```bash
  aws sts get-caller-identity
  # Should show: Account: 004878717866
  ```

- [ ] Python 3.11+ (for student creation script)
  ```bash
  python3 --version
  # Should show: Python 3.11.x or higher
  ```

- [ ] List of 40 student email addresses
  - First names (optional)
  - Last names (optional)

**That's all you need!** No Docker Desktop, no AWS Console access, just AWS CLI.

---

## Part 2: One-Command Setup (10 minutes)

### Step 1: Navigate to Project Directory

```bash
cd "/Users/sceddy/Documents/AI Assurance MCP day"
```

### Step 2: Run the Deployment Script

```bash
bash AWS_DEPLOY.sh
```

**What this command does:**

1. ✅ Creates a CodeBuild project in AWS
2. ✅ Builds the Docker image in AWS (not on your computer)
3. ✅ Pushes the image to Amazon ECR
4. ✅ Creates AppRunner service
5. ✅ Waits for service to be RUNNING
6. ✅ Gives you the Lab URL

**Expected output (takes 10-15 minutes):**

```
🚀 AWS-NATIVE DEPLOYMENT
════════════════════════════════════════════════════════════

Step 1: Setting up CodeBuild project...
✅ CodeBuild project ready

Step 2: Creating buildspec.yml...
✅ buildspec.yml created

Step 3: Uploading project and triggering CodeBuild...
✅ Build triggered: arn:aws:codebuild:...
   Monitor at: https://console.aws.amazon.com/...

Step 4: Waiting for build to complete (3-5 minutes)...
  Current status: IN_PROGRESS
  Current status: SUCCEEDED
✅ Build succeeded!

Step 5: Creating/updating AppRunner service...
✅ Service created: arn:aws:apprunner:...

Step 6: Waiting for AppRunner to be RUNNING (2-3 minutes)...
  Current status: OPERATION_IN_PROGRESS
  Current status: RUNNING
✅ Service is RUNNING!

Step 7: Getting service URL...

════════════════════════════════════════════════════════════
✅ DEPLOYMENT COMPLETE!
════════════════════════════════════════════════════════════

🌐 Lab URL:
   https://xxxxx.us-east-1.apprunner.amazonaws.com

NEXT STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Create your student list (students.csv)
2. Run: bash CREATE_STUDENTS_ONLY.sh students.csv
3. Share the Lab URL with students

════════════════════════════════════════════════════════════
```

**✅ Step 2 Complete!** You now have:
- ✅ Lab application running on AppRunner
- ✅ Lab URL (save this!)
- ✅ Everything ready for students

---

## Part 3: Create Student Accounts (5 minutes)

### Step 1: Create students.csv File

In the same directory, create a file called `students.csv` with your student list.

**Format (exactly like this):**

```csv
email,first_name,last_name
alice.smith@example.com,Alice,Smith
bob.jones@example.com,Bob,Jones
charlie.brown@example.com,Charlie,Brown
david.garcia@example.com,David,Garcia
emma.wilson@example.com,Emma,Wilson
... repeat for all 40 students ...
```

**Just need emails?** You can skip first_name/last_name:

```csv
email
alice@example.com
bob@example.com
charlie@example.com
... etc ...
```

**Save the file as:** `students.csv` (in same directory as the lab code)

### Step 2: Create All Student Accounts

Run this command:

```bash
bash CREATE_STUDENTS_ONLY.sh students.csv
```

**What this does:**
1. Reads all emails from your CSV file
2. Creates a Cognito account for each student
3. Sets a temporary password for each
4. Marks email as verified
5. Shows you success/failure count

**Expected output:**

```
👥 Creating students from: students.csv
📊 Found 40 students in students.csv

  [  1/40] ✅ alice.smith@example.com
  [  2/40] ✅ bob.jones@example.com
  [  3/40] ✅ charlie.brown@example.com
  ... (continues for all 40) ...
  [ 40/40] ✅ emma.wilson@example.com

════════════════════════════════════════════════════════════
✅ Created: 40
⚠️  Failed/Existing: 0
📊 Total: 40
════════════════════════════════════════════════════════════

Next: Share the lab URL with students
```

**✅ Step 3 Complete!** All 40 students can now log in!

---

## Part 4: Send Login Instructions to Students (1 minute)

### What to Send

Send each student an email with:

```
Subject: AI Assurance Lab - Login Instructions

Welcome to the AI Assurance Lab!

🌐 Lab URL: https://xxxxx.us-east-1.apprunner.amazonaws.com
(Replace xxxxx with your actual URL from Step 2)

📧 Your Email: alice.smith@example.com

🔐 Your First Login:
   1. Visit the Lab URL above
   2. Enter your email address
   3. Check your email for temporary password (should arrive in 1-2 minutes)
   4. Enter the temporary password
   5. You'll be prompted to set a new permanent password
   6. After login, you'll see the chat interface

⚙️ Next Steps:
   1. Click on ⚙️ Credentials (top right)
   2. Add your ThousandEyes API token (if you have one)
   3. Add your Meraki API token (if you have one)
   4. Click "Test Connection" to verify
   5. Go back to chat and start asking questions!

📚 Lab Guide: [Attach AI-Assurance_Lab-Guide.html or provide link]

Questions? Contact the proctor.
```

**✅ Step 4 Complete!** Students can now log in and start using the lab!

---

## Part 5: During the Lab (Monitoring)

### Before Lab Starts (60 minutes before)

- [ ] Test the app yourself
  - Visit the Lab URL
  - Log in with one of your student accounts
  - Verify you can see the chat interface
  - Check that Credentials page loads

- [ ] Verify AppRunner is healthy
  ```bash
  aws apprunner list-services --region us-east-1
  # Should show Status: RUNNING
  ```

- [ ] Have a few students test login early
  - Help with any password/email issues
  - Make sure they can see the interface

### During Lab (Every 30 minutes)

**Quick check:**
```bash
aws apprunner list-services --region us-east-1
# Make sure Status is still RUNNING
```

**What to look for:**
- ✅ Service status is RUNNING
- ✅ Students can log in
- ✅ Chat is responding
- ✅ No major errors

### If Something Breaks

**Lab URL not loading:**
```bash
# Check if AppRunner is still running
aws apprunner list-services --region us-east-1

# If status is not RUNNING, restart it
aws apprunner restart-service \
  --service-arn arn:aws:apprunner:us-east-1:004878717866:service/ai-assurance-lab/... \
  --region us-east-1
```

**Student can't log in:**
1. Have them clear browser cache and try again
2. Check: Did they set a permanent password? (not using temporary password)
3. Reset password if needed:
   ```bash
   aws cognito-idp admin-set-user-password \
     --user-pool-id us-east-1_tOHJ64R7F \
     --username alice@example.com \
     --password NewPassword123! \
     --permanent \
     --region us-east-1
   ```

**Chat not responding:**
- Usually just slow (3-5 sec)
- Have student refresh the page
- Check CloudWatch logs:
  ```bash
  aws logs tail /aws/apprunner/ai-assurance-lab --follow --region us-east-1
  ```

---

## Part 6: After the Lab - Your Options

### Option A: Keep Running & Reuse for Next Lab (⭐ Recommended for Same Week)

**This is the smart approach!** Keep infrastructure running and just reset students for your next lab.

```bash
# After Lab 1 completes:
bash RESET_USERS.sh next_cohort.csv

# ⏱️  Only 3 minutes!
# ✅ AppRunner stays warm
# ✅ All old students deleted
# ✅ All new students created
# ✅ Lab ready to go
```

**Benefits:**
- ✅ **17 minutes faster** than full deployment (3 min vs 20 min)
- ✅ **$20-35 cheaper** per lab (just DynamoDB scans, no re-deployment)
- ✅ Can run **5 labs in one day** with minimal setup
- ✅ AppRunner already warmed up

**Good for:** Back-to-back labs, same week, multiple cohorts

**See full guide:** `RESET_USERS_BETWEEN_LABS.md`

### Option B: Shut Down AppRunner, Keep Data (For Week-Long Breaks)

If you're taking a break and won't need the lab for 1+ weeks:

```bash
# Delete AppRunner to save idle costs
aws apprunner delete-service \
  --service-arn arn:aws:apprunner:us-east-1:004878717866:service/ai-assurance-lab/... \
  --region us-east-1

# ✅ Saves: ~$0.065/hour × 168 hours = ~$11/week
# ✅ Data stays: DynamoDB and Cognito keep all accounts
```

When you're ready for the next lab:
```bash
bash AWS_DEPLOY.sh  # 10 minutes to redeploy
```

**Benefits:**
- ✅ Saves money on idle services ($11+/week)
- ✅ All student data/accounts preserved
- ✅ Can redeploy in 10 minutes anytime

**Good for:** Week-long breaks between cohorts, or scheduled shutdown

### Option C: Keep Everything Running (Maximum Convenience)

If budget is not a concern and you want maximum uptime:

```bash
# Just leave everything running!
# Services stay active and ready

# When you need new students:
bash RESET_USERS.sh new_students.csv  # 3 minutes

# Cost: ~$0.065/hr for AppRunner idle time
# That's ~$13/week if running 24/7
```

**Good for:** Week-long training programs, on-demand labs

### Optional: Save Deployment Info

The script saves deployment info to: `DEPLOYMENT_INFO.txt`

Contains:
- Lab URL
- Service ARN
- Build ID
- Deployment date/time

---

## 🎯 Complete Quick Reference

### Setup Summary

| Step | Time | Command |
|------|------|---------|
| 1. Deploy | 10 min | `bash AWS_DEPLOY.sh` |
| 2. Create students.csv | 5 min | Create CSV file |
| 3. Create accounts | 2 min | `bash CREATE_STUDENTS_ONLY.sh students.csv` |
| 4. Share with students | 1 min | Send Lab URL |
| **Total (First Lab)** | **~20 min** | |

### Reset Between Labs (Reuse Infrastructure!)

| Step | Time | Command |
|------|------|---------|
| 1. Create new students.csv | 5 min | Create CSV file |
| 2. Reset users & create accounts | 3 min | `bash RESET_USERS.sh students.csv` |
| 3. Share Lab URL | 1 min | Send same URL as before |
| **Total (Subsequent Labs)** | **~3 min** | Saves 17 minutes! |

### Key Commands

```bash
# FIRST LAB: Deploy everything
bash AWS_DEPLOY.sh

# Create student accounts
bash CREATE_STUDENTS_ONLY.sh students.csv

# SUBSEQUENT LABS: Reset users and create new accounts (REUSE INFRASTRUCTURE!)
bash RESET_USERS.sh students.csv
# This deletes old users, clears credentials, and creates new students in 3 minutes!

# Reuse lab without resetting
aws apprunner list-services --region us-east-1

# View logs
aws logs tail /aws/apprunner/ai-assurance-lab --follow --region us-east-1

# Restart service (if needed)
aws apprunner restart-service --service-arn <arn> --region us-east-1

# Clean up: Delete AppRunner (optional, to save money during breaks)
aws apprunner delete-service --service-arn <arn> --region us-east-1
```

### Important URLs

```
Lab URL: https://xxxxx.us-east-1.apprunner.amazonaws.com

AWS Dashboards:
  AppRunner: https://console.aws.amazon.com/apprunner/
  CodeBuild: https://console.aws.amazon.com/codesuite/codebuild/
  CloudWatch Logs: https://console.aws.amazon.com/logs/
  Cognito: https://console.aws.amazon.com/cognito/
  DynamoDB: https://console.aws.amazon.com/dynamodb/
```

---

## 💾 Architecture (What's Running)

```
AWS Infrastructure:
├── AppRunner (web server)
│   └── Flask application (running your lab)
├── DynamoDB (database)
│   └── Student credentials (encrypted)
├── Cognito (authentication)
│   └── Student accounts & logins
├── Bedrock (AI)
│   └── Claude 3.5 Sonnet responses
└── CloudWatch (monitoring)
    └── Application logs
```

**All managed automatically.** You don't need to configure anything!

---

## 🔐 Security (What You Should Know)

### Student Credentials

- ✅ Each student's API tokens are **encrypted** in the database
- ✅ Tokens are **isolated** per student (Alice can't see Bob's tokens)
- ✅ Tokens are **never logged** or exposed to the interface
- ✅ Database is **encrypted at rest** by AWS

### Your Lab Data

- ✅ Everything **HTTPS encrypted** in transit
- ✅ **Sessions timeout** after 4 hours (security + cost)
- ✅ **No student data** is stored outside DynamoDB
- ✅ You can **delete everything** anytime

---

## 💰 Cost Breakdown (4-hour lab with 40 students)

| Service | Cost |
|---------|------|
| AppRunner (4 hours @ $0.065/hr) | $0.26 |
| DynamoDB (40 students adding credentials) | $5-10 |
| Bedrock (Claude API calls) | $20-30 |
| **Total** | **~$25-40** |

**Per student:** ~$0.60-$1.00

Very cost-effective!

---

## ❓ FAQ

### "How do I get my Lab URL?"
After `bash AWS_DEPLOY.sh` completes, it prints the Lab URL. Save it!

### "Can I keep the lab running and just swap students?"
**YES!** That's the smart approach for multiple labs. Use `bash RESET_USERS.sh students.csv` to:
- Delete old students (1 min)
- Clear their credentials (30 sec)
- Create new students (1-2 min)
- Total: 3 minutes vs 20 minutes for full redeploy!

### "How much does it cost to keep the lab running between sessions?"
**$0.065/hour** for AppRunner idle. That's about **$13/week** if running 24/7. Minimal cost!

### "Can students use their own API tokens?"
Yes! In the ⚙️ Credentials page, they add their own ThousandEyes/Meraki tokens.

### "What if deployment fails?"
Run the script again. It will detect existing resources and update them.

### "Can I run multiple labs in one day?"
**Absolutely!** Deploy once, then reset users between each lab. Takes 3 minutes per reset.

### "What happens after the lab?"
You have three options:
1. **Keep running** for next lab (3-minute reset)
2. **Shut down AppRunner** if taking a break (saves money, redeploy in 10 min when needed)
3. **Keep everything running** if budget allows (maximum convenience)

### "Can I share the Lab URL?"
Yes! Anyone with the URL can log in if they have a Cognito account.

### "How do students reset their password?"
Tell them to click "Forgot Password" on the Cognito login page.

### "Is there a detailed reset guide?"
Yes! See `RESET_USERS_BETWEEN_LABS.md` for complete instructions, cost analysis, and multiple approaches.

---

## 📚 For More Details

- **AWS-Native Deployment:** `AWS_NATIVE_DEPLOYMENT.md`
- **Lab Day Checklist:** `LAB_SETUP_CHECKLIST.md`
- **Quick Reference:** `QUICK_REFERENCE.txt`
- **Student Guide:** `AI-Assurance_Lab-Guide.html`
- **Technical Details:** `README.md`

---

## ✅ Success Criteria

Your lab is successful when:

- ✅ All 40 students can log in
- ✅ Students can see the chat interface
- ✅ Chat responds to their messages (within 5 seconds)
- ✅ Students can add credentials (⚙️ page)
- ✅ No major errors in logs
- ✅ Service stays RUNNING throughout

You have everything you need to achieve this!

---

## 🚀 Ready to Deploy?

### Your 4-Step Quick Start (First Lab)

```bash
# Step 1: Deploy (10 min)
bash AWS_DEPLOY.sh
# ↓ Save the Lab URL!

# Step 2: Create students.csv (5 min)
# Format: email,first_name,last_name

# Step 3: Create accounts (2 min)
bash CREATE_STUDENTS_ONLY.sh students.csv

# Step 4: Share Lab URL with students (1 min)
```

**Total: ~20 minutes to production-ready lab!**

### Your 2-Step Quick Reset (Subsequent Labs)

```bash
# Step 1: Create new students.csv (5 min)

# Step 2: Reset & recreate students (3 min)
bash RESET_USERS.sh students.csv
# ↓ Use same Lab URL as before!
```

**Total: ~3 minutes for next lab! (Saves 17 minutes)**

---

## 💡 Key Takeaway

This is a **complete, production-ready** lab system:
- ✅ Secure (encrypted credentials, per-user isolation)
- ✅ Scalable (handles 40+ students easily)
- ✅ Automated (one command deploys everything)
- ✅ Cost-effective ($25-40 for 4-hour lab)
- ✅ Professional (enterprise-grade infrastructure)

No Docker needed. No complicated setup. Just run the script and go!

---

**You've got everything you need. Let's make this lab amazing!** 🎓

**Start here:** `bash AWS_DEPLOY.sh`

