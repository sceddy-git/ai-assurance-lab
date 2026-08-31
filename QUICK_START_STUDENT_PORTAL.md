# Quick Start: Student Management Portal

## 5-Minute Setup

### Step 1: Prepare Your CSV
Create a file called `students.csv`:

```csv
email,first_name,last_name
alice@example.com,Alice,Smith
bob@example.com,Bob,Jones
charlie@example.com,Charlie,Brown
... (repeat for all 40 students)
```

### Step 2: Update .env
Add your email as a proctor:

```bash
PROCTOR_EMAILS=your-email@example.com
```

### Step 3: Restart Flask App
```bash
# Kill old process, start new one
python app.py
```

### Step 4: Open Portal
Visit: `https://[your-lab-url]/admin/students`

### Step 5: Upload CSV
1. Click "Choose File"
2. Select `students.csv`
3. Wait for success message
4. Done! ✅

---

## Usage

### Create Students
1. Open portal at `/admin/students`
2. Upload CSV → Students created in Cognito
3. Share lab URL with students
4. They log in with email

### Reset for New Cohort
1. Click "Delete All Students"
2. Confirm twice (safety)
3. Upload new CSV with different emails
4. New students ready immediately

### Check Current Students
1. Click "Refresh List"
2. See all students in table
3. View their status and creation date

---

## CSV Examples

### Minimal (Just Emails)
```csv
email,first_name,last_name
alice@example.com,Alice,Smith
bob@example.com,Bob,Jones
```

### Full Details
```csv
email,first_name,last_name
alice.smith@mycompany.com,Alice,Smith
bob.jones@mycompany.com,Bob,Jones
charlie.brown@mycompany.com,Charlie,Brown
david.garcia@mycompany.com,David,Garcia
emma.wilson@mycompany.com,Emma,Wilson
frank.lee@mycompany.com,Frank,Lee
```

### Excel Users
1. Save as `.csv` (not .xlsx)
2. Download if needed
3. Upload to portal

---

## Workflow

### Day 1 - Initial Deployment
```bash
# Deploy lab
bash AWS_ONLY_DEPLOY.sh          # ~20 min
# App is now running

# Then manage students
# Visit /admin/students portal
# Upload cohort1.csv with 40 students
# Lab ready!
```

### Day 2 - New Cohort (Same Infrastructure)
```bash
# No deployment needed!
# Just reset students

# Visit portal
# Click "Delete All Students"
# Upload cohort2.csv with 40 new students
# Done in ~3 minutes!
```

### Day 3 - Another Cohort
```bash
# Repeat Day 2 process
# Reset + upload = 3 minutes
```

---

## Tips & Tricks

### Large CSV Files
- Portal supports 1000+ students
- Takes ~1-2 seconds per student
- Progress shown in real-time

### Duplicates
- If email exists, it shows error
- Safe to retry with cleaned CSV
- No students partially created

### Offline Prep
1. Create CSV with all students
2. Keep in shared folder
3. When lab ready, just upload

### Batch Multiple Times
1. Upload Monday morning: 40 students
2. Upload Monday afternoon: 40 different students
3. Upload Tuesday: 40 different students
4. All using same infrastructure!

---

## Student Login Flow

### What Students See
1. Click Lab URL
2. "Sign in with email"
3. Enter email: `alice@example.com`
4. Click "Continue"
5. Check email for temporary password
6. Enter password on lab
7. Set permanent password
8. **Logged in!** Access lab

### Typical Email Arrival
- Usually: < 1 minute
- Sometimes: 2-3 minutes
- Can click "Resend" if not received

---

## Troubleshooting

### "Access Denied" Error
→ Check that your email is in `PROCTOR_EMAILS` in .env

### CSV Upload Fails
→ Make sure file is `.csv` format, not `.xlsx`

### Students Not Created
→ Check CSV has `email` column and valid emails

### "User already exists"
→ Click "Delete All Students" first, then upload

### Can't See Portal
→ Must be logged in to lab first
→ Must be proctor email

---

## Summary

✅ **Deploy Lab** (first time) - 20 minutes
✅ **Upload Students** - 1 minute
✅ **Reset & Re-upload** - 3 minutes
✅ **No terminal commands needed!**
✅ **Fully browser-based management**

The portal makes managing multiple student cohorts incredibly easy!
