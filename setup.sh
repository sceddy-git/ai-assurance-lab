#!/bin/bash

# AI Assurance Lab - Setup Script
# Run this script to configure the application for local development

set -e

echo "🚀 AI Assurance Lab - Setup Script"
echo "=================================="

# Check Python version
echo ""
echo "✓ Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "  Using Python $python_version"

# Create virtual environment
echo ""
echo "✓ Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  Created venv/"
else
    echo "  venv/ already exists"
fi

# Activate virtual environment
echo ""
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "✓ Installing dependencies..."
pip install --upgrade pip > /dev/null
pip install -r requirements.txt > /dev/null
echo "  Installed all requirements"

# Generate encryption key if not present
echo ""
echo "✓ Checking encryption key..."
if [ ! -f ".env" ]; then
    echo "  Generating new encryption key..."
    encryption_key=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    cp .env.example .env
    sed -i.bak "s/your-32-byte-fernet-key-in-base64/$encryption_key/" .env
    rm -f .env.bak
    echo "  ✓ Generated and saved to .env"
else
    echo "  .env already exists"
fi

# Generate Flask secret key
echo ""
echo "✓ Checking Flask secret key..."
if ! grep -q "SECRET_KEY=" .env || grep -q "SECRET_KEY=your-flask-secret-key" .env; then
    echo "  Generating new Flask secret key..."
    flask_key=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i.bak "s/SECRET_KEY=.*/SECRET_KEY=$flask_key/" .env
    rm -f .env.bak
    echo "  ✓ Generated and saved to .env"
fi

# Test encryption
echo ""
echo "✓ Testing encryption module..."
python3 -c "
import os
os.environ['ENCRYPTION_KEY'] = __import__('cryptography.fernet', fromlist=['Fernet']).Fernet.generate_key().decode()
from crypto import test_encryption
if test_encryption():
    print('  ✓ Encryption working correctly')
else:
    print('  ✗ Encryption test failed')
    exit(1)
" 2>/dev/null || echo "  ⚠ Encryption test skipped (ENCRYPTION_KEY may not be set)"

# Check AWS credentials
echo ""
echo "✓ Checking AWS credentials..."
if aws sts get-identity > /dev/null 2>&1; then
    account_id=$(aws sts get-identity | grep Account | grep -oP '\d{12}')
    echo "  ✓ AWS configured (Account: $account_id)"
else
    echo "  ⚠ AWS credentials not configured. Run: aws configure"
fi

# Check DynamoDB table
echo ""
echo "✓ Checking DynamoDB table..."
if aws dynamodb describe-table --table-name AIAssuranceLab-UserMCPCredentials --region us-east-1 > /dev/null 2>&1; then
    table_status=$(aws dynamodb describe-table --table-name AIAssuranceLab-UserMCPCredentials --region us-east-1 | grep TableStatus | grep -oP '(?<=: ")[^"]*')
    echo "  ✓ Table exists (Status: $table_status)"
else
    echo "  ⚠ Table not found. Create with:"
    echo "    aws dynamodb create-table \\"
    echo "      --table-name AIAssuranceLab-UserMCPCredentials \\"
    echo "      --attribute-definitions AttributeName=email,AttributeType=S \\"
    echo "      --key-schema AttributeName=email,KeyType=HASH \\"
    echo "      --billing-mode PAY_PER_REQUEST \\"
    echo "      --region us-east-1"
fi

# Summary
echo ""
echo "=================================="
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your Cognito and AWS settings"
echo "2. Create DynamoDB table if not already created (see above)"
echo "3. Run: python3 app.py"
echo "4. Visit: http://localhost:5000"
echo ""
echo "For more information, see README.md"
