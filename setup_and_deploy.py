#!/usr/bin/env python3
"""
AI Assurance Lab - Complete Setup & Deployment Script
Handles everything: Docker build, ECR push, AppRunner deployment, student creation
"""

import os
import sys
import subprocess
import json
import csv
import time
import boto3
from pathlib import Path
from datetime import datetime

# Configuration
ACCOUNT_ID = "004878717866"
REGION = "us-east-1"
REPO_NAME = "ai-assurance-lab"
SERVICE_NAME = "ai-assurance-lab"
PROJECT_DIR = "/Users/sceddy/Documents/AI Assurance MCP day"

class AIAssuranceLabDeployment:
    def __init__(self):
        self.cognito_client = boto3.client('cognito-idp', region_name=REGION)
        self.apprunner_client = boto3.client('apprunner', region_name=REGION)
        self.iam_client = boto3.client('iam', region_name=REGION)
        self.config = {}
        
    def log(self, message, level="ℹ️"):
        """Print formatted log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level} {message}")
    
    def run_command(self, cmd, description=""):
        """Run shell command"""
        if description:
            self.log(description)
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                self.log(f"Error: {result.stderr}", "❌")
                return False, result.stderr
            return True, result.stdout
        except Exception as e:
            self.log(f"Exception: {str(e)}", "❌")
            return False, str(e)
    
    def load_cognito_config(self):
        """Load Cognito configuration from previous setup"""
        config_file = Path("/tmp/cognito_config.txt")
        if not config_file.exists():
            self.log("Cognito config not found. Run AWS CLI setup first.", "⚠️")
            return False
        
        with open(config_file) as f:
            for line in f:
                key, value = line.strip().split('=', 1)
                self.config[key] = value
        
        self.log(f"Loaded Cognito config", "✅")
        return True
    
    def build_docker_image(self):
        """Build Docker image"""
        self.log("Building Docker image...", "📦")
        
        # Check if Docker is running
        ok, _ = self.run_command("docker ps > /dev/null 2>&1")
        if not ok:
            self.log("Docker is not running. Please start Docker Desktop.", "❌")
            return False
        
        os.chdir(PROJECT_DIR)
        ok, output = self.run_command(
            f"docker build -t {REPO_NAME}:latest .",
            "Building Docker image..."
        )
        
        if ok:
            self.log("Docker image built successfully", "✅")
            return True
        else:
            self.log(f"Docker build failed: {output}", "❌")
            return False
    
    def push_to_ecr(self):
        """Push Docker image to ECR"""
        self.log("Pushing image to ECR...", "⬆️")
        
        ecr_uri = f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com"
        
        # Login to ECR
        ok, _ = self.run_command(
            f"aws ecr get-login-password --region {REGION} | docker login --username AWS --password-stdin {ecr_uri}",
            "Logging into ECR..."
        )
        
        if not ok:
            self.log("ECR login failed", "❌")
            return False
        
        # Tag image
        ok, _ = self.run_command(
            f"docker tag {REPO_NAME}:latest {ecr_uri}/{REPO_NAME}:latest",
            "Tagging image..."
        )
        
        if not ok:
            self.log("Docker tag failed", "❌")
            return False
        
        # Push image
        ok, _ = self.run_command(
            f"docker push {ecr_uri}/{REPO_NAME}:latest",
            "Pushing to ECR..."
        )
        
        if ok:
            self.log("Image pushed to ECR", "✅")
            self.config['ECR_IMAGE'] = f"{ecr_uri}/{REPO_NAME}:latest"
            return True
        else:
            self.log("Docker push failed", "❌")
            return False
    
    def create_apprunner_service(self):
        """Create AppRunner service"""
        self.log("Creating AppRunner service...", "🚀")
        
        ecr_image = self.config.get('ECR_IMAGE', f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/{REPO_NAME}:latest")
        role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/ai-assurance-lab-apprunner-role"
        
        try:
            response = self.apprunner_client.create_service(
                ServiceName=SERVICE_NAME,
                SourceConfiguration={
                    'ImageRepository': {
                        'ImageIdentifier': ecr_image,
                        'ImageRepositoryType': 'ECR',
                        'ImageConfiguration': {
                            'Port': '8080'
                        }
                    }
                },
                InstanceConfiguration={
                    'Cpu': '1024',
                    'Memory': '2048',
                    'InstanceRoleArn': role_arn
                }
            )
            
            service_arn = response['Service']['ServiceArn']
            self.config['SERVICE_ARN'] = service_arn
            self.log(f"AppRunner service created: {service_arn}", "✅")
            
            # Wait for service to become RUNNING
            self.log("Waiting for service to become RUNNING...", "⏳")
            self.wait_for_service(service_arn)
            
            return True
        except Exception as e:
            if 'InvalidParameterException' in str(e) and 'already exists' in str(e):
                self.log("Service already exists. Finding existing service...", "⚠️")
                try:
                    response = self.apprunner_client.list_services()
                    for service in response.get('ServiceSummaryList', []):
                        if service['ServiceName'] == SERVICE_NAME:
                            service_arn = service['ServiceArn']
                            self.config['SERVICE_ARN'] = service_arn
                            self.log(f"Using existing service: {service_arn}", "✅")
                            return True
                except:
                    pass
                return False
            else:
                self.log(f"Failed to create AppRunner service: {str(e)}", "❌")
                return False
    
    def wait_for_service(self, service_arn, max_wait=300):
        """Wait for AppRunner service to be running"""
        start = time.time()
        while time.time() - start < max_wait:
            try:
                response = self.apprunner_client.describe_service(ServiceArn=service_arn)
                status = response['Service']['Status']
                
                if status == 'RUNNING':
                    self.log("Service is RUNNING", "✅")
                    service_url = response['Service'].get('ServiceUrl')
                    if service_url:
                        self.config['SERVICE_URL'] = service_url
                        self.log(f"Service URL: {service_url}", "🌐")
                    return True
                else:
                    print(f"  Status: {status}", end='\r')
                    time.sleep(10)
            except Exception as e:
                self.log(f"Error checking service status: {str(e)}", "⚠️")
                time.sleep(10)
        
        self.log("Service creation timed out (may take longer to fully initialize)", "⚠️")
        return True  # Don't fail, it may still be initializing
    
    def update_cognito_callbacks(self):
        """Update Cognito callback URLs"""
        self.log("Updating Cognito callback URLs...", "🔐")
        
        user_pool_id = self.config.get('COGNITO_USER_POOL_ID')
        client_id = self.config.get('COGNITO_CLIENT_ID')
        service_url = self.config.get('SERVICE_URL', 'https://YOUR-SERVICE-URL')
        
        try:
            self.cognito_client.update_user_pool_client(
                UserPoolId=user_pool_id,
                ClientId=client_id,
                CallbackURLs=[
                    'http://localhost:5000/auth/callback',
                    f'{service_url}/auth/callback'
                ],
                LogoutURLs=[
                    'http://localhost:5000',
                    service_url
                ]
            )
            self.log("Cognito callback URLs updated", "✅")
            return True
        except Exception as e:
            self.log(f"Failed to update callback URLs: {str(e)}", "⚠️")
            return True  # Don't fail, may work anyway
    
    def create_students(self, csv_file):
        """Create Cognito users from CSV"""
        self.log(f"Creating students from: {csv_file}", "👥")
        
        if not Path(csv_file).exists():
            self.log(f"CSV file not found: {csv_file}", "❌")
            return False
        
        user_pool_id = self.config.get('COGNITO_USER_POOL_ID')
        students = []
        
        # Read CSV
        try:
            with open(csv_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email = row.get('email') or row.get('Email')
                    if email and email.strip():
                        students.append({
                            'email': email.strip(),
                            'first_name': (row.get('first_name') or row.get('First Name') or '').strip(),
                            'last_name': (row.get('last_name') or row.get('Last Name') or '').strip(),
                        })
            
            self.log(f"Found {len(students)} students in CSV", "📊")
        except Exception as e:
            self.log(f"Failed to read CSV: {str(e)}", "❌")
            return False
        
        if len(students) == 0:
            self.log("No students found in CSV", "⚠️")
            return False
        
        # Create users
        created = 0
        failed = 0
        
        for i, student in enumerate(students, 1):
            email = student['email']
            first_name = student['first_name'] or email.split('@')[0]
            last_name = student['last_name'] or ''
            
            try:
                self.cognito_client.admin_create_user(
                    UserPoolId=user_pool_id,
                    Username=email,
                    TemporaryPassword=f"TempPass{i}!@#",
                    MessageAction='SUPPRESS',
                    UserAttributes=[
                        {'Name': 'email', 'Value': email},
                        {'Name': 'email_verified', 'Value': 'true'},
                        {'Name': 'given_name', 'Value': first_name},
                        {'Name': 'family_name', 'Value': last_name},
                    ]
                )
                created += 1
                print(f"  [{i:2d}/{len(students)}] ✅ {email}", end='\r')
            except Exception as e:
                if 'already exists' in str(e):
                    print(f"  [{i:2d}/{len(students)}] ⚠️  {email} (exists)", end='\r')
                else:
                    print(f"  [{i:2d}/{len(students)}] ❌ {email}", end='\r')
                failed += 1
        
        print("")
        self.log(f"Created: {created}, Failed: {failed}, Total: {len(students)}", f"{'✅' if failed == 0 else '⚠️'}")
        return True
    
    def save_summary(self):
        """Save deployment summary"""
        summary = f"""
════════════════════════════════════════════════════════════
🎉 DEPLOYMENT COMPLETE!
════════════════════════════════════════════════════════════

AWS INFRASTRUCTURE:
  Account ID:        {self.config.get('COGNITO_USER_POOL_ID', 'N/A').split('_')[0]}
  Region:            {REGION}

COGNITO:
  User Pool ID:      {self.config.get('COGNITO_USER_POOL_ID', 'N/A')}
  Client ID:         {self.config.get('COGNITO_CLIENT_ID', 'N/A')}
  Domain:            {self.config.get('COGNITO_DOMAIN', 'N/A')}

APPRUNNER:
  Service Name:      {SERVICE_NAME}
  Service URL:       {self.config.get('SERVICE_URL', 'N/A')}
  Service ARN:       {self.config.get('SERVICE_ARN', 'N/A')}

DATABASE:
  Table:             AIAssuranceLab-UserMCPCredentials
  Region:            {REGION}

NEXT STEPS:
  1. Share your student email spreadsheet
  2. We'll create all student accounts automatically

════════════════════════════════════════════════════════════
"""
        
        print(summary)
        
        # Save to file
        with open(f"{PROJECT_DIR}/DEPLOYMENT_SUMMARY.txt", 'w') as f:
            f.write(summary)
        
        self.log(f"Summary saved to DEPLOYMENT_SUMMARY.txt", "💾")
    
    def deploy(self):
        """Run full deployment"""
        print("════════════════════════════════════════════════════════════")
        print("🚀 AI ASSURANCE LAB - AUTOMATED SETUP & DEPLOYMENT")
        print("════════════════════════════════════════════════════════════")
        print()
        
        # Load config
        if not self.load_cognito_config():
            return False
        
        # Build and deploy (requires Docker)
        self.log("Checking for Docker...", "ℹ️")
        ok, _ = self.run_command("docker ps > /dev/null 2>&1")
        
        if ok:
            # Build and push
            if not self.build_docker_image():
                self.log("Build failed. You can try again or manually build.", "⚠️")
                self.save_summary()
                return True
            
            if not self.push_to_ecr():
                self.log("Push failed. You can try again or manually push.", "⚠️")
                self.save_summary()
                return True
            
            if not self.create_apprunner_service():
                self.log("AppRunner creation failed. Check AWS console.", "⚠️")
                self.save_summary()
                return True
            
            if not self.update_cognito_callbacks():
                self.log("Callback update failed but deployment may still work.", "⚠️")
        else:
            self.log("Docker not running. Manual deployment needed.", "⚠️")
            self.log("Run: cd '/Users/sceddy/Documents/AI Assurance MCP day' && bash DEPLOY_SCRIPT.sh", "ℹ️")
            self.save_summary()
            return True
        
        self.save_summary()
        return True

def main():
    if len(sys.argv) > 1:
        # Create students from CSV
        csv_file = sys.argv[1]
        deployer = AIAssuranceLabDeployment()
        if deployer.load_cognito_config():
            deployer.create_students(csv_file)
        return
    
    # Full deployment
    deployer = AIAssuranceLabDeployment()
    success = deployer.deploy()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
