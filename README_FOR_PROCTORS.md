# 📚 AI Assurance Lab - Complete Proctor Documentation

**A comprehensive resource guide for all proctors (both new and experienced)**

---

## 🎯 Choose Your Path

### If you want the simplest setup (20 minutes) ⭐ **RECOMMENDED**
→ **[PROCTOR_COMPLETE_SETUP_GUIDE.md](PROCTOR_COMPLETE_SETUP_GUIDE.md)** ⭐ **START HERE**
- Everything in one document
- 4 simple steps
- One command to deploy
- AWS-native (no Docker Desktop)
- Perfect for any proctor

### If you're in a hurry (5 minutes)
→ **[QUICK_START_AWS_NATIVE.md](QUICK_START_AWS_NATIVE.md)**
- 3 simple steps
- Quick commands
- Get running in 20 minutes

### If you're running multiple labs (⭐ NEW!)
→ **[RESET_USERS_BETWEEN_LABS.md](RESET_USERS_BETWEEN_LABS.md)**
- Keep infrastructure running
- Reset users in 3 minutes (not 20!)
- Cost comparison ($20-35 cheaper per lab!)
- Multiple workflow options
- Perfect for same-week labs

### If you want all the details (30 minutes)
→ **[PROCTOR_GUIDE_AUTOMATED.md](PROCTOR_GUIDE_AUTOMATED.md)**
- Complete reference guide
- 12 comprehensive parts
- Troubleshooting section
- Lab day procedures

### If you want day-of execution checklist
→ **[LAB_SETUP_CHECKLIST.md](LAB_SETUP_CHECKLIST.md)**
- Comprehensive checklist
- Daily execution guide
- Section-by-section breakdown
- Print and use during lab

### If you need technical reference
→ **[QUICK_REFERENCE.txt](QUICK_REFERENCE.txt)**
- API endpoints
- Database schema
- Useful AWS commands
- Quick troubleshooting

### If you want the big picture (10 minutes)
→ **[SETUP_STATUS.md](SETUP_STATUS.md)**
- What's already done
- What you need to do
- Current infrastructure status

### If you're a student
→ **[AI-Assurance_Lab-Guide.html](AI-Assurance_Lab-Guide.html)**
- Lab objectives
- How to use the interface
- Example questions for Claude
- Print & share with students

---

## 📋 Documentation Overview

### For Setup & Deployment

| Document | Length | For Whom | When to Read |
|----------|--------|----------|--------------|
| **PROCTOR_GUIDE_AUTOMATED.md** | 20 min | All proctors | BEFORE first deployment |
| **00_START_HERE_QUICK.txt** | 2 min | New proctors | When in a hurry |
| **SETUP_STATUS.md** | 5 min | All | To understand current status |
| **AUTOMATED_SETUP_GUIDE.md** | 10 min | Detail-oriented | For step-by-step breakdown |
| **RESET_USERS_BETWEEN_LABS.md** | 10 min | Running multiple labs | BEFORE second+ labs |

### For Lab Execution

| Document | Length | For Whom | When to Use |
|----------|--------|----------|-------------|
| **LAB_SETUP_CHECKLIST.md** | 30 min | All proctors | Print before lab day |
| **QUICK_REFERENCE.txt** | 2 min lookup | Proctors on duty | During lab for quick answers |
| **PROCTOR_GUIDE_AUTOMATED.md** | (troubleshooting) | Proctors on duty | When issues arise |

### For Students

| Document | Length | For Whom | When to Share |
|----------|--------|----------|---------------|
| **AI-Assurance_Lab-Guide.html** | 10 min | Students | BEFORE lab day |

### Legacy / Reference (Archived)

| Document | Status | Replace With |
|----------|--------|--------------|
| **PROCTOR_DEPLOYMENT_GUIDE.md** | Deprecated | PROCTOR_GUIDE_AUTOMATED.md |
| **PROCTOR_START_HERE.md** | Archived | PROCTOR_GUIDE_AUTOMATED.md |

---

## 🚀 Quick Start (Any Proctor)

**Time to production: 20 minutes**

### Step 1: Prepare (5 minutes)
```bash
# Read the automated guide
cat PROCTOR_GUIDE_AUTOMATED.md | head -100

# Gather your student emails (40 total)
# Create students.csv with format:
# email,first_name,last_name
```

### Step 2: Deploy (10 minutes)
```bash
# Start Docker Desktop
open /Applications/Docker.app
# Wait for "Docker Desktop is running"

# Run deployment
bash DEPLOY_SCRIPT.sh
# Saves your service URL
```

### Step 3: Create Students (2 minutes)
```bash
# Create student accounts
bash CREATE_STUDENTS_ONLY.sh students.csv

# All 40 students created ✓
```

### Step 4: Share (3 minutes)
```bash
# Send students the lab URL
# They log in, set password, add credentials
# Lab is ready!
```

---

## 📖 Complete Reading List (By Role)

### New Proctor (First Time)
1. **This file** (you're reading it now)
2. **PROCTOR_GUIDE_AUTOMATED.md** (comprehensive guide)
3. **LAB_SETUP_CHECKLIST.md** (during lab preparation)
4. **QUICK_REFERENCE.txt** (bookmark for lab day)

**Total reading time: ~45 minutes**

### Returning Proctor (Running Another Lab)
1. **RESET_USERS_BETWEEN_LABS.md** (run labs faster! ⭐)
   - Keep infrastructure, just swap users
   - 3 minutes per lab instead of 20!
2. **LAB_SETUP_CHECKLIST.md** (day-of procedures)
3. **QUICK_REFERENCE.txt** (quick lookup)

**Total reading time: ~10 minutes**
**Total setup time: ~3 minutes** (vs 20 for full redeploy!)

### Tech-Savvy Proctor (Want to understand the system)
1. **PROCTOR_GUIDE_AUTOMATED.md** (setup)
2. **IMPLEMENTATION_SUMMARY.md** (technical architecture)
3. **QUICK_REFERENCE.txt** (APIs & schema)
4. **README.md** (complete documentation)

**Total reading time: ~60 minutes**

### Proctor in a Crisis (Something broke)
1. **PROCTOR_GUIDE_AUTOMATED.md** → Troubleshooting section
2. **QUICK_REFERENCE.txt** → diagnostic commands
3. **LAB_SETUP_CHECKLIST.md** → "Lab Troubleshooting" section

**Time to resolution: 5-10 minutes**

---

## 🎯 Key Concepts Every Proctor Should Know

### The Technology Stack

- **Frontend:** Professional HTML/CSS/JavaScript interface
- **Backend:** Flask Python application with 9 routes
- **Encryption:** Fernet (AES-128, per-user isolation)
- **Database:** DynamoDB (encrypted credentials per student)
- **AI:** AWS Bedrock with Claude 3.5 Sonnet
- **Auth:** AWS Cognito (email-based OAuth2)
- **Hosting:** AWS AppRunner (auto-scaling, production-ready)

### How Students Use It

1. **Login:** Email + temporary password (via Cognito)
2. **First Time:** Set permanent password
3. **Credentials:** Add ThousandEyes & Meraki API tokens (in Settings)
4. **Chat:** Ask Claude questions about their network
5. **Data:** Claude uses their tokens to pull real data
6. **Privacy:** Each student's tokens are encrypted and isolated

### How Encryption Works (Important!)

- Each student's API token is encrypted using Fernet (symmetric AES)
- The encryption key includes their email address (unique per student)
- Tokens are stored encrypted in DynamoDB
- Tokens are NEVER logged or exposed
- Only decrypted when the student asks a question
- Alice cannot decrypt Bob's tokens

### Cost Management

- **AppRunner:** ~$0.065/hour (minimal for 4-hour lab)
- **DynamoDB:** Pay-per-request ($0.125 per million reads)
- **Bedrock:** ~$0.005 per 1K tokens
- **Total for 4-hour lab:** ~$25-40 (less than $1 per student)

---

## 🔧 Troubleshooting Quick Map

**Issue → Find Solution Here**

| Problem | Read This | Command to Run |
|---------|-----------|---|
| Docker not running | PROCTOR_GUIDE_AUTOMATED.md § Part 5 | `open /Applications/Docker.app` |
| Docker build fails | LAB_SETUP_CHECKLIST.md § Troubleshooting | Check requirements.txt |
| ECR push fails | PROCTOR_GUIDE_AUTOMATED.md § Part 5 | `aws sts get-caller-identity` |
| Student creation fails | PROCTOR_GUIDE_AUTOMATED.md § Part 5 | Check CSV format first |
| AppRunner won't start | QUICK_REFERENCE.txt (Troubleshooting) | `aws apprunner list-services` |
| Student can't log in | LAB_SETUP_CHECKLIST.md § During Lab | Check Cognito console |
| Chat not responding | PROCTOR_GUIDE_AUTOMATED.md § Part 4 | Check CloudWatch logs |
| Credentials won't save | LAB_SETUP_CHECKLIST.md § Troubleshooting | Check DynamoDB table |

---

## 📊 What's Pre-Configured (You Don't Do This)

✅ **Already set up for you:**
- Cognito User Pool created
- DynamoDB table created
- ECR repository created
- IAM roles & policies set up
- Flask application built
- Encryption keys generated
- All AWS credentials configured

**You only do:**
1. ✅ Start Docker Desktop
2. ✅ Run deployment script
3. ✅ Provide student CSV
4. ✅ Run student creation script

That's it!

---

## 🎓 Sample Lab Day Timeline

**60 minutes before:**
- [ ] Test login with browser
- [ ] Check CloudWatch logs
- [ ] Verify AppRunner is healthy

**30 minutes before:**
- [ ] Send lab URL to students
- [ ] Have first students test login
- [ ] Troubleshoot any issues

**Lab time:**
- Every 10 min: Check logs
- Every 30 min: Check metrics
- Always: Respond to issues

**After lab:**
- [ ] Collect feedback
- [ ] Review logs
- [ ] Optional: Shutdown services

---

## 🔐 Security Guarantees

As a proctor, you should know:

- ✅ **No shared credentials** - Each student's tokens are isolated
- ✅ **No plaintext storage** - Tokens encrypted in database
- ✅ **No logging of secrets** - Tokens never appear in logs
- ✅ **No hardcoded secrets** - Everything in environment variables
- ✅ **HTTPS only** - All traffic encrypted in transit
- ✅ **HttpOnly cookies** - Sessions secure from JavaScript
- ✅ **GDPR compliant** - Can delete student data anytime
- ✅ **Enterprise-grade** - Production-ready infrastructure

---

## 📞 Getting Help

### For Documentation Questions
→ See the specific guide (all linked above)

### For Technical Issues
→ **PROCTOR_GUIDE_AUTOMATED.md** § Part 5 (Troubleshooting)

### For AWS-Specific Issues
→ Run diagnostic commands from QUICK_REFERENCE.txt

### For Data/Security Questions
→ **IMPLEMENTATION_SUMMARY.md** (Technical Details)

### For Emergency Support
→ AWS Support (if your account has a plan)

---

## 📝 Checklists to Print

Print and bring to lab day:

1. **LAB_SETUP_CHECKLIST.md**
   - Check off as you prepare
   - Check off during lab
   - Reference during troubleshooting

2. **QUICK_REFERENCE.txt**
   - Keep at your desk
   - Quick lookups during lab
   - Emergency commands

---

## 🌟 Pro Tips for Experienced Proctors

### Monitoring
- Set CloudWatch dashboard to auto-refresh every 30 seconds
- Monitor `errors` in AppRunner logs specifically
- DynamoDB throttling is extremely rare (pay-per-request)

### Performance
- First 5 chat requests are slower (warm-up)
- Subsequent requests should be < 2 seconds
- If consistently slow, check Bedrock availability

### Student Support
- "Clear your browser cache" fixes 80% of issues
- Password resets take 2-3 minutes to propagate
- Temporary passwords emailed are usually received in < 1 minute

### Cost Optimization
- **For same-week labs:** Keep AppRunner running, reset users ($0-5 per reset)
- **For multi-week breaks:** Delete AppRunner, redeploy when needed (saves $11+/week)
- **For long programs:** Mix both approaches
- See **RESET_USERS_BETWEEN_LABS.md** for complete cost breakdown

### Data Preservation
- Export DynamoDB before deleting AppRunner
- Save CloudWatch logs for analysis
- Note which students used which features

---

## 🚀 The Automated Scripts Explained

### DEPLOY_SCRIPT.sh
- Builds Docker image locally
- Pushes to ECR
- Creates AppRunner service
- Updates Cognito URLs
- **Time:** ~10 minutes

### CREATE_STUDENTS_ONLY.sh
- Reads CSV file
- Creates Cognito user for each
- Sets temporary passwords
- Marks emails verified
- **Time:** ~2 minutes

### RESET_USERS.sh (⭐ NEW!)
- Deletes old student accounts
- Clears stored credentials
- Creates new student accounts
- **Time:** ~3 minutes (saves 17 min vs full redeploy!)
- **Cost:** $0-5 (vs $25-40 full redeploy)

### setup_and_deploy.py
- Python alternative to DEPLOY_SCRIPT.sh
- Can also handle student creation
- Useful if bash unavailable
- **Time:** Same as shell script

---

## 📚 All Available Documents

```
/Users/sceddy/Documents/AI Assurance MCP day/

PROCTOR GUIDES:
  ✅ README_FOR_PROCTORS.md          ← You are here
  ✅ PROCTOR_GUIDE_AUTOMATED.md      ← Main setup guide
  ✅ RESET_USERS_BETWEEN_LABS.md     ← For multiple labs ⭐
  ✅ 00_START_HERE_QUICK.txt         ← Quick reference
  ✅ LAB_SETUP_CHECKLIST.md          ← Execution checklist
  ✅ SETUP_STATUS.md                 ← Current status

STUDENT MATERIALS:
  ✅ AI-Assurance_Lab-Guide.html     ← Share with students

TECHNICAL REFERENCE:
  ✅ README.md                        ← Complete docs
  ✅ IMPLEMENTATION_SUMMARY.md        ← Architecture
  ✅ QUICK_REFERENCE.txt             ← Quick lookup
  ✅ AUTOMATED_SETUP_GUIDE.md        ← Detailed setup

SCRIPTS:
  ✅ DEPLOY_SCRIPT.sh                ← One-command deploy
  ✅ CREATE_STUDENTS_ONLY.sh         ← Bulk student creation
  ✅ RESET_USERS.sh                  ← Reset users between labs ⭐
  ✅ setup_and_deploy.py             ← Python helper

APPLICATION CODE:
  ✅ app.py, crypto.py, dynamo_db.py, tool_handlers.py
  ✅ templates/lab.html, templates/credentials.html
  ✅ static/css/style.css

CONFIG & DEPLOYMENT:
  ✅ Dockerfile, requirements.txt, .env, .gitignore
```

---

## ✨ Final Thoughts

This lab is designed to be **incredibly easy** for proctors while maintaining **enterprise-grade** quality for students.

You don't need to be an AWS expert. Everything is automated.

**Your job is to:**
1. Run the scripts (pre-configured)
2. Support students (they're using familiar UI)
3. Monitor the dashboard (it tells you what's wrong)

**That's it.**

### Before You Start
- Read: **PROCTOR_GUIDE_AUTOMATED.md**
- Ask: Any remaining questions?
- Plan: Your lab day schedule

### When You Deploy
- Start Docker Desktop
- Run: `bash DEPLOY_SCRIPT.sh`
- Save the service URL

### When You Run the Lab
- Keep QUICK_REFERENCE.txt handy
- Monitor AppRunner dashboard
- Support students

### After the Lab
- Collect feedback
- Review logs (optional)
- Shutdown services (optional)

---

**You've got everything you need. Let's make this lab amazing! 🎓**

Questions? See PROCTOR_GUIDE_AUTOMATED.md

Ready to deploy? Follow 00_START_HERE_QUICK.txt

Let's go! 🚀

