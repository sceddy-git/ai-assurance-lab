# 🚀 START HERE - EC2 Web-Managed Lab

## Your Lab is Ready! Here's How to Deploy It

The AI Assurance Lab is fully built and ready to run on EC2. Everything is managed through a web browser - **no terminal commands after initial setup**.

---

## What You'll Do (In Order)

### 1️⃣ **Launch EC2 Instance** (5 minutes)
→ See: `EC2_SETUP_MINIMAL.md` (Part 1)

- Go to AWS Console
- Launch Ubuntu 22.04 instance (t3.small)
- Configure security group (HTTP/HTTPS/SSH)
- Launch
- Copy public IP address

### 2️⃣ **SSH & Run Setup** (5 minutes)
→ See: `EC2_SETUP_MINIMAL.md` (Part 2-3)

```bash
ssh -i your-key.pem ubuntu@YOUR_IP
curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/ai-assurance-lab/main/ec2-setup.sh | bash
exit
```

That's it! Script does everything.

### 3️⃣ **Configure via Web Portal** (5 minutes)
→ See: `EC2_SETUP_MINIMAL.md` (Part 4)

1. Open: `http://YOUR_IP` in browser
2. Log in with Cognito account
3. Click **Settings** link
4. Fill in Cognito details
5. Add encryption key
6. Add proctor emails
7. Save
8. Done! ✅

### 4️⃣ **Upload Students** (1 minute)
→ See: `STUDENT_MANAGEMENT_FEATURE.md`

1. Prepare CSV file:
   ```csv
   email,first_name,last_name
   alice@company.com,Alice,Smith
   bob@company.com,Bob,Jones
   ```
2. Click **Students** link in browser
3. Upload CSV
4. Done! ✅

### 5️⃣ **Share Lab URL**
Students log in and use the lab!

---

## That's It! 🎉

Your lab is now:
- ✅ Running 24/7
- ✅ Web-managed
- ✅ Cost-effective ($15/month)
- ✅ Fully automated
- ✅ Professional and ready to teach

---

## Total Time: ~20 Minutes

| Step | Time | What You Do |
|------|------|-----------|
| 1. Launch EC2 | 5 min | Click in AWS console |
| 2. SSH & Setup | 5 min | One SSH command + wait |
| 3. Configure | 5 min | Fill form in web portal |
| 4. Upload Students | 1 min | Drag CSV in web portal |
| **Total** | **~20 min** | **Lab is live!** |

---

## Management (All Via Browser!)

After setup, everything is in your browser:

### Daily Operations
- **Upload students**: Students tab
- **Check status**: Settings → System Status
- **View logs**: Settings → Logs
- **Restart app**: Settings → System Status → Restart
- **Deploy code**: Settings → Deployment → Pull Latest
- **Reset cohort**: Students → Delete All + Upload New

### Everything is **point-and-click** - No terminal needed!

---

## Files to Read

### Quick Setup (Read First)
- **`EC2_SETUP_MINIMAL.md`** ← Start with this!
  - Quick 15-minute guide
  - Step-by-step walkthrough
  - All you need to get started

### Complete Reference (For Later)
- **`EC2_FULL_DEPLOYMENT_GUIDE.md`**
  - Complete, detailed guide
  - Troubleshooting section
  - Advanced configuration
  - Security best practices
  - Read after initial setup

### Features & Usage
- **`STUDENT_MANAGEMENT_FEATURE.md`**
  - How student portal works
  - CSV format details
  - Error handling

- **`WEB_MANAGED_LAB_SUMMARY.md`**
  - Overview of what we built
  - Architecture diagram
  - Cost analysis

---

## What You Need

### Before Starting
- [ ] AWS account (with some credits or paid plan)
- [ ] GitHub account (optional - needed if deploying from repo)
- [ ] SSH key (download from AWS when creating key pair)
- [ ] Cognito user pool set up
- [ ] Student CSV file prepared

### Cognito Setup (If Not Done Yet)
If you haven't set up Cognito:
1. AWS Console → Cognito
2. Create User Pool
3. Create App Client
4. Note: Domain, Client ID, Client Secret
5. You'll enter these in the Settings tab

---

## Quick Checklist

### Before First Setup
- [ ] Read `EC2_SETUP_MINIMAL.md`
- [ ] Prepare student CSV file
- [ ] Get Cognito details ready
- [ ] Generate encryption key (instructions in portal)

### During Setup
- [ ] Launch EC2
- [ ] Save SSH key safely
- [ ] Note public IP address
- [ ] SSH and run setup script
- [ ] Open browser to lab URL
- [ ] Configure settings
- [ ] Upload students

### After Setup
- [ ] Test student login
- [ ] Check System Status (Settings tab)
- [ ] View logs to verify everything works
- [ ] Done! 🎉

---

## Need Help?

### Common Issues

**"Can't SSH to instance"**
→ Check security group allows port 22
→ Check you have .pem key file

**"Lab won't load in browser"**
→ Check EC2 is running
→ Check security group allows port 80
→ Check IP address is correct

**"Login fails"**
→ Check Cognito settings in Settings tab
→ Check client ID and secret are correct

**"Can't upload students"**
→ Check CSV format (email, first_name, last_name)
→ Check file is .csv (not .xlsx)

### Where to Check
1. **System Status** (Settings → System Status)
   - Shows if Flask is running
   - Shows CPU/memory
   
2. **Logs** (Settings → Logs)
   - Shows actual error messages
   - Most helpful for troubleshooting

3. **Documentation**
   - `EC2_FULL_DEPLOYMENT_GUIDE.md` has troubleshooting section

---

## Cost

### Monthly Estimate
- EC2 t3.small: ~$10
- DynamoDB: ~$2
- Total: ~$12/month

### Free Tier Eligible
If first year on AWS:
- EC2 t3.micro: FREE (or $3)
- DynamoDB: ~$2
- Total: ~$2-5/month

---

## What's Different From Before?

### Before (AppRunner / CodeBuild)
- ❌ Docker complications
- ❌ CodeBuild build failures
- ❌ AWS CLI required
- ❌ Complex deployment

### Now (EC2 + Web Portal)
- ✅ No Docker needed
- ✅ Simple one-command setup
- ✅ Fully web-based management
- ✅ Much cheaper

---

## You're All Set! 🚀

1. **Read**: `EC2_SETUP_MINIMAL.md`
2. **Follow**: The 4 steps (20 minutes)
3. **Manage**: Everything via web portal (forever!)

Your lab is ready to teach! Enjoy! 🎓

---

## Questions?

- **Stuck on setup?** → Read `EC2_FULL_DEPLOYMENT_GUIDE.md`
- **Features not working?** → Check `Settings → Logs`
- **Need to troubleshoot?** → See "Troubleshooting" in full guide
- **Want to scale up?** → Change instance type (1 click)

You've got this! 💪

**Next: Open `EC2_SETUP_MINIMAL.md` and follow Part 1 (Launch EC2)**
