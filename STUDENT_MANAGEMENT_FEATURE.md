# Student Management Portal - New Feature

## Overview

The AI Assurance Lab now includes a **web-based Student Management Portal** that allows proctors to upload and manage student accounts directly through the Flask application interface.

**No more bash scripts needed!** Simply:
1. Open the portal in your browser
2. Upload a CSV file with student emails
3. Students are created in Cognito immediately
4. View, reset, and manage students from the portal

---

## Accessing the Portal

### URL
```
https://[your-lab-url]/admin/students
```

### Requirements
- Must be logged in to the lab application
- Email address must be in `PROCTOR_EMAILS` environment variable

### Configure Proctor Access
In your `.env` file, add:
```bash
PROCTOR_EMAILS=admin@example.com,another.proctor@example.com
```

---

## Features

### 1. Upload Students CSV
- **Drag & Drop**: Drag CSV file onto the upload area
- **Click Upload**: Click to browse and select file
- **Format**: CSV with columns: `email`, `first_name`, `last_name`

**Example CSV:**
```
email,first_name,last_name
alice@example.com,Alice,Smith
bob@example.com,Bob,Jones
charlie@example.com,Charlie,Brown
```

**Results:**
- Shows number of students created
- Shows errors if any
- Auto-refreshes student list

### 2. View Current Students
- **Live List**: See all students currently in Cognito
- **Details**: Email, name, creation date, status
- **Auto-Load**: List updates after CSV upload
- **Refresh**: Click "Refresh List" anytime

### 3. Reset Students
- **Delete All**: Remove all current students
- **Confirm Twice**: Safety confirmation dialogs
- **Quick Reset**: Prepare for new cohort in seconds
- **Preserves Data**: Credentials in DynamoDB remain (if needed)

---

## Workflow Example

### First Lab
1. Open `/admin/students` in browser
2. Click "Choose File"
3. Select `cohort1.csv` (40 students)
4. View results: "Created: 40, Failed: 0"
5. Students can now log in immediately

### Second Lab (Same Day)
1. Click "Delete All Students"
2. Confirm twice
3. Upload `cohort2.csv` (different 40 students)
4. View results: "Created: 40, Failed: 0"
5. Students ready to go!

### Multiple Cohorts (Same Week)
- Repeat step 1-5 as many times as needed
- No downtime, no scripts, no terminal commands
- Everything in the browser

---

## CSV Format

### Required Columns
- `email` - Student email address (must be unique per cohort)
- `first_name` - (optional) Student's first name
- `last_name` - (optional) Student's last name

### Example
```csv
email,first_name,last_name
alice.smith@company.com,Alice,Smith
bob.jones@company.com,Bob,Jones
charlie.brown@company.com,Charlie,Brown
david.garcia@company.com,David,Garcia
emma.wilson@company.com,Emma,Wilson
```

### Notes
- Must be plain text CSV (not Excel format)
- Headers are required
- Email column is mandatory
- Extra columns are ignored
- Duplicate emails are skipped with error message
- One student per line

---

## Error Handling

### Common Errors
| Error | Cause | Solution |
|-------|-------|----------|
| "File must be CSV format" | Wrong file type uploaded | Save as `.csv` not `.xlsx` |
| "{email}: User already exists" | Email already in system | Delete all students first, or use different emails |
| "{email}: Invalid..." | Malformed email | Check email format in CSV |

### Error Display
- **Upload Results**: Shows count of successes and failures
- **Error Details**: First 10 errors displayed (scroll to see)
- **Retry**: Fix errors and upload again

---

## Authentication

### Login Flow
1. Student receives Cognito email with password
2. Clicks lab URL
3. Enters email + temporary password
4. Sets permanent password
5. Logs in and uses lab

### Resetting Passwords
Students can click "Forgot Password" on login page to reset.

---

## Technical Details

### Backend API Endpoints
All endpoints require proctor authentication (`PROCTOR_EMAILS`):

- `POST /api/admin/students/upload` - Upload and create students
- `GET /api/admin/students/list` - List all students
- `POST /api/admin/students/delete-all` - Delete all students

### Security
- ✅ Requires login
- ✅ Checks proctor email access
- ✅ Rate-limited by Flask
- ✅ Cognito password auto-generated
- ✅ No credentials exposed

### Performance
- Handles 100+ students per CSV
- Creates ~1-2 seconds per student
- Batch errors reported clearly
- Non-blocking (shows progress)

---

## Advantages Over Bash Scripts

| Feature | Portal | Scripts |
|---------|--------|---------|
| Browser-based | ✅ | ❌ |
| No terminal needed | ✅ | ❌ |
| Error details shown | ✅ | Limited |
| Progress display | ✅ | Limited |
| Refresh list in UI | ✅ | Manual |
| Delete all easily | ✅ | Manual |
| Mobile-friendly | ✅ | ❌ |
| No shell commands | ✅ | ❌ |

---

## Future Enhancements

Possible additions:
- Individual student deletion
- Password reset from portal
- Bulk email sending
- CSV download of current students
- Student activity logs
- Credential reset option

---

## Troubleshooting

### Portal Not Loading
1. Verify you're logged in to the lab
2. Check that your email is in `PROCTOR_EMAILS`
3. Try incognito browser

### Upload Hanging
- Wait 1-2 minutes for large files
- Check browser console for errors (F12)
- Try smaller batch of students

### Students Not Created
- Check CSV format (must have `email` column)
- Verify no duplicate emails in CSV
- Delete all students first, then retry

---

## Summary

The **Student Management Portal** makes it incredibly easy to:
- ✅ Create student accounts with one CSV upload
- ✅ Reset cohorts in seconds
- ✅ View all current students
- ✅ See real-time results and errors
- ✅ Manage everything from your browser

No more bash scripts. No more terminal commands. Just drag, drop, and go!
