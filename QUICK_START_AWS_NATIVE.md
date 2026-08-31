# 🚀 Quick Start - AWS-Native Deployment (No Docker Desktop)

**Deploy entirely in AWS in 3 steps - 20 minutes total**

---

## ✅ What You Need

- ✅ AWS CLI configured (`aws sts get-caller-identity` works)
- ✅ List of 40 student emails (CSV file)
- ❌ NO Docker Desktop needed!

That's it!

---

## Step 1: Deploy to AWS (10 minutes)

Run this one command:

```bash
cd "/Users/sceddy/Documents/AI Assurance MCP day"
bash AWS_DEPLOY.sh
```

**What it does:**
1. Creates a CodeBuild project in AWS
2. Builds the Docker image in AWS (not locally)
3. Pushes to ECR
4. Creates AppRunner service
5. Gives you the Lab URL

**What you'll see:**
```
✅ CodeBuild project ready
✅ buildspec.yml created
✅ Build triggered: arn:aws:codebuild:...
✅ Build succeeded!
✅ Service is RUNNING!

🌐 Lab URL:
   https://xxxxx.us-east-1.apprunner.amazonaws.com
```

**Save the Lab URL!** You'll give it to students.

---

## Step 2: Create Student File (5 minutes)

Create a file called `students.csv`:

```csv
email,first_name,last_name
alice.smith@example.com,Alice,Smith
bob.jones@example.com,Bob,Jones
charlie.brown@example.com,Charlie,Brown
david.garcia@example.com,David,Garcia
... repeat for all 40 ...
```

---

## Step 3: Create Student Accounts (2 minutes)

Run:

```bash
bash CREATE_STUDENTS_ONLY.sh students.csv
```

**Output:**
```
📊 Found 40 students in students.csv

  [  1/40] ✅ alice.smith@example.com
  [  2/40] ✅ bob.jones@example.com
  ...
  [ 40/40] ✅ ...@example.com

════════════════════════════════════════════════════════════
✅ Created: 40
⚠️  Failed/Existing: 0
📊 Total: 40
════════════════════════════════════════════════════════════
```

---

## Step 4: Share with Students (1 minute)

Send all students:

```
Welcome to AI Assurance Lab!

Lab URL: https://xxxxx.us-east-1.apprunner.amazonaws.com

Your email: alice.smith@example.com

First login:
1. Visit the Lab URL
2. Enter your email
3. Check email for temporary password
4. Set a permanent password
5. Go to ⚙️ Credentials to add API tokens
6. Start using the lab!
```

---

## Done! 🎉

**That's it.** Your lab is deployed and ready for 40 students.

- ✅ No Docker Desktop
- ✅ No local builds
- ✅ All in AWS
- ✅ 20 minutes total
- ✅ $25-40 cost for 4-hour lab

---

## If Something Goes Wrong

### "Build failed"
```bash
# Check CodeBuild logs
https://console.aws.amazon.com/codesuite/codebuild/projects/ai-assurance-lab-build/history
```

### "AppRunner won't start"
```bash
# Check AppRunner status
aws apprunner list-services --region us-east-1
```

### "Student creation failed"
- Check CSV format (email, first_name, last_name)
- Make sure Cognito User Pool exists
- Check: `aws cognito-idp describe-user-pool --user-pool-id us-east-1_tOHJ64R7F --region us-east-1`

---

## What's Actually Happening

```
You run:                          AWS does:
bash AWS_DEPLOY.sh                ↓
                           CodeBuild spins up
                           Runs: docker build .
                           Pushes to ECR
                           ↓
                           AppRunner deploys
                           Gives you URL
                           ↓
                           You get Lab URL
```

**No local Docker needed!** Everything runs in AWS.

---

## Cost

For a 4-hour lab with 40 students:

- CodeBuild (build): $0.10
- AppRunner (4 hrs): $0.26
- DynamoDB: $5-10
- Bedrock Claude: $20-30
- **Total: ~$25-40** (~$1 per student)

---

## Next Steps

1. Run: `bash AWS_DEPLOY.sh`
2. Save the Lab URL
3. Create `students.csv`
4. Run: `bash CREATE_STUDENTS_ONLY.sh students.csv`
5. Share Lab URL with students
6. Done!

---

## For More Details

See: **[AWS_NATIVE_DEPLOYMENT.md](AWS_NATIVE_DEPLOYMENT.md)**

For Lab Day: **[LAB_SETUP_CHECKLIST.md](LAB_SETUP_CHECKLIST.md)**

---

**Ready? Let's go!** 🚀

```bash
bash AWS_DEPLOY.sh
```

