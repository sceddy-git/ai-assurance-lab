"""
DynamoDB operations for managing user MCP credentials.
Handles encryption/decryption, connectivity testing, and credential lifecycle.
"""

import os
import json
import logging
import time
import requests
from typing import Dict, Optional, Tuple
import boto3
from botocore.exceptions import ClientError

from crypto import encrypt_token, decrypt_token, EncryptionError

logger = logging.getLogger(__name__)

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb', region_name=os.getenv('DYNAMODB_REGION', 'us-east-1'))
table_name = os.getenv('DYNAMODB_TABLE', 'AIAssuranceLab-UserMCPCredentials')


def get_table():
    """Get the DynamoDB table resource."""
    try:
        return dynamodb.Table(table_name)
    except Exception as e:
        logger.error(f"Failed to get DynamoDB table: {e}")
        raise


class DynamoDBError(Exception):
    """Custom exception for DynamoDB operations."""
    pass


def save_user_credentials(
    email: str,
    te_token: Optional[str] = None,
    meraki_token: Optional[str] = None
) -> bool:
    """
    Save or update a user's encrypted MCP credentials.
    
    Args:
        email: User's email address (partition key)
        te_token: ThousandEyes API token (optional, only update if provided)
        meraki_token: Meraki API token (optional, only update if provided)
        
    Returns:
        bool: True if successful
        
    Raises:
        DynamoDBError: If save operation fails
    """
    if not email:
        raise DynamoDBError("Email is required")
    
    try:
        table = get_table()
        current_time = int(time.time())
        
        # Prepare update expression and values
        update_expr = "SET updated_at = :updated_at"
        expr_values = {":updated_at": current_time}
        
        # Add new credentials to the update
        if te_token:
            try:
                encrypted_te = encrypt_token(te_token, email)
                update_expr += ", thousandeyes_token = :te_token"
                expr_values[":te_token"] = encrypted_te
            except EncryptionError as e:
                logger.error(f"Failed to encrypt ThousandEyes token for {email}: {e}")
                raise DynamoDBError(f"Failed to encrypt ThousandEyes token: {str(e)}")
        
        if meraki_token:
            try:
                encrypted_meraki = encrypt_token(meraki_token, email)
                update_expr += ", meraki_token = :meraki_token"
                expr_values[":meraki_token"] = encrypted_meraki
            except EncryptionError as e:
                logger.error(f"Failed to encrypt Meraki token for {email}: {e}")
                raise DynamoDBError(f"Failed to encrypt Meraki token: {str(e)}")
        
        # Set created_at if this is the first save
        update_expr = "SET #created = if_not_exists(#created, :created_at), " + update_expr
        expr_values[":created_at"] = current_time
        
        # Use AttributeNamePlaceholder to avoid conflicts with reserved words
        attr_names = {"#created": "created_at"}
        
        table.update_item(
            Key={"email": email},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=attr_names
        )
        
        logger.info(f"Successfully saved credentials for {email}")
        return True
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"DynamoDB error for {email}: {error_code} - {e}")
        raise DynamoDBError(f"DynamoDB error: {error_code}")
    except DynamoDBError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error saving credentials for {email}: {e}")
        raise DynamoDBError(f"Failed to save credentials: {str(e)}")


def get_user_credentials(email: str) -> Dict:
    """
    Retrieve and decrypt a user's MCP credentials.
    Returns empty dict if user has no credentials stored.
    
    Args:
        email: User's email address
        
    Returns:
        Dict with keys: te_token, meraki_token, te_connected, meraki_connected, created_at, updated_at
        
    Raises:
        DynamoDBError: If retrieval fails
    """
    if not email:
        raise DynamoDBError("Email is required")
    
    try:
        table = get_table()
        response = table.get_item(Key={"email": email})
        
        if 'Item' not in response:
            # User has no credentials yet
            return {
                "te_token": None,
                "meraki_token": None,
                "te_connected": False,
                "meraki_connected": False,
                "created_at": None,
                "updated_at": None
            }
        
        item = response['Item']
        result = {
            "te_connected": item.get("te_connected", False),
            "meraki_connected": item.get("meraki_connected", False),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at")
        }
        
        # Decrypt tokens
        try:
            if "thousandeyes_token" in item and item["thousandeyes_token"]:
                result["te_token"] = decrypt_token(item["thousandeyes_token"], email)
            else:
                result["te_token"] = None
        except EncryptionError as e:
            logger.warning(f"Failed to decrypt ThousandEyes token for {email}: {e}")
            result["te_token"] = None
        
        try:
            if "meraki_token" in item and item["meraki_token"]:
                result["meraki_token"] = decrypt_token(item["meraki_token"], email)
            else:
                result["meraki_token"] = None
        except EncryptionError as e:
            logger.warning(f"Failed to decrypt Meraki token for {email}: {e}")
            result["meraki_token"] = None
        
        return result
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"DynamoDB error retrieving credentials for {email}: {error_code}")
        raise DynamoDBError(f"DynamoDB error: {error_code}")
    except DynamoDBError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving credentials for {email}: {e}")
        raise DynamoDBError(f"Failed to retrieve credentials: {str(e)}")


def test_te_connectivity(email: str) -> Dict:
    """
    Test ThousandEyes API connectivity with user's token.
    
    Args:
        email: User's email address
        
    Returns:
        Dict with keys: valid (bool), error (str, optional), account_info (dict, optional)
        
    Raises:
        DynamoDBError: If credential retrieval fails
    """
    try:
        credentials = get_user_credentials(email)
        token = credentials.get("te_token")
        
        if not token:
            return {"valid": False, "error": "ThousandEyes token not configured"}
        
        # Test API call: Get account information
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        url = "https://api.thousandeyes.com/v6/account"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"ThousandEyes connectivity test passed for {email}")
                return {
                    "valid": True,
                    "account_info": response.json()
                }
            elif response.status_code == 401:
                logger.warning(f"ThousandEyes token invalid for {email}")
                return {"valid": False, "error": "Invalid or expired ThousandEyes token"}
            elif response.status_code == 403:
                return {"valid": False, "error": "ThousandEyes token lacks required permissions"}
            else:
                return {"valid": False, "error": f"ThousandEyes API returned {response.status_code}"}
        
        except requests.exceptions.Timeout:
            return {"valid": False, "error": "ThousandEyes API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"valid": False, "error": "Unable to connect to ThousandEyes API"}
        except Exception as e:
            logger.error(f"ThousandEyes connectivity test error for {email}: {e}")
            return {"valid": False, "error": f"Test failed: {type(e).__name__}"}
    
    except DynamoDBError as e:
        raise DynamoDBError(f"Failed to retrieve credentials: {str(e)}")


def test_meraki_connectivity(email: str) -> Dict:
    """
    Test Meraki API connectivity with user's token.
    
    Args:
        email: User's email address
        
    Returns:
        Dict with keys: valid (bool), error (str, optional), organizations (list, optional)
        
    Raises:
        DynamoDBError: If credential retrieval fails
    """
    try:
        credentials = get_user_credentials(email)
        token = credentials.get("meraki_token")
        
        if not token:
            return {"valid": False, "error": "Meraki token not configured"}
        
        # Test API call: Get organizations
        headers = {
            "X-Cisco-Meraki-API-Key": token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        url = "https://api.meraki.com/api/v1/organizations"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                orgs = response.json()
                logger.info(f"Meraki connectivity test passed for {email}")
                return {
                    "valid": True,
                    "organizations": orgs if isinstance(orgs, list) else []
                }
            elif response.status_code == 401:
                logger.warning(f"Meraki token invalid for {email}")
                return {"valid": False, "error": "Invalid or expired Meraki token"}
            elif response.status_code == 403:
                return {"valid": False, "error": "Meraki token lacks required permissions"}
            else:
                return {"valid": False, "error": f"Meraki API returned {response.status_code}"}
        
        except requests.exceptions.Timeout:
            return {"valid": False, "error": "Meraki API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"valid": False, "error": "Unable to connect to Meraki API"}
        except Exception as e:
            logger.error(f"Meraki connectivity test error for {email}: {e}")
            return {"valid": False, "error": f"Test failed: {type(e).__name__}"}
    
    except DynamoDBError as e:
        raise DynamoDBError(f"Failed to retrieve credentials: {str(e)}")


def update_connection_status(email: str, service: str, connected: bool) -> bool:
    """
    Update the connection status for a service.
    
    Args:
        email: User's email address
        service: Service name ('thousandeyes' or 'meraki')
        connected: True if connected, False if disconnected
        
    Returns:
        bool: True if successful
        
    Raises:
        DynamoDBError: If update fails
    """
    if service not in ["thousandeyes", "meraki"]:
        raise DynamoDBError(f"Unknown service: {service}")
    
    if not email:
        raise DynamoDBError("Email is required")
    
    try:
        table = get_table()
        
        if service == "thousandeyes":
            attr_name = "te_connected"
        else:
            attr_name = "meraki_connected"
        
        table.update_item(
            Key={"email": email},
            UpdateExpression=f"SET {attr_name} = :status, updated_at = :updated_at",
            ExpressionAttributeValues={
                ":status": connected,
                ":updated_at": int(time.time())
            }
        )
        
        logger.info(f"Updated {service} connection status to {connected} for {email}")
        return True
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"DynamoDB error updating status for {email}: {error_code}")
        raise DynamoDBError(f"DynamoDB error: {error_code}")
    except Exception as e:
        logger.error(f"Unexpected error updating status for {email}: {e}")
        raise DynamoDBError(f"Failed to update status: {str(e)}")


def delete_user_credentials(email: str, service: str) -> bool:
    """
    Delete a user's credential for a specific service.
    
    Args:
        email: User's email address
        service: Service name ('thousandeyes' or 'meraki')
        
    Returns:
        bool: True if successful
        
    Raises:
        DynamoDBError: If delete fails
    """
    if service not in ["thousandeyes", "meraki"]:
        raise DynamoDBError(f"Unknown service: {service}")
    
    if not email:
        raise DynamoDBError("Email is required")
    
    try:
        table = get_table()
        
        if service == "thousandeyes":
            attr_name = "thousandeyes_token"
            status_attr = "te_connected"
        else:
            attr_name = "meraki_token"
            status_attr = "meraki_connected"
        
        table.update_item(
            Key={"email": email},
            UpdateExpression=f"REMOVE {attr_name} SET {status_attr} = :false, updated_at = :updated_at",
            ExpressionAttributeValues={
                ":false": False,
                ":updated_at": int(time.time())
            }
        )
        
        logger.info(f"Deleted {service} credential for {email}")
        return True
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"DynamoDB error deleting credential for {email}: {error_code}")
        raise DynamoDBError(f"DynamoDB error: {error_code}")
    except Exception as e:
        logger.error(f"Unexpected error deleting credential for {email}: {e}")
        raise DynamoDBError(f"Failed to delete credential: {str(e)}")
