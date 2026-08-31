#!/bin/bash

# AI Assurance Lab - Student Account Creation
# Usage: bash CREATE_STUDENTS_ONLY.sh students.csv

if [ -z "$1" ]; then
  echo "Usage: bash CREATE_STUDENTS_ONLY.sh <students.csv>"
  echo ""
  echo "CSV format (first row must be header):"
  echo "  email,first_name,last_name"
  echo "  alice@example.com,Alice,Smith"
  echo "  bob@example.com,Bob,Jones"
  exit 1
fi

CSV_FILE="$1"
REGION="us-east-1"
USER_POOL_ID="us-east-1_tOHJ64R7F"

if [ ! -f "$CSV_FILE" ]; then
  echo "❌ File not found: $CSV_FILE"
  exit 1
fi

echo "════════════════════════════════════════════════════════════"
echo "👥 CREATING STUDENT ACCOUNTS"
echo "════════════════════════════════════════════════════════════"
echo ""

# Count students
TOTAL=$(grep -c "," "$CSV_FILE" 2>/dev/null)
TOTAL=$((TOTAL - 1))  # Subtract header

if [ $TOTAL -le 0 ]; then
  echo "❌ No valid students found in CSV"
  exit 1
fi

echo "📊 Found $TOTAL students in $CSV_FILE"
echo ""

CREATED=0
FAILED=0
SKIP=0

# Read CSV and create users
while IFS=',' read -r email first_name last_name; do
  # Skip header row
  if [ "$email" = "email" ] || [ "$email" = "Email" ]; then
    continue
  fi
  
  # Skip empty lines
  if [ -z "$email" ]; then
    continue
  fi
  
  # Trim whitespace
  email=$(echo "$email" | xargs)
  first_name=$(echo "$first_name" | xargs)
  last_name=$(echo "$last_name" | xargs)
  
  # Use email prefix as first name if not provided
  if [ -z "$first_name" ]; then
    first_name=$(echo "$email" | cut -d@ -f1)
  fi
  
  ((CREATED++))
  
  # Create user
  aws cognito-idp admin-create-user \
    --user-pool-id $USER_POOL_ID \
    --username "$email" \
    --temporary-password "TempPass${CREATED}!@#" \
    --message-action SUPPRESS \
    --user-attributes \
      Name=email,Value="$email" \
      Name=email_verified,Value=true \
      Name=given_name,Value="$first_name" \
      Name=family_name,Value="$last_name" \
    --region $REGION > /dev/null 2>&1
  
  if [ $? -eq 0 ]; then
    echo "  [$(printf %3d $CREATED)/$TOTAL] ✅ $email"
  else
    echo "  [$(printf %3d $CREATED)/$TOTAL] ⚠️  $email (may already exist)"
    ((FAILED++))
  fi
done < "$CSV_FILE"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ Created: $((CREATED - FAILED))"
echo "⚠️  Failed/Existing: $FAILED"
echo "📊 Total: $TOTAL"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Next: Share the lab URL with students"
echo "They'll log in, set a password, and add their API credentials"
