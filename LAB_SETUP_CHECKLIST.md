# AI Assurance Lab - Setup Checklist for Proctor

**Total Setup Time: ~2-3 hours**  
**Lab Duration: Flexible (2-4 hours recommended)**  
**Students: 40**

---

## Section 1: Pre-Lab Setup (Start 1-2 days before lab)

### AWS Account & Services
- [ ] AWS Account access confirmed (004878717866)
- [ ] AWS CLI configured: `aws configure`
- [ ] Bedrock enabled in us-east-1
  - [ ] Claude 3.5 Sonnet model available
  - [ ] Test: `aws bedrock list-foundation-models --region us-east-1`
- [ ] DynamoDB table created: `AIAssuranceLab-UserMCPCredentials`
  - [ ] Status: ACTIVE
  - [ ] Encryption enabled
  - [ ] Test: `aws dynamodb describe-table --table-name AIAssuranceLab-UserMCPCredentials`

### Docker & Deployment (Start 1 day before lab)
- [ ] Docker Desktop installed and running (or CodeBuild alternative planned)
- [ ] ECR repository created: `ai-assurance-lab`
  - [ ] URI: `004878717866.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab`
- [ ] Docker image built and pushed to ECR
  - [ ] Command: See PROCTOR_DEPLOYMENT_GUIDE.md Part 2
  - [ ] Verify: `aws ecr describe-images --repository-name ai-assurance-lab`

### Cognito Setup (Start 1 day before lab)
- [ ] Cognito User Pool created: `AI-Assurance-Lab`
  - [ ] User Pool ID: _______________ (save this)
  - [ ] Sign-in method: Email
  - [ ] Password policy: 8+ characters
- [ ] App Client created
  - [ ] Client ID: _______________ (save this)
  - [ ] Client Secret: _______________ (save this - keep secure!)
  - [ ] Auth flows: USER_PASSWORD_AUTH, REFRESH_TOKEN_AUTH enabled
- [ ] Cognito Domain created
  - [ ] Domain: _______________ (e.g., `ai-assurance-lab-RANDOM`)
  - [ ] Format: `ai-assurance-lab-RANDOM.auth.us-east-1.amazoncognito.com`

### AppRunner Deployment (Start 1 day before lab)
- [ ] AppRunner service created: `ai-assurance-lab`
  - [ ] Source: ECR image from above
  - [ ] Port: 8080
  - [ ] Service Status: RUNNING (green)
  - [ ] AppRunner URL: _______________ (save this)
- [ ] Environment variables configured in AppRunner
  - [ ] COGNITO_DOMAIN set
  - [ ] COGNITO_CLIENT_ID set
  - [ ] COGNITO_CLIENT_SECRET set
  - [ ] ENCRYPTION_KEY set
  - [ ] All other variables set (see guide)
- [ ] IAM role created with permissions
  - [ ] DynamoDB access: Read/Write to table
  - [ ] Bedrock access: InvokeModel for Claude
  - [ ] CloudWatch Logs: Write logs

### Cognito Callback URLs (After AppRunner deployment)
- [ ] App Client updated with callback URL
  - [ ] Callback URL: `https://<YOUR-APPRUNNER-URL>/auth/callback`
  - [ ] Sign-out URL: `https://<YOUR-APPRUNNER-URL>/logout`
  - [ ] Allowed OAuth flows: ALLOW_CODE verified

---

## Section 2: Test Deployment (3-6 hours before lab)

### Service Availability
- [ ] AppRunner service is RUNNING
  - [ ] Test: Visit `https://<YOUR-APPRUNNER-URL>` in browser
  - [ ] Should redirect to Cognito login
- [ ] Cognito User Pool is ACTIVE
  - [ ] Test: Try signing up for test account
  - [ ] Email verification works
- [ ] DynamoDB table is accessible
  - [ ] Test: `aws dynamodb scan --table-name AIAssuranceLab-UserMCPCredentials --limit 1`

### Create Test Account
- [ ] Create Cognito test user
  - [ ] Email: `test.proctor@example.com`
  - [ ] Temporary password: Auto-generated
  - [ ] Send invitation: Yes
- [ ] Set permanent password
  - [ ] Receive email invitation
  - [ ] Click link and set new password
  - [ ] Password: Store securely

### Test Full Workflow
- [ ] Log in with test account
  - [ ] URL: `https://<YOUR-APPRUNNER-URL>`
  - [ ] Enter credentials
  - [ ] Redirected to chat interface
- [ ] Test credential management
  - [ ] Click "⚙️ Credentials"
  - [ ] See status page (both services disconnected)
  - [ ] Add test ThousandEyes token (can be placeholder)
  - [ ] Click "Test Connection"
  - [ ] See response (may fail if invalid token, but UI should work)
  - [ ] See status update
  - [ ] Delete token successfully
- [ ] Test chat interface
  - [ ] Go back to chat
  - [ ] Send test message: "Hello, who are you?"
  - [ ] Receive Claude response
  - [ ] See message history preserved
- [ ] Monitor AppRunner logs
  - [ ] CloudWatch Logs show no critical errors
  - [ ] Response times < 5 seconds
  - [ ] No memory leaks or crashes

### Verify Security
- [ ] Tokens are not logged (check CloudWatch logs)
  - [ ] Search logs for "token" - should find none
- [ ] Session cookies are HttpOnly
  - [ ] Browser dev tools: Cookies don't show in JavaScript
- [ ] No plaintext secrets in code or logs
  - [ ] Encryption is working correctly

---

## Section 3: Student Account Creation (2-4 hours before lab)

### Prepare Student List
- [ ] Have list of 40 student emails
  - [ ] Format: `firstname.lastname@domain.com`
  - [ ] No duplicates
  - [ ] Valid email addresses

### Create Students in Cognito (Choose one method)

**Method A: Manual Creation (Best for <10 students)**
- [ ] For each student:
  - [ ] Go to Cognito User Pool → Users
  - [ ] Click "Create user"
  - [ ] Email: student@example.com
  - [ ] Auto-generate password: Yes
  - [ ] Mark email verified: Yes
  - [ ] Send invitation: Yes
  - [ ] Repeat for all 40 students

**Method B: Batch Creation via AWS CLI (Best for 40+ students)**
- [ ] Create Python script or use AWS CLI batch
  - [ ] Script location: `create_students.py`
  - [ ] User Pool ID: `us-east-1_XXXXXXXXX`
  - [ ] Read student emails from CSV
  - [ ] Create each user with temporary password
- [ ] Run script: `python3 create_students.py`
  - [ ] Check output for errors
  - [ ] All 40 users created
  - [ ] Temporary passwords generated

**Method C: AWS Cognito Console Bulk Import**
- [ ] Create CSV file: `students.csv`
  - [ ] Columns: email, given_name, family_name
  - [ ] 40 rows (one per student)
- [ ] In Cognito console → User management → Create users
  - [ ] Select "Bulk import"
  - [ ] Upload CSV
  - [ ] Verify results

### Confirm Student Accounts Created
- [ ] Count users in Cognito User Pool
  - [ ] Should be exactly 40 (plus your test account)
  - [ ] All have verified emails
  - [ ] All have auto-generated temporary passwords

### Send Login Instructions
- [ ] Prepare email template:
  ```
  Subject: AI Assurance Lab Login Information
  
  Welcome to the AI Assurance Lab!
  
  Lab URL: https://<YOUR-APPRUNNER-URL>
  
  Your credentials:
  Email: [student@example.com]
  Temporary Password: [sent separately]
  
  First Login:
  1. Visit the URL above
  2. Enter your email and temporary password
  3. You'll be prompted to set a new permanent password
  4. After login, configure your API credentials in Settings
  
  Lab Guide: [Attached or linked]
  
  Questions? Contact proctor during lab.
  ```
- [ ] Send to all 40 students
  - [ ] Include lab guide (AI-Assurance_Lab-Guide.html)
  - [ ] Mention they'll receive temporary password separately
  - [ ] Provide proctor contact (email/Slack)

---

## Section 4: Day-Before Verification (Evening before lab)

### Verify All Services Still Running
- [ ] AppRunner service RUNNING
  - [ ] CloudWatch shows no errors in last hour
  - [ ] Response time normal
- [ ] Cognito User Pool ACTIVE
  - [ ] 40 students + test account visible
- [ ] DynamoDB table has 0 items
  - [ ] Will populate as students add credentials during lab

### Final Security Check
- [ ] .env file NOT in Git repo (check .gitignore)
- [ ] No hardcoded secrets in code
- [ ] Encryption module tested and working
- [ ] Test account can't access other accounts' data

### Backup Important Information
- [ ] Save to secure location:
  - [ ] Cognito User Pool ID
  - [ ] Cognito Client ID
  - [ ] Cognito Client Secret
  - [ ] AppRunner URL
  - [ ] DynamoDB table name
  - [ ] AWS Account ID
- [ ] Write down proctor contact info for students

---

## Section 5: 60 Minutes Before Lab

### Verify Everything One Last Time
- [ ] Test login: `https://<YOUR-APPRUNNER-URL>`
  - [ ] Use test account
  - [ ] Get to chat interface
- [ ] Test credentials page
  - [ ] See credential status
  - [ ] UI responsive
- [ ] Test chat
  - [ ] Send message: "Test message"
  - [ ] Receive response
  - [ ] Message appears in history
- [ ] Check AppRunner dashboard
  - [ ] Service status: RUNNING (green)
  - [ ] Recent requests show no errors
  - [ ] CPU/Memory usage normal

### Prepare Lab Room
- [ ] Network/WiFi verified
  - [ ] All 40 students can connect
  - [ ] Bandwidth sufficient (~1 Mbps per student)
- [ ] Screen/projector ready for demonstrations
- [ ] Backup internet (mobile hotspot) available
- [ ] Slack/email ready for student support

### Have Support Materials Ready
- [ ] Print or have digital:
  - [ ] Lab guide (HTML or PDF)
  - [ ] Quick reference card (QUICK_REFERENCE.txt)
  - [ ] Login instructions
  - [ ] FAQ (common issues & fixes)
- [ ] Have password reset procedure ready
  - [ ] How to reset student password in Cognito
  - [ ] How to re-send email verification

---

## Section 6: 30 Minutes Before Lab - Student Check-In

### Monitor Student Access
- [ ] Monitor CloudWatch logs for login attempts
  - [ ] Watch for authentication errors
  - [ ] Should see ~40 successful logins
- [ ] Ask first 5 students: "Can you log in?"
  - [ ] Respond quickly to issues
  - [ ] Adjust if needed

### Troubleshoot Early Issues
- [ ] If students can't log in:
  - [ ] Check: Did they receive invitation email?
  - [ ] Check: Did they set password?
  - [ ] Check: Is password correct?
  - [ ] Check: Cognito User Pool active?
- [ ] If students see blank page:
  - [ ] Check: AppRunner service running?
  - [ ] Check: Browser cache (clear it)
  - [ ] Check: Try different browser
- [ ] If chat is slow:
  - [ ] Check: Network connectivity
  - [ ] Check: AppRunner response time (CloudWatch)
  - [ ] Check: Bedrock availability

### Get Confirmation from Students
- [ ] Have at least 20 students confirm they're logged in
  - [ ] Can see chat interface
  - [ ] Can see credentials page
  - [ ] No major issues

---

## Section 7: Lab Time - Proctor Duties

### Every 10 Minutes
- [ ] Check CloudWatch logs for errors
  - [ ] Look for 5xx errors
  - [ ] Note any patterns
- [ ] Ask students if they're having issues
  - [ ] "Everyone good? Any questions?"

### Every 30 Minutes
- [ ] Check AppRunner metrics
  - [ ] CPU usage reasonable (<70%)
  - [ ] Memory usage reasonable (<70%)
  - [ ] Response time normal (<3 seconds)
- [ ] Check DynamoDB
  - [ ] Credentials being saved (scan table)
  - [ ] No errors in CloudWatch logs

### Respond to Issues Immediately
| Issue | Resolution |
|-------|-----------|
| Can't log in | Check Cognito User Pool, reset password if needed |
| Chat not responding | Check Bedrock availability, restart AppRunner if needed |
| Credentials won't save | Check DynamoDB table, verify encryption key |
| Slow responses | Check AppRunner CPU/memory, scale if needed |
| Student lost session | Have them log out, clear cache, log back in |

### Support Availability
- [ ] Be available throughout lab
  - [ ] Respond to questions in < 2 minutes
  - [ ] Have technical backup contact (AWS Support)
  - [ ] Have emergency procedures documented

---

## Section 8: End of Lab - Shutdown & Cleanup

### Capture Lab Data (Optional)
- [ ] Export student interactions
  - [ ] Query DynamoDB for credential usage
  - [ ] Check CloudWatch logs for patterns
  - [ ] Note any interesting findings
- [ ] Collect student feedback
  - [ ] Quick survey: What worked? What didn't?
  - [ ] Technical issues encountered?
  - [ ] Feature requests?

### Graceful Shutdown
- [ ] Announce lab is ending
- [ ] Give students time to disconnect
- [ ] No immediate service termination

### Optional: Keep Services Running
- [ ] AppRunner remains active (low cost)
- [ ] DynamoDB remains active (pay-per-request)
- [ ] Students can access lab afterwards

### Optional: Shutdown Everything
- [ ] Delete AppRunner service
- [ ] Delete Cognito User Pool (careful - no undo)
- [ ] Delete DynamoDB table (careful - no undo)
- [ ] Delete ECR repository

---

## Section 9: Post-Lab Analysis

### Review Logs
- [ ] Total requests processed
- [ ] Error rate
- [ ] Average response time
- [ ] Peak load handling
- [ ] Notable issues and resolutions

### Student Feedback
- [ ] Collect responses
- [ ] Identify pain points
- [ ] Note feature requests
- [ ] Plan improvements for next lab

### Cost Analysis
- [ ] AppRunner cost (usually $1-5 per hour)
- [ ] DynamoDB cost (pay-per-request, usually $1-3 per 100k requests)
- [ ] Bedrock cost (per invocation, usually $0.01-0.10 per request)
- [ ] Total estimated cost: _______

---

## Critical Contacts & Resources

### AWS Support
- [ ] AWS Support Plan active (if available)
- [ ] Support email: ____________________
- [ ] Support phone: ____________________

### Lab Administrator
- [ ] Name: ____________________
- [ ] Email: ____________________
- [ ] Phone: ____________________
- [ ] Slack: ____________________

### Technical Resources
- [ ] CloudWatch Logs: https://console.aws.amazon.com/logs/
- [ ] AppRunner Dashboard: https://console.aws.amazon.com/apprunner/
- [ ] Cognito Dashboard: https://console.aws.amazon.com/cognito/
- [ ] DynamoDB Console: https://console.aws.amazon.com/dynamodb/
- [ ] Bedrock Console: https://console.aws.amazon.com/bedrock/

### Documentation
- [ ] PROCTOR_DEPLOYMENT_GUIDE.md (this directory)
- [ ] README.md (application documentation)
- [ ] LAB_SETUP_CHECKLIST.md (this file)
- [ ] AI-Assurance_Lab-Guide.html (student guide)

---

## Success Metrics

Lab is considered successful if:

- ✅ **Accessibility**: All 40 students can log in (100% success rate)
- ✅ **Stability**: AppRunner uptime > 99.5% (max 1-2 min downtime)
- ✅ **Performance**: Chat response time < 5 seconds (average < 2 sec)
- ✅ **Security**: Zero credential leakage between students
- ✅ **Functionality**: All 40 students can add credentials and chat
- ✅ **Support**: All student issues resolved within 5 minutes
- ✅ **Satisfaction**: Positive feedback from majority of students (>80%)

---

## Emergency Procedures

### AppRunner Service Down
1. Check AppRunner console for status
2. Check CloudWatch logs for errors
3. If hung: Restart service (AWS Console)
4. If still failing: Redeploy from ECR
5. Notify students of estimated restoration time

### Cognito Issues
1. Check User Pool status
2. Verify User Pool not accidentally deleted
3. Check IAM permissions
4. If major issue: Have backup test account ready

### DynamoDB Issues
1. Check table exists and is ACTIVE
2. Check CloudWatch logs for throttling
3. If throttled: Table has auto-scaling (may take 5 min)
4. If failed: Contact AWS Support

### Complete Service Failure
1. Announce to students: "We're experiencing technical issues. Stand by."
2. Check all services (AppRunner, Cognito, DynamoDB)
3. Review CloudWatch logs for root cause
4. Attempt recovery based on root cause
5. If unrecoverable: Postpone lab and contact AWS Support

---

## Final Checklist (Day-of Lab Start)

```
⏱️  60 Minutes Before:
  [ ] AppRunner service RUNNING
  [ ] Test login successful
  [ ] CloudWatch logs show no errors
  [ ] Test credentials workflow
  [ ] Test chat interaction
  [ ] All 40 students created in Cognito
  [ ] Lab room setup complete
  [ ] WiFi/network verified
  [ ] Support materials printed/ready

⏱️  30 Minutes Before:
  [ ] Monitor first 5 student logins
  [ ] Troubleshoot any early issues
  [ ] Announce lab starting soon
  [ ] Have password reset ready
  [ ] Take screenshot of working app (for proof)

⏱️  Lab Start:
  [ ] Welcome students
  [ ] Explain lab objectives
  [ ] Provide credentials (username)
  [ ] Direct to lab URL
  [ ] Monitor logins closely
  [ ] Be ready to support

⏱️  During Lab:
  [ ] Monitor AppRunner every 10 minutes
  [ ] Check CloudWatch logs every 30 minutes
  [ ] Respond to issues within 2 minutes
  [ ] Track student progress informally

⏱️  Lab End:
  [ ] Announce session closing
  [ ] Capture any final data needed
  [ ] Conduct quick survey (optional)
  [ ] Thank students
  [ ] Shut down if planned (or leave running)
```

---

**Ready to run the lab!** 🚀

Print this checklist and check off items as you go. You're well-prepared for a successful AI Assurance Lab session with 40 students.

