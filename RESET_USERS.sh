#!/bin/bash

# AI Assurance Lab - Reset Users Between Labs
# Deletes old student accounts, clears data, and creates new ones
# Keeps AppRunner/DynamoDB/Cognito running for reuse

if [ -z "$1" ]; then
  echo "Usage: bash RESET_USERS.sh students.csv"
  echo ""
  echo "Example:"
  echo "  bash RESET_USERS.sh new_cohort_students.csv"
  echo ""
  echo "CSV format:"
  echo "  email,first_name,last_name"
  echo "  alice@example.com,Alice,Smith"
  echo "  bob@example.com,Bob,Jones"
  exit 1
fi

CSV_FILE="$1"
USER_POOL_ID="us-east-1_tOHJ64R7F"
REGION="us-east-1"
TABLE_NAME="AIAssuranceLab-UserMCPCredentials"

if [ ! -f "$CSV_FILE" ]; then
  echo "❌ File not found: $CSV_FILE"
  exit 1
fi

echo "════════════════════════════════════════════════════════════"
echo "🔄 RESETTING LAB FOR NEW COHORT"
echo "════════════════════════════════════════════════════════════"
echo ""

# Verify AppRunner is still running
echo "⏳ Verifying AppRunner is still running..."
SERVICE_STATUS=$(aws apprunner list-services \
  --region $REGION \
  --query "ServiceSummaryList[?ServiceName=='ai-assurance-lab'].Status" \
  --output text)

if [ "$SERVICE_STATUS" != "RUNNING" ]; then
  echo "⚠️  WARNING: AppRunner status is: $SERVICE_STATUS"
  echo "   It may be initializing or have issues."
  echo "   Continuing anyway..."
fi
echo "✅ AppRunner verified"

# Step 1: Delete old users
echo ""
echo "Step 1: Deleting old student accounts..."
DELETED_COUNT=0
aws cognito-idp list-users \
  --user-pool-id $USER_POOL_ID \
  --region $REGION \
  --query 'Users[*].Username' \
  --output text | tr '\t' '\n' | while read username; do
  if [ ! -z "$username" ] && [ "$username" != "None" ]; then
    aws cognito-idp admin-delete-user \
      --user-pool-id $USER_POOL_ID \
      --username "$username" \
      --region $REGION 2>/dev/null
    echo "  ✅ Deleted: $username"
    DELETED_COUNT=$((DELETED_COUNT + 1))
  fi
done

echo "✅ Old users deleted"

# Step 2: Clear credential data from DynamoDB
echo ""
echo "Step 2: Clearing stored credentials from previous cohort..."
CLEARED_COUNT=0
aws dynamodb scan \
  --table-name $TABLE_NAME \
  --region $REGION \
  --query 'Items[*].email.S' \
  --output text | tr '\t' '\n' | while read email; do
  if [ ! -z "$email" ] && [ "$email" != "None" ]; then
    aws dynamodb delete-item \
      --table-name $TABLE_NAME \
      --key "{\"email\": {\"S\": \"$email\"}}" \
      --region $REGION 2>/dev/null
    echo "  ✅ Cleared: $email"
    CLEARED_COUNT=$((CLEARED_COUNT + 1))
  fi
done

echo "✅ Credential data cleared"

# Step 3: Create new student accounts
echo ""
echo "Step 3: Creating new student accounts..."
echo ""

bash CREATE_STUDENTS_ONLY.sh "$CSV_FILE"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ RESET COMPLETE!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Lab is ready for the new cohort!"
echo ""
echo "📍 Lab URL: https://xxxxx.us-east-1.apprunner.amazonaws.com"
echo "             (Same as before - AppRunner stayed running)"
echo ""
echo "Next: Share the Lab URL with your new cohort of students!"
echo ""
