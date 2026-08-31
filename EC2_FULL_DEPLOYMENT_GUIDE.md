# EC2 Deployment Guide - Complete & Web-Managed

## Overview

This guide walks you through deploying the AI Assurance Lab on EC2 with a completely web-based management interface. After initial setup, you manage EVERYTHING through the browser.

---

## Quick Summary

1. **Launch EC2** (5 min in AWS console)
2. **SSH once** (5 min)
3. **Run setup script** (5 min)
4. **Configure via web portal** (5 min)
5. **Upload students via web** (1 min)
6. **Done! Lab is running** 🚀

**Total: ~20 minutes to a fully functional lab**

---

## Part 1: Launch EC2 Instance

### Step 1.1: Open AWS Console
- Go to **AWS Console** → **EC2** → **Instances**
- Click **"Launch Instances"**

### Step 1.2: Configure Instance

**Basic Settings:**
- **Name**: `ai-assurance-lab`
- **OS**: Ubuntu 22.04 LTS (free tier eligible)
- **Instance Type**: `t3.small` ($10-12/month) or `t3.micro` ($3-5/month, free tier)

**Network Settings:**
- ✅ Create new security group
- ✅ Allow SSH (22) - for initial setup
- ✅ Allow HTTP (80) - for web access
- ✅ Allow HTTPS (443) - for production

**Storage:**
- Size: 20 GB (sufficient)
- Type: gp3

**Key Pair:**
- Create or select existing key pair
- **Save it!** You need it to SSH in

### Step 1.3: Launch
- Click **"Launch Instance"**
- Wait for status → **"running"** (2-3 min)
- Copy the **Public IPv4 address** (e.g., `54.123.45.67`)

---

## Part 2: Initial SSH Setup

### Step 2.1: Open Terminal

**On Mac/Linux:**
```bash
# Change directory to where you saved your key
cd ~/Downloads

# Make key readable only by you
chmod 400 your-key.pem

# SSH into instance
ssh -i your-key.pem ubuntu@54.123.45.67
# Replace IP with your instance's public IP
```

**On Windows:**
- Use PuTTY or Windows Terminal (with WSL)
- Import your .pem key if using PuTTY

### Step 2.2: Verify SSH Connection
You should see:
```
ubuntu@ip-172-31-0-123:~$
```

If you see this, you're connected! ✅

---

## Part 3: Run Setup Script

### Step 3.1: Download and Run Setup

```bash
# Get the setup script from your repo
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/ai-assurance-lab/main/ec2-setup.sh | bash

# Replace YOUR_USERNAME with your GitHub username
```

This script will:
- ✅ Update system packages
- ✅ Install Python 3.11
- ✅ Install git
- ✅ Clone your repository
- ✅ Create Python virtual environment
- ✅ Install dependencies from requirements.txt
- ✅ Create `.env` file from template
- ✅ Configure Flask as systemd service
- ✅ Start Flask app automatically
- ✅ Takes ~5 minutes

### Step 3.2: Wait for Completion

You'll see:
```
================================
✅ Setup Complete!
================================

🌐 Access your lab at:
   http://54.123.45.67

📝 Next steps:
   1. Open the URL in your browser
   2. Log in with Cognito
   3. Click 'Settings' tab
   4. Configure Cognito details
   5. ...
```

### Step 3.3: Exit SSH

```bash
exit
```

**You don't need to SSH again!** Everything is web-managed from here.

---

## Part 4: Configure via Web Portal

### Step 4.1: Open in Browser

1. Get your EC2 public IP (from AWS console)
2. Open browser
3. Visit: `http://54.123.45.67` (use your IP)

You should see: **AI Assurance Lab Login**

### Step 4.2: Log In

- Use your Cognito account to log in
- If first time, Cognito may prompt you to set a password

### Step 4.3: Configure Settings

After login:

1. Click **Settings** link (top right)
2. Go to **Configuration** tab
3. Fill in:
   - **Cognito Domain**: `your-pool.auth.us-east-1.amazoncognito.com`
   - **Client ID**: From Cognito console
   - **Client Secret**: From Cognito console
   - **Proctor Emails**: Your email (to access students)
   - **Encryption Key**: Generate via python command shown in portal
4. Click **Save Configuration**
5. Flask will restart automatically

### Step 4.4: Verify Configuration

After restart (takes 5 seconds):

1. Click **System Status** tab
2. You should see: **✓ Running**
3. Done! ✅

---

## Part 5: Upload Students

### Step 5.1: Prepare CSV

Create `students.csv`:
```csv
email,first_name,last_name
alice@company.com,Alice,Smith
bob@company.com,Bob,Jones
charlie@company.com,Charlie,Brown
```

### Step 5.2: Upload via Portal

1. Click **Students** link (top right)
2. Drag CSV onto upload area
3. Watch results appear
4. Students created! ✅

### Step 5.3: Share Lab URL

Share the lab URL with students:
- `http://54.123.45.67` (or your domain)

Students can now log in!

---

## Part 6: Managing Your Lab

### Daily Operations (All Via Browser!)

**Check Status:**
- Settings → System Status
- See CPU, memory, Flask status

**View Logs:**
- Settings → Logs
- See what's happening in real-time

**Restart App:**
- Settings → System Status → Restart Flask App
- Takes 5 seconds

**Deploy Code:**
- Settings → Deployment
- Click "Pull Latest Code & Restart"
- Gets newest code from GitHub

**Upload New Students:**
- Click Students
- Upload CSV
- Done!

**Reset for New Cohort:**
- Students → Delete All Students
- Upload new CSV
- Takes 3 seconds

---

## Part 7: Advanced Configuration

### Using a Domain (Optional)

Instead of IP address, use a domain:

1. **Get Domain**: Route53, GoDaddy, Namecheap, etc.
2. **Point to EC2**: Create A record with EC2 IP
3. **Update .env**: Change `APP_URL=http://yourdomain.com`
4. **Restart Flask** via Settings tab
5. **Access**: `http://yourdomain.com`

### Enable HTTPS (Optional)

For production, enable SSL:

1. SSH into instance once:
```bash
ssh -i your-key.pem ubuntu@54.123.45.67
```

2. Install Certbot:
```bash
sudo apt-get install certbot python3-certbot-nginx -y
sudo certbot certonly --standalone -d yourdomain.com
```

3. Update Flask config (via Settings → Configuration)
4. Or contact support

### Auto-Backups (Optional)

DynamoDB automatically backs up student data:
1. AWS Console → DynamoDB → Tables
2. Click your table
3. Enable **Point-in-time recovery**
4. Done! Auto-backed up

---

## Part 8: Cost Optimization

### Monthly Costs

| Resource | Instance Type | Cost |
|----------|---|---|
| EC2 Compute | t3.micro | ~$3-5 |
| EC2 Compute | t3.small | ~$10-12 |
| Data Transfer | Default | Free (within region) |
| DynamoDB | PAY_PER_REQUEST | $1-5 depending on usage |
| **Total** | t3.small | ~$15/month |

### Cost Saving Tips

- ✅ Use t3.micro for <20 students
- ✅ Use t3.small for 20-100 students
- ✅ Stop instance when not in use (in AWS console)
- ✅ Can upgrade instance type anytime (click stop → change type → start)
- ✅ DynamoDB scales automatically

### Stopping Instance (To Save Money)

When not using lab:

1. AWS Console → EC2 → Instances
2. Right-click instance
3. Select **Stop instance**
4. Instance paused, still costs ~1% of running cost
5. To restart: Right-click → **Start instance**

---

## Part 9: Troubleshooting

### Lab Won't Load

**Problem**: Can't access `http://54.123.45.67`

**Solution**:
1. Check EC2 is running (AWS console)
2. Check security group allows HTTP (port 80)
3. Wait 30 seconds (Flask might be starting)
4. Try Settings → Restart Flask App

### Students Can't Log In

**Problem**: Login page loads but says "Invalid credentials"

**Solution**:
1. Settings → Configuration tab
2. Verify Cognito domain is correct
3. Verify Client ID is correct
4. Click Save Configuration
5. Students try again

### Encryption Key Error

**Problem**: "ENCRYPTION_KEY not configured"

**Solution**:
1. Generate key: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
2. Settings → Configuration → Encryption Key
3. Paste the key
4. Save Configuration

### Flask Won't Restart

**Problem**: "Error: Could not restart Flask"

**Solution**:
1. Wait 30 seconds
2. Try again
3. If still fails, check logs (Logs tab)
4. Last resort: SSH and run `sudo systemctl restart flask-app`

### Check Logs for Errors

1. Settings → Logs tab
2. Look for red error messages
3. First error usually shows the problem
4. Fix in Configuration tab, save, restart

---

## Part 10: Security Best Practices

### Before Running in Production

1. **Enable HTTPS** (see Part 7)
2. **Update Security Group**:
   - Restrict SSH to your IP only
   - Keep HTTP/HTTPS open (students need it)
3. **Strong Cognito Password**: Change after first login
4. **Backup** → Enable DynamoDB PITR
5. **Monitor**: Check logs occasionally

### Ongoing

- ✅ Keep secrets (Client Secret) out of code
- ✅ Don't share EC2 IP publicly
- ✅ Restrict SSH access to your IP
- ✅ Review logs if something seems off
- ✅ Update Flask code regularly via Deployment tab

---

## Part 11: Scaling Up Later

If you need more power:

1. AWS Console → EC2 → Instances
2. Right-click instance
3. Select **Instance Settings** → **Change Instance Type**
4. Select larger type (t3.medium, t3.large, etc.)
5. Reboot
6. **Done!** No redeployment needed

---

## Summary Checklist

### Initial Setup (One Time)
- [ ] Launch EC2 instance
- [ ] Note public IP address
- [ ] Create/download SSH key
- [ ] SSH into instance
- [ ] Run setup script
- [ ] Close SSH connection

### Configuration (One Time)
- [ ] Open lab in browser
- [ ] Log in with Cognito
- [ ] Go to Settings tab
- [ ] Enter Cognito domain, client ID, secret
- [ ] Generate encryption key
- [ ] Add proctor emails
- [ ] Click Save Configuration
- [ ] Verify Flask is running

### Student Onboarding
- [ ] Prepare CSV with student emails
- [ ] Go to Students tab
- [ ] Upload CSV
- [ ] Share lab URL with students
- [ ] Students log in with Cognito

### Ongoing Operations
- [ ] Check status occasionally (Settings tab)
- [ ] Restart Flask if needed (1 click)
- [ ] Deploy new code when available (Deployment tab)
- [ ] Reset students between cohorts (3 clicks)
- [ ] View logs if issues arise

---

## Getting Help

### Check Logs First
- Settings → Logs tab
- Usually shows the exact problem

### Common Issues & Fixes

| Issue | Check |
|-------|-------|
| Lab won't load | Is Flask running? (Status tab) |
| Login fails | Cognito settings correct? |
| Students can't create credentials | Encryption key set? |
| Slow performance | Check CPU/memory (Status tab) |
| Code changes not showing | Did you Deploy? (Deployment tab) |

### Support Resources
- Check logs (Settings → Logs)
- Restart Flask (Settings → System Status)
- Pull latest code (Settings → Deployment)
- Review this guide's troubleshooting section

---

## Final Notes

✅ **Web-Based Management**: Everything after initial setup is done in browser
✅ **No Terminal Needed**: No AWS CLI, no manual scripts
✅ **Fully Automated**: Flask starts/restarts automatically
✅ **Cost Effective**: $10-15/month for full lab
✅ **Scalable**: Easy to upgrade instance type later
✅ **Always On**: Lab runs 24/7 if needed
✅ **Simple Reset**: Delete all + upload new CSV = ready for next cohort

You now have a professional, web-managed AI Assurance Lab running on AWS!

**Welcome to the automated lab! 🚀**
