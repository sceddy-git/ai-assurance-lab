"""
AI Assurance Lab - Flask application with user-configurable MCP connectivity.
Each student manages their own encrypted API credentials for ThousandEyes and Meraki.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlencode, parse_qs
from urllib.request import urlopen

from flask import Flask, render_template, session, request, redirect, url_for, jsonify
from flask_cors import CORS
import requests
import boto3

from dynamo_db import (
    save_user_credentials,
    get_user_credentials,
    test_te_connectivity,
    test_meraki_connectivity,
    update_connection_status,
    delete_user_credentials,
    DynamoDBError
)
from crypto import EncryptionError
from tool_handlers import (
    handle_thousandeyes_tool,
    handle_meraki_tool,
    get_available_tools
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

# AWS and Cognito configuration
COGNITO_DOMAIN = os.getenv('COGNITO_DOMAIN')
COGNITO_CLIENT_ID = os.getenv('COGNITO_CLIENT_ID')
COGNITO_CLIENT_SECRET = os.getenv('COGNITO_CLIENT_SECRET')
COGNITO_REGION = os.getenv('COGNITO_REGION', 'us-east-1')
APP_URL = os.getenv('APP_URL', 'http://localhost:5000')
BEDROCK_REGION = os.getenv('BEDROCK_REGION', 'us-east-1')

# Initialize Bedrock client
bedrock_client = boto3.client('bedrock-runtime', region_name=BEDROCK_REGION)


def login_required(f):
    """Decorator to require Cognito login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# Initialize Cognito client for user management
cognito_client = boto3.client('cognito-idp', region_name=COGNITO_REGION)

# ============================================================================
# Authentication Routes
# ============================================================================

@app.route('/login')
def login():
    """Redirect to Cognito login."""
    return redirect(
        f'https://{COGNITO_DOMAIN}/oauth2/authorize?'
        f'client_id={COGNITO_CLIENT_ID}&'
        f'response_type=code&'
        f'redirect_uri={APP_URL}/auth/callback&'
        f'scope=email+openid+profile'
    )


@app.route('/auth/callback')
def auth_callback():
    """Handle Cognito callback after login."""
    code = request.args.get('code')
    
    if not code:
        logger.warning("Auth callback received without code")
        return jsonify({'error': 'No authorization code received'}), 400
    
    try:
        # Exchange code for tokens
        token_url = f'https://{COGNITO_DOMAIN}/oauth2/token'
        token_data = {
            'grant_type': 'authorization_code',
            'client_id': COGNITO_CLIENT_ID,
            'client_secret': COGNITO_CLIENT_SECRET,
            'code': code,
            'redirect_uri': f'{APP_URL}/auth/callback'
        }
        
        token_response = requests.post(token_url, data=token_data, timeout=10)
        token_response.raise_for_status()
        
        tokens = token_response.json()
        id_token = tokens.get('id_token')
        
        if not id_token:
            logger.error("No ID token in Cognito response")
            return jsonify({'error': 'Failed to obtain ID token'}), 400
        
        # Decode ID token to get user info
        # Note: In production, validate the token signature
        import jwt
        try:
            decoded = jwt.decode(
                id_token,
                options={"verify_signature": False},
                algorithms=["RS256"]
            )
            user_email = decoded.get('email')
            
            if not user_email:
                logger.error("No email in ID token")
                return jsonify({'error': 'Email not found in token'}), 400
            
            # Store in session
            session['user_email'] = user_email
            session['access_token'] = tokens.get('access_token')
            session.permanent = True
            app.permanent_session_lifetime = timedelta(days=7)
            
            logger.info(f"User logged in: {user_email}")
            
            return redirect(url_for('lab'))
        
        except jwt.DecodeError as e:
            logger.error(f"Failed to decode ID token: {e}")
            return jsonify({'error': 'Failed to decode token'}), 400
    
    except requests.RequestException as e:
        logger.error(f"Cognito token exchange failed: {e}")
        return jsonify({'error': 'Authentication failed'}), 500


@app.route('/logout')
def logout():
    """Clear session and redirect to Cognito logout."""
    session.clear()
    return redirect(
        f'https://{COGNITO_DOMAIN}/logout?'
        f'client_id={COGNITO_CLIENT_ID}&'
        f'logout_uri={APP_URL}'
    )


# ============================================================================
# Credential Management Routes
# ============================================================================

@app.route('/credentials')
@login_required
def credentials_page():
    """Display MCP credential management UI."""
    return render_template('credentials.html', email=session.get('user_email'))


@app.route('/api/credentials', methods=['GET'])
@login_required
def get_credentials_status():
    """
    Get user's MCP credential status (no plaintext tokens).
    Returns configuration status and connection state.
    """
    try:
        email = session.get('user_email')
        credentials = get_user_credentials(email)
        
        return jsonify({
            "te_configured": bool(credentials.get('te_token')),
            "te_connected": credentials.get('te_connected', False),
            "meraki_configured": bool(credentials.get('meraki_token')),
            "meraki_connected": credentials.get('meraki_connected', False),
            "last_updated": credentials.get('updated_at')
        })
    
    except DynamoDBError as e:
        logger.error(f"DynamoDB error for {email}: {e}")
        return jsonify({'error': 'Failed to retrieve credentials'}), 500
    except Exception as e:
        logger.error(f"Unexpected error in get_credentials_status: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/credentials/add', methods=['POST'])
@login_required
def add_credential():
    """
    Add or update a user's MCP credential.
    Validates token format, encrypts, and stores in DynamoDB.
    """
    try:
        email = session.get('user_email')
        data = request.json
        service = data.get('service', '').lower()
        token = data.get('token', '').strip()
        
        if not service or not token:
            return jsonify({'error': 'service and token are required'}), 400
        
        if service not in ['thousandeyes', 'meraki']:
            return jsonify({'error': 'Unknown service'}), 400
        
        # Validate token format
        if service == 'thousandeyes':
            # ThousandEyes tokens are typically 32+ chars
            if len(token) < 10:
                return jsonify({'error': 'ThousandEyes token appears too short'}), 400
        
        elif service == 'meraki':
            # Meraki tokens are typically 32+ chars
            if len(token) < 20:
                return jsonify({'error': 'Meraki token appears too short'}), 400
        
        # Save credentials
        if service == 'thousandeyes':
            save_user_credentials(email, te_token=token)
        else:
            save_user_credentials(email, meraki_token=token)
        
        logger.info(f"Saved {service} credential for {email}")
        
        return jsonify({
            'status': 'success',
            'message': f'{service.capitalize()} credential saved'
        })
    
    except EncryptionError as e:
        logger.error(f"Encryption error for {email}: {e}")
        return jsonify({'error': 'Failed to encrypt credential'}), 500
    except DynamoDBError as e:
        logger.error(f"DynamoDB error for {email}: {e}")
        return jsonify({'error': 'Failed to save credential'}), 500
    except Exception as e:
        logger.error(f"Error in add_credential: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/credentials/test', methods=['POST'])
@login_required
def test_credential():
    """
    Test if a credential is valid by making a test API call.
    Updates connection status in DynamoDB.
    """
    try:
        email = session.get('user_email')
        data = request.json
        service = data.get('service', '').lower()
        
        if service not in ['thousandeyes', 'meraki']:
            return jsonify({'error': 'Unknown service'}), 400
        
        # Test connectivity
        if service == 'thousandeyes':
            result = test_te_connectivity(email)
        else:
            result = test_meraki_connectivity(email)
        
        # Update connection status
        is_valid = result.get('valid', False)
        update_connection_status(email, service, is_valid)
        
        if is_valid:
            logger.info(f"Connectivity test passed for {service} on {email}")
            return jsonify({
                'status': 'success',
                'connected': True,
                'message': f'{service.capitalize()} credential is valid'
            })
        else:
            error_msg = result.get('error', f'{service} credential test failed')
            logger.warning(f"Connectivity test failed for {service} on {email}: {error_msg}")
            return jsonify({
                'status': 'error',
                'connected': False,
                'message': error_msg
            }), 400
    
    except DynamoDBError as e:
        logger.error(f"DynamoDB error during credential test: {e}")
        return jsonify({'error': 'Failed to test credential'}), 500
    except Exception as e:
        logger.error(f"Error in test_credential: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/credentials/delete', methods=['POST'])
@login_required
def delete_credential():
    """
    Revoke a user's MCP credential for a service.
    """
    try:
        email = session.get('user_email')
        data = request.json
        service = data.get('service', '').lower()
        
        if service not in ['thousandeyes', 'meraki']:
            return jsonify({'error': 'Unknown service'}), 400
        
        delete_user_credentials(email, service)
        
        logger.info(f"Deleted {service} credential for {email}")
        
        return jsonify({
            'status': 'success',
            'message': f'{service.capitalize()} credential deleted'
        })
    
    except DynamoDBError as e:
        logger.error(f"DynamoDB error deleting credential: {e}")
        return jsonify({'error': 'Failed to delete credential'}), 500
    except Exception as e:
        logger.error(f"Error in delete_credential: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# Chat Route (with user credentials)
# ============================================================================

@app.route('/lab')
@login_required
def lab():
    """Display the main lab chat interface."""
    email = session.get('user_email')
    return render_template('lab.html', email=email)


@app.route('/guide')
@login_required
def guide():
    """Display the lab guide (rendered standalone, embedded via iframe in the lab sidebar)."""
    return render_template('guide.html')


@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """
    Chat with Claude using user's stored MCP credentials.
    Retrieves per-user tokens and only exposes tools for configured services.
    """
    try:
        email = session.get('user_email')
        data = request.json
        user_message = data.get('message', '')
        conversation_history = data.get('history', [])
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get user's stored credentials
        try:
            credentials = get_user_credentials(email)
        except DynamoDBError as e:
            logger.error(f"Failed to retrieve credentials for {email}: {e}")
            return jsonify({'error': 'Failed to retrieve your credentials'}), 500
        
        te_token = credentials.get('te_token')
        meraki_token = credentials.get('meraki_token')
        
        # Check which services are available
        available_tools = get_available_tools(
            te_enabled=bool(te_token),
            meraki_enabled=bool(meraki_token)
        )
        
        # Build messages for Claude
        messages = conversation_history + [
            {"role": "user", "content": user_message}
        ]
        
        # Call Bedrock Claude model
        try:
            response = bedrock_client.invoke_model(
                modelId='us.anthropic.claude-sonnet-4-5-20250929-v1:0',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2048,
                    "tools": available_tools,
                    "messages": messages
                })
            )
            
            result = json.loads(response['body'].read())
            content = result.get('content', [])
        
        except Exception as e:
            logger.error(f"Bedrock invocation failed: {e}")
            return jsonify({'error': 'Failed to invoke AI model'}), 500
        
        # Check if Claude made any tool calls
        tool_calls = [c for c in content if c.get('type') == 'tool_use']
        
        if tool_calls:
            tool_results = []
            
            for tool_call in tool_calls:
                tool_name = tool_call.get('name', '')
                tool_input = tool_call.get('input', {})
                tool_use_id = tool_call.get('id', '')
                
                # Route to appropriate handler using user's token
                try:
                    if tool_name.startswith('get_') or tool_name in ['list_organizations', 'list_networks', 'list_devices', 'list_device', 'list_network_clients']:
                        # Determine if ThousandEyes or Meraki
                        if any(x in tool_name for x in ['account', 'agents', 'alerts', 'alert_rules', 'tests', 'test_results', 'outages', 'endpoint']):
                            tool_result = handle_thousandeyes_tool(tool_name, tool_input, te_token)
                        else:
                            tool_result = handle_meraki_tool(tool_name, tool_input, meraki_token)
                    else:
                        tool_result = {"error": f"Unknown tool: {tool_name}"}
                
                except Exception as e:
                    logger.error(f"Tool execution error for {tool_name}: {e}")
                    tool_result = {"error": f"Tool execution failed: {str(e)}"}
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps(tool_result) if not isinstance(tool_result, str) else tool_result
                })
            
            # Continue conversation with tool results
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": tool_results})
            
            try:
                final_response = bedrock_client.invoke_model(
                    modelId='us.anthropic.claude-sonnet-4-5-20250929-v1:0',
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 2048,
                        "messages": messages
                    })
                )
                
                final_result = json.loads(final_response['body'].read())
                assistant_message = final_result['content'][0]['text']
            
            except Exception as e:
                logger.error(f"Final response generation failed: {e}")
                return jsonify({'error': 'Failed to generate final response'}), 500
        
        else:
            # No tool calls, just return the response
            assistant_message = next(
                (c.get('text', '') for c in content if c.get('type') == 'text'),
                'No response generated'
            )
        
        return jsonify({
            "response": assistant_message,
            "tools_used": len(tool_calls) if tool_calls else 0,
            "te_available": bool(te_token),
            "meraki_available": bool(meraki_token)
        })
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# Student Management Routes (Proctor Portal)
# ============================================================================

@app.route('/admin/students')
@login_required
def admin_students():
    """Proctor portal for managing students."""
    # Only allow if user is a proctor (hardcoded for now, could use DynamoDB)
    user_email = session.get('user_email', '')
    proctor_emails = os.getenv('PROCTOR_EMAILS', 'admin@example.com').split(',')
    
    if user_email not in proctor_emails:
        return jsonify({'error': 'Access denied - proctor access required'}), 403
    
    return render_template('admin_students.html', email=user_email)


@app.route('/api/admin/students/upload', methods=['POST'])
@login_required
def upload_students_csv():
    """Upload and create students from CSV file."""
    user_email = session.get('user_email', '')
    proctor_emails = os.getenv('PROCTOR_EMAILS', 'admin@example.com').split(',')
    
    if user_email not in proctor_emails:
        return jsonify({'error': 'Access denied'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'File must be CSV format'}), 400
    
    try:
        # Read CSV
        import io
        import csv
        
        stream = io.StringIO(file.stream.read().decode('UTF-8'))
        reader = csv.DictReader(stream)
        
        created = 0
        failed = 0
        errors = []
        
        for row in reader:
            email = row.get('email', '').strip()
            first_name = row.get('first_name', '').strip()
            last_name = row.get('last_name', '').strip()
            
            if not email:
                failed += 1
                errors.append('Empty email in row')
                continue
            
            try:
                # Generate temporary password
                import secrets
                temp_password = secrets.token_urlsafe(12)
                
                # Create user in Cognito
                cognito_client.admin_create_user(
                    UserPoolId=os.getenv('COGNITO_USER_POOL_ID'),
                    Username=email,
                    TemporaryPassword=temp_password,
                    UserAttributes=[
                        {'Name': 'email', 'Value': email},
                        {'Name': 'email_verified', 'Value': 'true'},
                        {'Name': 'given_name', 'Value': first_name},
                        {'Name': 'family_name', 'Value': last_name}
                    ],
                    MessageAction='SUPPRESS'
                )
                created += 1
                
            except cognito_client.exceptions.UsernameExistsException:
                failed += 1
                errors.append(f'{email}: User already exists')
            except Exception as e:
                failed += 1
                errors.append(f'{email}: {str(e)}')
        
        return jsonify({
            'status': 'success',
            'created': created,
            'failed': failed,
            'errors': errors[:10]  # Return first 10 errors
        })
    
    except Exception as e:
        logger.error(f"Error uploading students: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/students/list', methods=['GET'])
@login_required
def list_students():
    """List all students in Cognito."""
    user_email = session.get('user_email', '')
    proctor_emails = os.getenv('PROCTOR_EMAILS', 'admin@example.com').split(',')
    
    if user_email not in proctor_emails:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        response = cognito_client.list_users(
            UserPoolId=os.getenv('COGNITO_USER_POOL_ID'),
            Limit=100
        )
        
        students = []
        for user in response.get('Users', []):
            email = next((attr['Value'] for attr in user['Attributes'] if attr['Name'] == 'email'), '')
            first_name = next((attr['Value'] for attr in user['Attributes'] if attr['Name'] == 'given_name'), '')
            last_name = next((attr['Value'] for attr in user['Attributes'] if attr['Name'] == 'family_name'), '')
            
            students.append({
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'created': str(user['UserCreateDate']),
                'status': user['UserStatus']
            })
        
        return jsonify({
            'status': 'success',
            'count': len(students),
            'students': students
        })
    
    except Exception as e:
        logger.error(f"Error listing students: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/students/delete-all', methods=['POST'])
@login_required
def delete_all_students():
    """Delete all students from Cognito."""
    user_email = session.get('user_email', '')
    proctor_emails = os.getenv('PROCTOR_EMAILS', 'admin@example.com').split(',')
    
    if user_email not in proctor_emails:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        response = cognito_client.list_users(
            UserPoolId=os.getenv('COGNITO_USER_POOL_ID'),
            Limit=100
        )
        
        deleted = 0
        for user in response.get('Users', []):
            try:
                cognito_client.admin_delete_user(
                    UserPoolId=os.getenv('COGNITO_USER_POOL_ID'),
                    Username=user['Username']
                )
                deleted += 1
            except Exception as e:
                logger.warning(f"Failed to delete user {user['Username']}: {str(e)}")
        
        return jsonify({
            'status': 'success',
            'deleted': deleted
        })
    
    except Exception as e:
        logger.error(f"Error deleting students: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# Settings/Administration Routes
# ============================================================================

@app.route('/admin/settings')
@login_required
def admin_settings():
    """Settings and administration page for proctors."""
    user_email = session.get('user_email', '')
    proctor_emails = os.getenv('PROCTOR_EMAILS', 'admin@example.com').split(',')
    
    if user_email not in proctor_emails:
        return jsonify({'error': 'Access denied - proctor access required'}), 403
    
    return render_template('admin_settings.html', email=user_email)


@app.route('/api/admin/settings/config', methods=['GET'])
@login_required
def get_settings():
    """Get current configuration (sensitive values redacted)."""
    user_email = session.get('user_email', '')
    proctor_emails = os.getenv('PROCTOR_EMAILS', 'admin@example.com').split(',')
    
    if user_email not in proctor_emails:
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify({
        'cognito_domain': os.getenv('COGNITO_DOMAIN', ''),
        'cognito_client_id': os.getenv('COGNITO_CLIENT_ID', ''),
        'cognito_region': os.getenv('COGNITO_REGION', 'us-east-1'),
        'app_url': os.getenv('APP_URL', ''),
        'bedrock_region': os.getenv('BEDROCK_REGION', 'us-east-1'),
        'dynamodb_region': os.getenv('DYNAMODB_REGION', 'us-east-1'),
        'dynamodb_table': os.getenv('DYNAMODB_TABLE', ''),
        'proctor_emails': os.getenv('PROCTOR_EMAILS', ''),
        'encryption_key_set': bool(os.getenv('ENCRYPTION_KEY')),
        'flask_env': os.getenv('FLASK_ENV', 'development'),
        'has_cognito_secret': bool(os.getenv('COGNITO_CLIENT_SECRET'))
    })


@app.route('/api/admin/settings/update', methods=['POST'])
@login_required
def update_settings():
    """Update configuration settings."""
    user_email = session.get('user_email', '')
    proctor_emails = os.getenv('PROCTOR_EMAILS', 'admin@example.com').split(',')
    
    if user_email not in proctor_emails:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.json
    
    try:
        # Update .env file
        env_file = '.env'
        env_content = {}
        
        # Read existing
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env_content[key] = value
        
        # Update with new values
        if 'cognito_domain' in data:
            env_content['COGNITO_DOMAIN'] = data['cognito_domain']
        if 'cognito_client_id' in data:
            env_content['COGNITO_CLIENT_ID'] = data['cognito_client_id']
        if 'cognito_client_secret' in data:
            env_content['COGNITO_CLIENT_SECRET'] = data['cognito_client_secret']
        if 'proctor_emails' in data:
            env_content['PROCTOR_EMAILS'] = data['proctor_emails']
        if 'encryption_key' in data:
            env_content['ENCRYPTION_KEY'] = data['encryption_key']
        
        # Write back
        with open(env_file, 'w') as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")
        
        logger.info(f"Settings updated by {user_email}")
        
        return jsonify({
            'status': 'success',
            'message': 'Settings saved. Flask will need to restart for changes to take effect.'
        })
    
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/system/status', methods=['GET'])
@login_required
def system_status():
    """Get system status."""
    user_email = session.get('user_email', '')
    proctor_emails = os.getenv('PROCTOR_EMAILS', 'admin@example.com').split(',')
    
    if user_email not in proctor_emails:
        return jsonify({'error': 'Access denied'}), 403
    
    import psutil
    import subprocess
    
    try:
        # Get CPU and memory
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Get Flask service status
        result = subprocess.run(
            ['systemctl', 'is-active', 'flask-app'],
            capture_output=True,
            text=True,
            timeout=5
        )
        flask_status = result.stdout.strip()
        
        # Get last restart time
        result = subprocess.run(
            ['systemctl', 'show', 'flask-app', '-p', 'StateChangeTimestamp'],
            capture_output=True,
            text=True,
            timeout=5
        )
        restart_time = result.stdout.strip()
        
        return jsonify({
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_mb': memory.used // (1024 ** 2),
            'memory_total_mb': memory.total // (1024 ** 2),
            'flask_status': flask_status,
            'restart_time': restart_time
        })
    
    except Exception as e:
        logger.warning(f"Could not get system status: {str(e)}")
        return jsonify({
            'error': 'Could not retrieve system status',
            'details': str(e)
        }), 500


@app.route('/api/admin/system/restart', methods=['POST'])
@login_required
def restart_flask():
    """Restart Flask application."""
    user_email = session.get('user_email', '')
    proctor_emails = os.getenv('PROCTOR_EMAILS', 'admin@example.com').split(',')
    
    if user_email not in proctor_emails:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        import subprocess
        
        logger.info(f"Flask restart requested by {user_email}")
        
        subprocess.run(
            ['sudo', 'systemctl', 'restart', 'flask-app'],
            timeout=10
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Flask is restarting. Page will reload in 5 seconds.'
        })
    
    except Exception as e:
        logger.error(f"Error restarting Flask: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/system/logs', methods=['GET'])
@login_required
def get_logs():
    """Get recent Flask logs."""
    user_email = session.get('user_email', '')
    proctor_emails = os.getenv('PROCTOR_EMAILS', 'admin@example.com').split(',')
    
    if user_email not in proctor_emails:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        import subprocess
        
        result = subprocess.run(
            ['sudo', 'journalctl', '-u', 'flask-app', '-n', '100', '--no-pager'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        logs = result.stdout.split('\n')
        
        return jsonify({
            'status': 'success',
            'logs': logs
        })
    
    except Exception as e:
        logger.warning(f"Could not retrieve logs: {str(e)}")
        return jsonify({
            'logs': ['Could not retrieve logs. Make sure you have sudo access.']
        })


@app.route('/api/admin/deploy/git-pull', methods=['POST'])
@login_required
def git_pull():
    """Pull latest code from git."""
    user_email = session.get('user_email', '')
    proctor_emails = os.getenv('PROCTOR_EMAILS', 'admin@example.com').split(',')
    
    if user_email not in proctor_emails:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        import subprocess
        
        logger.info(f"Git pull requested by {user_email}")
        
        result = subprocess.run(
            ['git', 'pull', 'origin', 'main'],
            capture_output=True,
            text=True,
            timeout=30,
            cwd='/home/ubuntu/ai-assurance-lab'
        )
        
        # Restart Flask
        subprocess.run(
            ['sudo', 'systemctl', 'restart', 'flask-app'],
            timeout=10
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Code updated and Flask restarted',
            'output': result.stdout
        })
    
    except Exception as e:
        logger.error(f"Error pulling code: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# Static Pages
# ============================================================================

@app.route('/')
def index():
    """Home page - redirect to login if not authenticated."""
    if 'user_email' in session:
        return redirect(url_for('lab'))
    return redirect(url_for('login'))


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    logger.warning(f"404 error: {request.path}")
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    logger.error(f"500 error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # Check for required environment variables
    required_vars = [
        'COGNITO_DOMAIN',
        'COGNITO_CLIENT_ID',
        'COGNITO_CLIENT_SECRET',
        'ENCRYPTION_KEY'
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please set these in .env file")
    
    logger.info(f"Starting Flask app on {APP_URL}")
    app.run(debug=os.getenv('FLASK_ENV') == 'development', host='0.0.0.0', port=5000)
