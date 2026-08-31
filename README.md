# AI Assurance Lab

A web application for 40 students to learn network troubleshooting using Claude AI with MCP (Model Context Protocol) integrations to ThousandEyes and Meraki APIs.

## Features

- **Email-based Authentication** via AWS Cognito
- **User-Configurable MCP Connectivity**: Each student manages their own encrypted API credentials
- **Claude AI Chatbot** powered by AWS Bedrock
- **ThousandEyes Integration** for network monitoring and alerts
- **Meraki Integration** for network device and client management
- **Encrypted Credential Storage** in DynamoDB (per-user, application-level encryption)
- **Real-time Service Status** indicator

## Architecture Overview

```
┌─────────────┐
│  Cognito    │  Email-based login
└──────┬──────┘
       │
┌──────▼──────────────────────┐
│  Flask Application (app.py)  │
│  - Auth routes               │
│  - Credential management     │
│  - Chat endpoint             │
└──────┬──────────────────────┘
       │
       ├─────────────────────┐
       │                     │
┌──────▼─────────┐   ┌───────▼──────┐
│    DynamoDB     │   │   Bedrock    │
│ (Encrypted      │   │   (Claude)   │
│  Credentials)   │   └──────────────┘
└─────────────────┘
       │
       ├─────────────────────────────┐
       │                             │
┌──────▼─────────┐         ┌────────▼───────┐
│ ThousandEyes   │         │     Meraki     │
│  API (user     │         │   API (user    │
│  token)        │         │   token)       │
└────────────────┘         └────────────────┘
```

## Prerequisites

- Python 3.11+
- AWS Account with:
  - Cognito User Pool configured
  - DynamoDB access
  - Bedrock Claude model enabled
- ThousandEyes and Meraki API credentials for testing

## Setup Instructions

### 1. Clone and Install Dependencies

```bash
cd "AI Assurance MCP day"
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure AWS CLI

```bash
aws configure
# Enter your AWS credentials and region (us-east-1)
```

### 3. Create DynamoDB Table

```bash
aws dynamodb create-table \
  --table-name AIAssuranceLab-UserMCPCredentials \
  --attribute-definitions AttributeName=email,AttributeType=S \
  --key-schema AttributeName=email,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### 4. Generate Encryption Key

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output (32-byte base64 string).

### 5. Create `.env` File

```bash
cp .env.example .env
```

Edit `.env` with:
- Cognito pool information (domain, client ID, client secret)
- Encryption key (from step 4)
- Other AWS region settings if needed

### 6. Set Up Cognito User Pool

1. Go to AWS Cognito console
2. Create user pool named "AI-Assurance-Lab"
3. Configure email sign-in
4. Create app client (web)
5. Add callback URL: `http://localhost:5000/auth/callback`
6. Copy User Pool ID and Client ID to `.env`

### 7. Run Locally

```bash
python3 app.py
```

Visit `http://localhost:5000` to start using the application.

## Environment Variables

See `.env.example` for all required variables:

- `COGNITO_DOMAIN`: Your Cognito domain
- `COGNITO_CLIENT_ID`: Web app client ID
- `COGNITO_CLIENT_SECRET`: Web app client secret
- `ENCRYPTION_KEY`: Fernet key for credential encryption
- `BEDROCK_REGION`: AWS region for Bedrock (default: us-east-1)
- `DYNAMODB_TABLE`: DynamoDB table name
- `FLASK_ENV`: Set to 'development' or 'production'
- `SECRET_KEY`: Flask session secret key

## Credential Management

### How Students Add Credentials

1. Click "⚙️ Credentials" in the header
2. Paste their ThousandEyes API token in the token field
3. Click "Save Token"
4. Click "Test Connection" to verify
5. Repeat for Meraki

### Security Features

- ✅ Credentials encrypted at rest using Fernet symmetric encryption
- ✅ Encryption is user-specific (student A cannot decrypt student B's tokens)
- ✅ Tokens never exposed to frontend (only status indicators)
- ✅ Tokens retrieved fresh for each API call
- ✅ No tokens logged or stored in plaintext
- ✅ Each student's credentials stored independently in DynamoDB

## File Structure

```
ai-assurance-lab/
├── app.py                    # Flask app with all routes
├── crypto.py                 # Encryption/decryption utilities
├── dynamo_db.py              # DynamoDB operations and connectivity tests
├── tool_handlers.py          # ThousandEyes and Meraki API handlers
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker container specification
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore patterns
├── templates/
│   ├── lab.html              # Main chat interface
│   └── credentials.html      # Credential management UI
├── static/
│   └── css/
│       └── style.css         # Shared styles
└── README.md                 # This file
```

## Deployment to AWS AppRunner

### 1. Build and Push Docker Image

```bash
aws ecr create-repository --repository-name ai-assurance-lab --region us-east-1

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Build and push
docker build -t ai-assurance-lab .
docker tag ai-assurance-lab:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-assurance-lab:latest
```

### 2. Create AppRunner Service

1. Go to AWS AppRunner console
2. Create new service
3. Select "Container registry" and point to ECR image
4. Configure port: 8080
5. Set environment variables from `.env`
6. Create service

### 3. Update Cognito Callback URL

In Cognito User Pool settings:
- Update app client allowed redirect URI to: `https://<apprunner-url>/auth/callback`

## Testing

### Test Encryption Module

```bash
python3 -c "
import os
os.environ['ENCRYPTION_KEY'] = __import__('cryptography.fernet', fromlist=['Fernet']).Fernet.generate_key().decode()
from crypto import test_encryption
test_encryption()
"
```

### Test DynamoDB Connection

```bash
python3 -c "
from dynamo_db import get_table
try:
    table = get_table()
    print('✓ DynamoDB connection successful')
except Exception as e:
    print(f'✗ DynamoDB error: {e}')
"
```

### Test Credential Flow

1. Log in to the web app
2. Go to Credentials page
3. Paste a test API token
4. Click "Test Connection"
5. Verify success/failure message

## Troubleshooting

### "Missing ENCRYPTION_KEY" Error
- Generate key: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- Add to `.env`: `ENCRYPTION_KEY=<generated-key>`

### "DynamoDB table not found" Error
- Create table using AWS CLI command above
- Verify table name matches `DYNAMODB_TABLE` in `.env`

### "Cognito authentication failed" Error
- Verify `COGNITO_DOMAIN`, `COGNITO_CLIENT_ID`, `COGNITO_CLIENT_SECRET` in `.env`
- Check callback URL matches in Cognito console
- Ensure app client is configured for web

### Credentials Not Saved
- Check CloudWatch logs for DynamoDB errors
- Verify IAM role has DynamoDB permissions
- Check ENCRYPTION_KEY is valid 32-byte base64 string

## API Reference

### Authentication

- `GET /login` - Redirect to Cognito login
- `GET /auth/callback` - Handle Cognito callback
- `GET /logout` - Logout and clear session

### Credential Management

- `GET /api/credentials` - Get credential status (no plaintext tokens)
- `POST /api/credentials/add` - Add/update credential
- `POST /api/credentials/test` - Test API connectivity
- `POST /api/credentials/delete` - Delete credential

### Chat

- `POST /api/chat` - Send message, retrieve Claude response with tool results

## Security Considerations

### Token Encryption

Tokens are encrypted using Fernet (symmetric) with a user-specific context:

```python
# User A's token encrypted with key derived from (ENCRYPTION_KEY + A@example.com)
# User B cannot decrypt with their context (ENCRYPTION_KEY + B@example.com)
```

### Session Security

- HttpOnly session cookies (no JavaScript access)
- 7-day session duration
- HTTPS-only in production

### API Security

- All endpoints require `@login_required` decorator
- User email extracted from Cognito session (never from request)
- DynamoDB queries scoped by user email

## License

Internal use for AI Assurance event. All rights reserved.

## Support

For issues or questions, contact the workshop organizers.
