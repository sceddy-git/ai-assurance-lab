# 🔄 Reset Users Between Labs (Keep Infrastructure Running)

**Reuse the lab infrastructure for multiple labs - just swap out students**

---

## Overview

Instead of deploying fresh each time, you can:

- ✅ **Keep AppRunner running** (stays warm, ready to go)
- ✅ **Keep DynamoDB running** (preserves any data you want)
- ✅ **Keep Cognito User Pool** (already configured)
- ✅ **Just swap out students** (delete old accounts, create new ones)

**Cost Savings:**
- Full deployment: $25-40 per lab
- Redeploying: $0-5 per lab (just new student data)
- Infrastructure stays running: $0.26/hour (AppRunner idle)

---

## Quick Reset Procedure (3 minutes)

### Step 1: Delete Old Student Accounts

```bash
# List all users in the Cognito User Pool
aws cognito-idp list-users \
  --user-pool-id us-east-1_tOHJ64R7F \
  --region us-east-1 \
  --query 'Users[*].Username' \
  --output text
```

**Option A: Delete all users at once**

```bash
# Get all usernames and delete them
aws cognito-idp list-users \
  --user-pool-id us-east-1_tOHJ64R7F \
  --region us-east-1 \
  --query 'Users[*].Username' \
  --output text | tr '\t' '\n' | while read username; do
    echo "Deleting: $username"
    aws cognito-idp admin-delete-user \
      --user-pool-id us-east-1_tOHJ64R7F \
      --username "$username" \
      --region us-east-1
  done

echo "✅ All users deleted"
```

**Option B: Delete specific users**

```bash
# Delete one user at a time
aws cognito-idp admin-delete-user \
  --user-pool-id us-east-1_tOHJ64R7F \
  --username alice@example.com \
  --region us-east-1
```

### Step 2: Optional - Clear Student Credential Data

```bash
# If you want to clear stored API credentials from the previous lab
aws dynamodb scan \
  --table-name AIAssuranceLab-UserMCPCredentials \
  --region us-east-1 \
  --query 'Items[*].email.S' \
  --output text | tr '\t' '\n' | while read email; do
    echo "Deleting credentials for: $email"
    aws dynamodb delete-item \
      --table-name AIAssuranceLab-UserMCPCredentials \
      --key "{\"email\": {\"S\": \"$email\"}}" \
      --region us-east-1
  done

echo "✅ All credential data cleared"
```

### Step 3: Create New Student Accounts

```bash
# Create your new students.csv
cat > students.csv << 'CSV'
email,first_name,last_name
alice@example.com,Alice,Smith
bob@example.com,Bob,Jones
... (repeat for all students)
CSV

# Create accounts
bash CREATE_STUDENTS_ONLY.sh students.csv

echo "✅ All new students created and ready to log in"
```

---

## Complete Workflow (Your Options)

### Option A: Full Reuse (Recommended for Frequent Labs)

**Best when:** Running multiple labs with different cohorts

```bash
# First lab
bash AWS_DEPLOY.sh                              # 10 min
bash CREATE_STUDENTS_ONLY.sh cohort1.csv       # 2 min
# Run lab
# Lab ends

# Second lab (3 minutes later)
bash RESET_USERS.sh cohort2.csv                # 3 min
# Run lab
# Lab ends

# Third lab (3 minutes later)
bash RESET_USERS.sh cohort3.csv                # 3 min
# Run lab
```

**Total cost:** $25-40 (one deployment) + $0.26/hour idle time between labs

### Option B: Full Cleanup (For Long Breaks)

**Best when:** Taking a long break between labs

```bash
# After your last lab, delete AppRunner to save money
aws apprunner delete-service \
  --service-arn arn:aws:apprunner:us-east-1:004878717866:service/ai-assurance-lab/... \
  --region us-east-1

# DynamoDB and Cognito stay (low cost)
# When you're ready for next lab: bash AWS_DEPLOY.sh again (10 min)
```

**Total cost:** $25-40 per deployment (AppRunner deleted when not in use)

---

## Automated Reset Script

Create a file called `RESET_USERS.sh`:

```bash
#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: bash RESET_USERS.sh students.csv"
  exit 1
fi

CSV_FILE="$1"
USER_POOL_ID="us-east-1_tOHJ64R7F"
REGION="us-east-1"

echo "════════════════════════════════════════════════════════════"
echo "🔄 RESETTING USERS FOR NEW LAB"
echo "════════════════════════════════════════════════════════════"
echo ""

# Step 1: Delete old users
echo "Step 1: Deleting old student accounts..."
aws cognito-idp list-users \
  --user-pool-id $USER_POOL_ID \
  --region $REGION \
  --query 'Users[*].Username' \
  --output text | tr '\t' '\n' | while read username; do
  if [ ! -z "$username" ]; then
    aws cognito-idp admin-delete-user \
      --user-pool-id $USER_POOL_ID \
      --username "$username" \
      --region $REGION 2>/dev/null
    echo "  ✅ Deleted: $username"
  fi
done

echo "✅ Old users deleted"

# Step 2: Clear credential data
echo ""
echo "Step 2: Clearing credential data from DynamoDB..."
aws dynamodb scan \
  --table-name AIAssuranceLab-UserMCPCredentials \
  --region $REGION \
  --query 'Items[*].email.S' \
  --output text | tr '\t' '\n' | while read email; do
  if [ ! -z "$email" ]; then
    aws dynamodb delete-item \
      --table-name AIAssuranceLab-UserMCPCredentials \
      --key "{\"email\": {\"S\": \"$email\"}}" \
      --region $REGION 2>/dev/null
    echo "  ✅ Cleared: $email"
  fi
done

echo "✅ Credential data cleared"

# Step 3: Create new users
echo ""
echo "Step 3: Creating new student accounts..."
bash CREATE_STUDENTS_ONLY.sh "$CSV_FILE"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ RESET COMPLETE!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Lab is ready for new cohort!"
echo "Lab URL: https://xxxxx.us-east-1.apprunner.amazonaws.com"
echo ""
```

**Use it:**
```bash
bash RESET_USERS.sh new_students.csv
```

---

## Advantages of Full Reuse

### Time Savings
- ✅ Full deployment: 20 minutes
- ✅ User reset: 3 minutes
- ✅ Save: 17 minutes per lab!

### Cost Savings
- ✅ Full deployment: $25-40 per lab
- ✅ User reset: $0-5 per lab (just DynamoDB scan/delete)
- ✅ Idle time: $0.26/hour (AppRunner sleeping)
- ✅ Save: $20-35 per lab!

### Convenience
- ✅ AppRunner already warmed up
- ✅ No waiting for initial deployment
- ✅ Just swap students and go
- ✅ Perfect for back-to-back labs

---

## Monitoring Between Labs

### Check AppRunner is Still Running

```bash
aws apprunner list-services \
  --region us-east-1 \
  --query "ServiceSummaryList[?ServiceName=='ai-assurance-lab'].Status" \
  --output text
# Should show: RUNNING
```

### Verify Service URL Still Works

```bash
# Get your Lab URL
aws apprunner list-services \
  --region us-east-1 \
  --query "ServiceSummaryList[?ServiceName=='ai-assurance-lab'].ServiceUrl" \
  --output text

# Visit it in browser to verify it loads
```

### Check Cognito User Pool

```bash
aws cognito-idp describe-user-pool \
  --user-pool-id us-east-1_tOHJ64R7F \
  --region us-east-1 \
  --query 'UserPool.Status' \
  --output text
# Should show: ACTIVE
```

---

## Detailed Reset Procedure (Manual Steps)

If you want to do it step-by-step without the script:

### Step 1: List Current Users

```bash
aws cognito-idp list-users \
  --user-pool-id us-east-1_tOHJ64R7F \
  --region us-east-1
```

**Output:**
```json
{
  "Users": [
    {
      "Username": "alice@example.com",
      "Attributes": [...],
      ...
    },
    ...
  ]
}
```

### Step 2: Delete Each User

```bash
# Delete one user
aws cognito-idp admin-delete-user \
  --user-pool-id us-east-1_tOHJ64R7F \
  --username alice@example.com \
  --region us-east-1

echo "✅ Deleted: alice@example.com"
```

Repeat for each user.

### Step 3: Clear Credentials (Optional)

```bash
# Delete one student's credentials
aws dynamodb delete-item \
  --table-name AIAssuranceLab-UserMCPCredentials \
  --key '{"email": {"S": "alice@example.com"}}' \
  --region us-east-1

echo "✅ Cleared credentials for: alice@example.com"
```

Repeat for each student.

### Step 4: Create New Users

```bash
# Prepare new students.csv
cat > students.csv << 'CSV'
email,first_name,last_name
new.alice@example.com,Alice,Smith
new.bob@example.com,Bob,Jones
... etc ...
CSV

# Create all accounts
bash CREATE_STUDENTS_ONLY.sh students.csv
```

---

## Cost Comparison

### Scenario: Run Lab Every Week for 4 Weeks

**Option A: Full Reuse (Recommended)**
- Week 1: Deploy ($25-40) + students ($0)
- Week 2: Reset users ($0-5) 
- Week 3: Reset users ($0-5)
- Week 4: Reset users ($0-5)
- Idle time: 3 weeks × $0.26/hr × 168 hrs = $131
- **Total: ~$165**

**Option B: Full Deployment Each Time**
- Week 1: Deploy ($25-40)
- Week 2: Deploy ($25-40)
- Week 3: Deploy ($25-40)
- Week 4: Deploy ($25-40)
- **Total: ~$100-160** (similar, but more manual work)

**Option C: Delete & Redeploy**
- Week 1: Deploy ($25-40) + delete
- Week 2: Deploy ($25-40)
- Week 3: Deploy ($25-40)
- Week 4: Deploy ($25-40)
- **Total: ~$100-160**

**Winner:** Option A (full reuse) - cheapest + fastest!

---

## FAQ

### "Can I reset users without redeploying?"
**YES!** That's exactly what this guide covers. Just delete old accounts and create new ones.

### "Do I need to restart AppRunner?"
**NO.** AppRunner keeps running. It doesn't know or care about users.

### "What if I delete users by mistake?"
**No problem.** Just create new accounts with `bash CREATE_STUDENTS_ONLY.sh students.csv`

### "How long does a full reset take?"
**~3 minutes total:**
- Delete old users: 1-2 minutes
- Clear credentials: 30 seconds
- Create new users: 1-2 minutes

### "Can I reset just specific users?"
**YES.** Delete specific users with their individual commands, then create new ones.

### "What about student data?"
**Your choice:**
- Keep it: Don't clear DynamoDB
- Delete it: Use the clear-credentials step

### "How many times can I reuse the lab?"
**Unlimited!** AppRunner will keep running. Just keep resetting users.

---

## Recommended Workflow

### For Frequent Labs (Same Week)
1. Deploy once: `bash AWS_DEPLOY.sh` (10 min)
2. Run Lab 1 with cohort1.csv
3. Reset: `bash RESET_USERS.sh cohort2.csv` (3 min)
4. Run Lab 2
5. Reset: `bash RESET_USERS.sh cohort3.csv` (3 min)
6. Run Lab 3
7. Cost: ~$25-40 total + idle time (~$13 for 3 days idle)

### For Labs Spaced Out (Different Weeks)
1. Deploy: `bash AWS_DEPLOY.sh` (10 min)
2. Run Lab 1
3. Keep running for a week (or delete to save money)
4. Reset: `bash RESET_USERS.sh cohort2.csv` (3 min)
5. Run Lab 2
6. Cost: ~$25-40 per week

---

## When to Deploy Fresh vs. Reset

### Deploy Fresh When:
- ✅ First lab ever
- ✅ Taking 2+ week break
- ✅ Want guaranteed fresh state
- ✅ Infrastructure might have issues

### Reset Users When:
- ✅ Running back-to-back labs
- ✅ Same week, different cohorts
- ✅ Want to save time
- ✅ Want to save money
- ✅ AppRunner is already running fine

---

## Summary

**Keep AppRunner running, reset users between labs:**

```bash
# First lab
bash AWS_DEPLOY.sh                    # 10 min

# Second lab (run later)
bash RESET_USERS.sh new_students.csv  # 3 min

# Third lab (run later)
bash RESET_USERS.sh new_students.csv  # 3 min
```

**Benefits:**
- ✅ 17 minutes faster per lab (20 → 3 min)
- ✅ $20-35 cheaper per lab
- ✅ Infrastructure already warmed up
- ✅ Perfect for multi-cohort training

**That's it!** Your lab infrastructure is reusable!

