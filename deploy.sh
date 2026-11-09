#!/bin/bash
# AI Assurance Lab - Deploy to all running instances
#
# Context (2026-11-09): the app moved from a single named EC2 instance to an
# Auto Scaling Group (ai-assurance-lab-asg, 1-3x m6i.large behind an ALB,
# scaling on CPU). A deploy now has to reach every instance currently in the
# group, not one hardcoded instance ID - the ASG's membership changes on its
# own as it scales, so this script always discovers the current instance
# list fresh from AWS rather than assuming who's running.
#
# What it does, per instance, via SSM (no SSH key needed):
#   1. git pull (as the app's own deploy user, with the known safe.directory
#      / $HOME workaround needed for SSM's default shell context)
#   2. py_compile app.py as a lint/sanity gate - if this fails, that
#      instance's restart is skipped and the script reports it as failed,
#      rather than restarting into a broken app
#   3. restart flask-app.service
#   4. confirm the service is active afterward
#
# Usage: ./deploy.sh
# Requires: AWS CLI configured with access to this account/region.

set -uo pipefail

REGION="us-east-1"
ASG_NAME="ai-assurance-lab-asg"
APP_DIR="/home/ubuntu/ai-assurance-lab"

echo "🚀 AI Assurance Lab - Fleet Deploy"
echo "===================================="

echo ""
echo "🔎 Discovering current ASG instances ($ASG_NAME)..."
INSTANCE_IDS=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names "$ASG_NAME" --region "$REGION" \
  --query "AutoScalingGroups[0].Instances[?LifecycleState=='InService'].InstanceId" \
  --output text | tr '\t\n' '  ' | xargs)

if [ -z "$INSTANCE_IDS" ]; then
  echo "❌ No InService instances found in $ASG_NAME. Aborting."
  exit 1
fi

INSTANCE_COUNT=$(echo "$INSTANCE_IDS" | wc -w | tr -d ' ')
echo "✅ Found $INSTANCE_COUNT instance(s): $INSTANCE_IDS"

# A freshly-launched ASG instance can be "InService" at the ASG level before
# its SSM agent has finished checking in - sending a command too early fails
# with "Instances not in a valid state for account". Wait for every target
# instance to show up as SSM-Online before sending anything (discovered by
# actually testing this script against a 2nd scaled-out instance).
echo ""
echo "⏳ Waiting for all instances to be SSM-Online..."
for attempt in $(seq 1 20); do
  FILTER_VALUES=$(echo "$INSTANCE_IDS" | tr -s ' ' ',')
  ONLINE_IDS=$(aws ssm describe-instance-information --region "$REGION" \
    --filters "Key=InstanceIds,Values=$FILTER_VALUES" \
    --query "InstanceInformationList[?PingStatus=='Online'].InstanceId" --output text)
  ONLINE_COUNT=$(echo "$ONLINE_IDS" | tr '\t' ' ' | wc -w | tr -d ' ')
  if [ "$ONLINE_COUNT" = "$INSTANCE_COUNT" ]; then
    echo "   ✅ All $INSTANCE_COUNT instance(s) are SSM-Online."
    break
  fi
  echo "   ...$ONLINE_COUNT/$INSTANCE_COUNT online, waiting (attempt $attempt/20)"
  sleep 10
done

DEPLOY_CMD="export HOME=/root; cd $APP_DIR && git -c safe.directory=$APP_DIR pull && venv/bin/python3 -m py_compile app.py && systemctl restart flask-app.service && sleep 3 && systemctl is-active flask-app.service"

# Build the --instance-ids argument as a JSON array for send-command
INSTANCE_IDS_JSON=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1].split()))" "$INSTANCE_IDS")

echo ""
echo "📦 Sending deploy command to all instances..."
CMD_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE_IDS_JSON" \
  --document-name "AWS-RunShellScript" \
  --region "$REGION" \
  --parameters "{\"commands\":[\"$DEPLOY_CMD\"]}" \
  --query "Command.CommandId" --output text)

if [ -z "$CMD_ID" ] || [ "$CMD_ID" = "None" ]; then
  echo "❌ send-command failed to return a Command ID - aborting (see error above)."
  exit 1
fi

echo "   Command ID: $CMD_ID"
echo "⏳ Waiting for deploy to finish on all instances..."
sleep 15

FAILED=0
for IID in $INSTANCE_IDS; do
  for attempt in 1 2 3 4 5 6; do
    STATUS=$(aws ssm get-command-invocation --command-id "$CMD_ID" --instance-id "$IID" --region "$REGION" --query "Status" --output text 2>/dev/null || echo "Pending")
    if [ "$STATUS" != "InProgress" ] && [ "$STATUS" != "Pending" ]; then
      break
    fi
    sleep 5
  done

  OUT=$(aws ssm get-command-invocation --command-id "$CMD_ID" --instance-id "$IID" --region "$REGION" --query "StandardOutputContent" --output text 2>/dev/null)
  ERR=$(aws ssm get-command-invocation --command-id "$CMD_ID" --instance-id "$IID" --region "$REGION" --query "StandardErrorContent" --output text 2>/dev/null)

  if [ "$STATUS" == "Success" ] && echo "$OUT" | grep -q "^active$"; then
    echo "✅ $IID: deployed, flask-app.service active"
  else
    echo "❌ $IID: deploy FAILED (status=$STATUS)"
    echo "--- stdout ---"
    echo "$OUT"
    echo "--- stderr ---"
    echo "$ERR"
    FAILED=1
  fi
done

echo ""
if [ "$FAILED" -eq 0 ]; then
  echo "🎉 Deploy succeeded on all $INSTANCE_COUNT instance(s)."
  echo ""
  echo "🔍 Final health check against the live domain:"
  sleep 5
  CODE=$(curl -s -o /dev/null -w "%{http_code}" https://ai.thousandeyeschannel.com/)
  echo "   https://ai.thousandeyeschannel.com/ -> $CODE"
  if [ "$CODE" == "302" ]; then
    echo "✅ Looks healthy."
  else
    echo "⚠️  Unexpected status code - investigate before assuming this deploy is good."
  fi
else
  echo "⚠️  One or more instances failed to deploy. Investigate before assuming this deploy is good."
  exit 1
fi
