# Git & CI/CD Setup - Always-On Lab

## Overview

Your lab will:
- ✅ Run 24/7 on EC2 ($15/month)
- ✅ Store code on GitHub
- ✅ Deploy updates via one-click in web portal
- ✅ Optional: Auto-deploy on git push (CI/CD)

---

## Part 1: Push Code to GitHub (One Time)

### Step 1.1: Create GitHub Repository

1. Go to **github.com**
2. Click **"New repository"** (green button)
3. **Name**: `ai-assurance-lab`
4. **Description**: AI Assurance Lab with web-managed Flask
5. **Public or Private**: Your choice
6. **Initialize with README**: No (we'll add our own)
7. Click **"Create repository"**

### Step 1.2: Push Code to GitHub

```bash
# Navigate to your project directory
cd /Users/sceddy/Documents/AI\ Assurance\ MCP\ day

# Initialize git (if not already done)
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: AI Assurance Lab with web-managed EC2 deployment"

# Add remote (replace YOUR_USERNAME and REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/ai-assurance-lab.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Step 1.3: Verify

Visit: `https://github.com/YOUR_USERNAME/ai-assurance-lab`

You should see all your code on GitHub! ✅

---

## Part 2: Keep Lab Always On

### Option A: Always Running (Simplest)

**Just leave EC2 running:**

```
EC2 Instance Status: running 24/7
Flask Service Status: running (systemd keeps it alive)
Cost: $15/month (continuous)
Uptime: 99%+ (automatic restarts if crash)
```

**No action needed** - it just runs!

### Option B: Stop When Not in Use (Save Money)

If you don't need it 24/7:

```bash
# Stop instance (via AWS Console)
EC2 → Instances → Right-click → "Stop instance"
Status: stopped
Cost: ~$1/month (storage only)

# Restart when needed
EC2 → Instances → Right-click → "Start instance"
Time to start: 2-3 minutes
```

**Our recommendation: Leave it running. $15/month is cheap for always-on availability!**

---

## Part 3: Deploying Enhancements

### Option A: One-Click Deploy (Easiest)

After pushing code to GitHub:

1. Click **Settings** tab in web portal
2. Click **Deployment** section
3. Click **"Pull Latest Code & Restart"**
4. Flask pulls latest from GitHub and restarts
5. Done in 30 seconds! ✅

**This is the manual approach - works great for occasional updates.**

### Option B: Auto-Deploy on Git Push (Optional CI/CD)

For automatic deployment on every push:

#### GitHub Actions Setup (Simple)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to EC2

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Deploy to EC2
      env:
        SSH_KEY: ${{ secrets.EC2_SSH_KEY }}
        EC2_HOST: ${{ secrets.EC2_HOST }}
        EC2_USER: ubuntu
      run: |
        mkdir -p ~/.ssh
        echo "$SSH_KEY" > ~/.ssh/id_rsa
        chmod 600 ~/.ssh/id_rsa
        ssh-keyscan -H $EC2_HOST >> ~/.ssh/known_hosts
        ssh -i ~/.ssh/id_rsa $EC2_USER@$EC2_HOST << 'EOF'
          cd /home/ubuntu/ai-assurance-lab
          git pull origin main
          source venv/bin/activate
          pip install -r requirements.txt
          sudo systemctl restart flask-app
        EOF
```

#### GitHub Secrets Setup

1. Go to **GitHub repo → Settings → Secrets and variables → Actions**
2. Click **"New repository secret"**
3. Add secrets:
   - **Name**: `EC2_SSH_KEY` → Paste your EC2 private key content
   - **Name**: `EC2_HOST` → Your EC2 public IP (e.g., `54.123.45.67`)
4. Save

#### Test It

1. Make a code change locally
2. Commit and push to GitHub
3. GitHub Actions runs automatically
4. Check EC2 logs (Settings → Logs) for deployment status
5. Your changes are live! ✅

**Result: Every git push automatically deploys to EC2!**

---

## Part 4: Recommended Workflow

### For Small Updates
```
Edit code locally
  ↓
git commit + git push
  ↓
GitHub Actions auto-deploys
  ↓
Lab updates live (30 seconds)
```

### For Testing Before Deploy
```
Edit code locally
  ↓
Test in development
  ↓
git commit + git push
  ↓
GitHub Actions auto-deploys
  ↓
Lab updates live
```

### For Quick Fixes
```
Web portal issue noticed
  ↓
Fix code locally
  ↓
git push
  ↓
Auto-deployed within seconds
  ↓
Done!
```

---

## Part 5: Repository Structure

Your GitHub repo will have:

```
ai-assurance-lab/
├── app.py                           # Main Flask app
├── requirements.txt                 # Dependencies
├── .env.example                     # Config template
├── ec2-setup.sh                     # Setup script
├── Dockerfile                       # Optional (not needed for EC2)
├── templates/
│   ├── lab.html
│   ├── admin_students.html
│   ├── admin_settings.html
│   ├── credentials.html
│   └── login.html
├── static/
│   └── css/style.css
├── dynamo_db.py
├── crypto.py
├── tool_handlers.py
├── .github/
│   └── workflows/
│       └── deploy.yml              # CI/CD pipeline (optional)
└── docs/
    ├── 00_READ_THIS_FIRST.md
    ├── START_HERE_EC2.md
    ├── EC2_SETUP_MINIMAL.md
    └── ... (other docs)
```

---

## Part 6: Ongoing Operations

### Daily Operations (All Web-Based)
- Click "Settings" to configure
- Click "Students" to upload new cohorts
- Click "Logs" to troubleshoot

### Code Updates (Two Options)

**Option 1: Manual (via web portal)**
```
Edit code → Push to GitHub → Settings → "Pull Latest Code" → Done
```

**Option 2: Automatic (via CI/CD)**
```
Edit code → Push to GitHub → Auto-deploys → Done
```

### Monitoring
- Always-on: EC2 keeps running
- Auto-restart: Systemd restarts Flask if it crashes
- Manual restart: One click in Settings tab
- Logs: View in real-time in Settings

---

## Part 7: Cost Analysis

### Monthly Cost (Always On)
```
EC2 t3.small:       $10-12
DynamoDB:           $1-5
GitHub (free):      $0
CI/CD (GitHub):     $0
─────────────────────────
TOTAL:              ~$15/month
```

### Stop Scenario (If you stop when not needed)
```
EC2 stopped:        $0.50-1/month
DynamoDB:           $1-5
Total:              ~$5/month
```

**Always-on is the sweet spot!**

---

## Part 8: Best Practices

### Code Management
✅ Commit often with clear messages
✅ Use meaningful branch names
✅ Keep main branch deployable
✅ Test locally before pushing
✅ Include documentation

### Security
✅ Never commit `.env` file (use `.env.example`)
✅ Use GitHub Secrets for sensitive data
✅ Keep dependencies updated
✅ Review code before push

### Deployment
✅ Push to GitHub frequently
✅ Use CI/CD for automatic deployment
✅ Monitor logs after deployment
✅ Keep a backup of `.env` file locally

---

## Part 9: Troubleshooting

### GitHub Push Fails

**Problem**: `fatal: 'origin' does not appear to be a git repository`

**Solution**:
```bash
git remote add origin https://github.com/YOUR_USERNAME/ai-assurance-lab.git
git branch -M main
git push -u origin main
```

### CI/CD Won't Deploy

**Problem**: GitHub Actions runs but EC2 doesn't update

**Check**:
1. SSH key in GitHub Secrets is correct
2. EC2 IP address in GitHub Secrets is correct
3. EC2 security group allows SSH (port 22)
4. Check EC2 logs: Settings → Logs tab

### Code Changes Not Appearing

**If using manual deploy**:
1. Settings → Deployment → "Pull Latest Code"
2. Wait 30 seconds
3. Refresh browser

**If using CI/CD**:
1. Check GitHub Actions tab (red/green status)
2. If red, check logs
3. If green, check EC2 logs (Settings → Logs)

---

## Quick Reference

### Git Commands You'll Use

```bash
# First time setup
git init
git remote add origin https://github.com/YOUR_USERNAME/repo.git

# Regular workflow
git add .                          # Stage all changes
git commit -m "Your message"       # Create commit
git push origin main               # Push to GitHub

# Pull from server
git pull origin main               # Get latest (server only needs this)
```

### GitHub CI/CD

Create `.github/workflows/deploy.yml` and add GitHub Secrets:
- `EC2_SSH_KEY`: Your private key
- `EC2_HOST`: Your EC2 IP

Auto-deploys on every push to main!

### Web Portal Deploy

Settings → Deployment → Pull Latest Code → Done

Manual one-click deploy anytime!

---

## Summary

### What You Have
✅ Code on GitHub
✅ EC2 running 24/7
✅ Manual deploy option (1 click)
✅ Optional auto-deploy (CI/CD)
✅ Always-on availability
✅ ~$15/month cost

### Workflow
1. Edit code locally
2. Push to GitHub
3. Auto-deploys (or manual 1-click)
4. Lab updates live
5. Monitor in Settings tab

### You're Set For
✅ Continuous improvements
✅ Regular updates
✅ Quick bug fixes
✅ Feature additions
✅ All without downtime

---

## Next Steps

### Immediate
1. Create GitHub repo
2. Push code
3. Keep EC2 running
4. Done! Lab is always-on ✅

### Optional
1. Set up GitHub Secrets
2. Create `.github/workflows/deploy.yml`
3. Auto-deploy on push
4. Even simpler workflow!

---

## You're All Set!

Your lab is now:
- ✅ Running 24/7 on EC2
- ✅ Version-controlled on GitHub
- ✅ Ready for enhancements
- ✅ Easy to deploy updates
- ✅ Professional setup

**Enjoy your always-on AI Assurance Lab! 🚀**
