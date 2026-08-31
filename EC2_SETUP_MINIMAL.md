# EC2 Setup - Web-Managed Flask Lab

## Quick Start (15 minutes)

Launch an EC2 instance, run one setup script, and manage everything through the web portal. No AWS CLI needed!

---

## Step 1: Launch EC2 Instance (AWS Console)

### In AWS Console:
1. Go to **EC2 Dashboard** → **Instances** → **Launch Instances**
2. **Name**: `ai-assurance-lab`
3. **OS Image**: Ubuntu 22.04 LTS (free tier eligible)
4. **Instance Type**: `t3.small` (or `t3.micro` for free tier)
5. **Key Pair**: Create or select (download if new)
6. **Network Settings**:
   - ✅ Allow SSH (port 22) - for initial setup only
   - ✅ Allow HTTP (port 80) - for web access
   - ✅ Allow HTTPS (port 443) - for production
7. **Storage**: 20 GB (default)
8. **Click**: "Launch Instance"
9. **Wait**: Instance shows "running" (2 min)
10. **Copy**: Public IPv4 address (e.g., `54.123.45.67`)

---

## Step 2: SSH into Instance (Terminal)

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@54.123.45.67
# (Replace key and IP with yours)

# You should see Ubuntu prompt:
# ubuntu@ip-xxx:~$
```

---

## Step 3: Run Setup Script (One Command)

```bash
# Download and run setup
curl -fsSL https://raw.githubusercontent.com/your-repo/setup.sh | bash

# This will:
# - Install Python 3.11
# - Install git
# - Clone your repo
# - Install dependencies
# - Configure Flask as systemd service
# - Start Flask app
# - All takes ~5 minutes

# When done, you'll see:
# ✅ Flask running on port 5000
# ✅ Access at: http://54.123.45.67
```

---

## Step 4: Access Portal (Browser)

1. **Open browser**
2. Visit: `http://54.123.45.67` (use your EC2 IP)
3. You should see: **AI Assurance Lab Login**
4. **Login** with your proctor account
5. **Click**: "Settings" (new menu item)
6. You now have full control! 🎉

---

## That's It!

From here, EVERYTHING is web-managed:
- ✅ Upload students via portal
- ✅ Restart Flask app (if needed)
- ✅ Check app status
- ✅ View logs
- ✅ Deploy new code (git pull)
- ✅ Manage environment variables
- ✅ Manage credentials encryption keys

**No AWS CLI. No terminal. Just the web page.**

---

## What Gets Installed

The setup script creates:

```
/home/ubuntu/ai-assurance-lab/
├── app.py
├── requirements.txt
├── templates/
├── static/
├── .env (from template)
└── ...

/etc/systemd/system/
└── flask-app.service (runs Flask automatically)
```

---

## Initial Configuration (5 minutes)

After accessing the portal, go to **Settings** tab:

1. **Cognito Configuration**
   - Enter your Cognito domain
   - Enter client ID
   - Enter client secret
   - Enter user pool ID

2. **Encryption Key**
   - Generate or paste existing key
   - Shown in setup instructions

3. **Proctor Emails**
   - Add comma-separated emails
   - Only these can access admin features

4. **Click**: "Save Configuration"

The app restarts automatically with new settings!

---

## Accessing via Domain (Optional)

Instead of IP address, use a domain:

1. **Get Domain**: Route53, GoDaddy, Namecheap, etc.
2. **Point to EC2 IP**: Create A record
3. **Access**: `http://yourdomain.com`
4. **HTTPS**: Get SSL cert (free via Certbot)

---

## Daily Operations

### Check Status
- **Portal** → **Settings** → **System Status**
- Shows: CPU, Memory, Flask status
- Shows: Last restart time

### View Logs
- **Portal** → **Settings** → **View Logs**
- Real-time Flask logs
- Error tracking
- Request history

### Restart Flask
- **Portal** → **Settings** → **Actions** → **Restart Flask**
- Takes 5 seconds
- No downtime for students already logged in

### Deploy New Code
- **Portal** → **Settings** → **Actions** → **Git Pull**
- Pulls latest from GitHub
- Restarts Flask automatically
- Shows what changed

### Manage Environment
- **Portal** → **Settings** → **Environment**
- Edit any `.env` variable
- No file editing needed
- Changes take effect on Flask restart

---

## Cost

**Monthly Estimate:**
- **t3.micro**: $3-5 (free tier eligible first year)
- **t3.small**: $10-12 (recommended for 40+ students)
- **Data transfer**: Usually free (within AWS region)
- **Total**: Very cheap!

---

## Scaling Up

If you need more power later:

1. **Stop instance**
2. **Resize instance type** (t3.medium, t3.large, etc.)
3. **Start instance**
4. **Done!** No redeployment needed

---

## Backup & Recovery

### Backup Student Data
- **Portal** → **Settings** → **Actions** → **Export Data**
- Downloads JSON of all students
- Downloads DynamoDB table backup

### Restore
- Stop instance
- Create new instance from same setup
- Upload backup
- Restored!

---

## Security Hardening (Optional)

After initial setup, for production:

1. **HTTPS**: Install SSL certificate (Certbot - one command)
2. **Firewall**: Restrict SSH to your IP only
3. **Auto-updates**: Enable automatic security patches
4. **Backups**: Enable automatic DynamoDB backups

All can be configured via portal!

---

## Summary

### Initial Setup
- Launch EC2 (5 min in AWS console)
- SSH and run 1 setup script (5 min)
- Configure via web portal (5 min)
- **Total: 15 minutes**

### Daily Operations
- **Entirely web-based**
- No SSH needed
- No AWS CLI needed
- No terminal commands
- Just log into portal

### Management
- Student accounts: Portal ✅
- App deployment: Portal ✅
- Configuration: Portal ✅
- Logs: Portal ✅
- Restart: Portal ✅
- Everything: Portal! 🎉

---

## Next Steps

1. **Launch EC2 instance** (follow Step 1)
2. **SSH once** (follow Step 2)
3. **Run setup script** (follow Step 3)
4. **Access portal** (follow Step 4)
5. **Configure settings** (5 minutes)
6. **Upload students** (1 minute)
7. **Share lab URL with students**
8. **Done! Lab is running!**

Everything else is just web portal clicks. No more terminal, no more scripts, no more complexity.

**Welcome to the automated lab! 🚀**
