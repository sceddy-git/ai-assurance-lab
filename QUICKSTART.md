# Quick Start Guide - AI Assurance Lab

## 5-Minute Setup

### Prerequisites
- Python 3.11+
- AWS CLI configured with credentials
- AWS account with Bedrock enabled in us-east-1

### Step 1: Install Dependencies (1 min)
```bash
cd "AI Assurance MCP day"
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Generate Keys (1 min)
```bash
# Generate Encryption Key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate Flask Secret
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Step 3: Configure .env (2 min)
```bash
cp .env.example .env
```

Edit `.env` with:
```
COGNITO_DOMAIN=your-pool.auth.us-east-1.amazoncognito.com
COGNITO_CLIENT_ID=your-client-id
COGNITO_CLIENT_SECRET=your-client-secret
ENCRYPTION_KEY=<paste-encryption-key-from-step-2>
SECRET_KEY=<paste-flask-secret-from-step-2>
```

### Step 4: Create DynamoDB Table (1 min)
```bash
aws dynamodb create-table \
  --table-name AIAssuranceLab-UserMCPCredentials \
  --attribute-definitions AttributeName=email,AttributeType=S \
  --key-schema AttributeName=email,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### Step 5: Run the App
```bash
python3 app.py
```

Visit: http://localhost:5000

---

## Testing the Credential System

### 1. Create a Test User in Cognito
- Go to AWS Cognito console
- Create user with email and temporary password
- User will be prompted to set permanent password on first login

### 2. Log In
- Visit http://localhost:5000
- Click "Login"
- Enter test user credentials

### 3. Add Credentials
- Click "⚙️ Credentials"
- Paste your ThousandEyes API token
- Click "Save Token"
- Click "Test Connection"
- You should see "✓ ThousandEyes credential is valid"

### 4. Chat with Claude
- Click back to chat
- See the service status indicator shows ThousandEyes ✓
- Ask a question like: "What tests are available in ThousandEyes?"
- Claude will use your credentials to fetch the data

---

## Troubleshooting

### "No module named 'flask'" 
→ Make sure virtual environment is activated: `source venv/bin/activate`

### "ENCRYPTION_KEY not configured"
→ Generate key and add to .env (see Step 2)

### "Cognito authentication failed"
→ Double-check COGNITO_DOMAIN, CLIENT_ID, CLIENT_SECRET in .env
→ Verify callback URL in Cognito: `http://localhost:5000/auth/callback`

### "DynamoDB table not found"
→ Run the AWS CLI create-table command (Step 4)
→ Check that table name matches in .env

### Credentials won't save
→ Check CloudWatch logs: `aws logs tail --follow /aws/dynamodb/`
→ Verify IAM user has DynamoDB permissions

---

## Files Overview

| File | Purpose |
|------|---------|
| `app.py` | Flask app with all routes |
| `crypto.py` | Fernet encryption/decryption |
| `dynamo_db.py` | DynamoDB CRUD + connectivity tests |
| `tool_handlers.py` | ThousandEyes & Meraki API handlers |
| `templates/lab.html` | Chat interface |
| `templates/credentials.html` | Credential management UI |
| `static/css/style.css` | Shared styles |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Docker container spec |

---

## Next Steps

### For Local Development
- Run tests with `python3 -m pytest` (add tests as needed)
- Enable debug logging: `FLASK_ENV=development`
- Use Flask development server: `python3 app.py` (auto-reload enabled)

### For Deployment to AppRunner
1. Build Docker image: `docker build -t ai-assurance-lab .`
2. Push to ECR
3. Create AppRunner service pointing to ECR
4. Update Cognito callback URL
5. Set environment variables in AppRunner console

### Add More Students
1. Create users in Cognito
2. Send them login link
3. They add their own credentials
4. Each student's data is isolated and encrypted

---

## Security Checklist

- ✅ Credentials encrypted with Fernet (symmetric)
- ✅ User-specific encryption context prevents cross-user access
- ✅ Tokens stored encrypted in DynamoDB
- ✅ No tokens logged or exposed in errors
- ✅ Session cookies are HttpOnly
- ✅ HTTPS required in production
- ✅ All endpoints require login

---

## For Questions

See full documentation in `README.md`
