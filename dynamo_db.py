"""
DynamoDB operations for managing user MCP credentials.
Handles encryption/decryption, connectivity testing, and credential lifecycle.
"""

import os
import json
import logging
import time
from typing import Dict, Optional, Tuple
import boto3
from botocore.exceptions import ClientError

from crypto import encrypt_token, decrypt_token, EncryptionError
from mcp_client import list_mcp_tools, MCPClientError, THOUSANDEYES_MCP_URL, MERAKI_MCP_URL

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
    meraki_token: Optional[str] = None,
    meraki_org_id: Optional[str] = None,
    splunk_url: Optional[str] = None,
    splunk_token: Optional[str] = None
) -> bool:
    """
    Save or update a user's encrypted MCP credentials.
    
    Args:
        email: User's email address (partition key)
        te_token: ThousandEyes API token (optional, only update if provided)
        meraki_token: Meraki API token (optional, only update if provided)
        meraki_org_id: Meraki Organization ID (optional). The Meraki MCP server's tools
            require an org ID for almost every call, and there's no "list my
            organizations" shortcut in its semantic_search/execute_api pair, so we
            store this once and inject it into the chat system prompt instead of
            making the student paste it into every message.
        splunk_url: Splunk MCP server URL - varies per student/facilitator (optional)
        splunk_token: Splunk MCP server auth token/API key, if the server requires one (optional)
        
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
        
        # Prepare update expression and values (single SET clause, comma-separated assignments)
        set_clauses = ["updated_at = :updated_at"]
        expr_values = {":updated_at": current_time}
        
        # Add new credentials to the update
        if te_token:
            try:
                encrypted_te = encrypt_token(te_token, email)
                set_clauses.append("thousandeyes_token = :te_token")
                expr_values[":te_token"] = encrypted_te
            except EncryptionError as e:
                logger.error(f"Failed to encrypt ThousandEyes token for {email}: {e}")
                raise DynamoDBError(f"Failed to encrypt ThousandEyes token: {str(e)}")
        
        if meraki_token:
            try:
                encrypted_meraki = encrypt_token(meraki_token, email)
                set_clauses.append("meraki_token = :meraki_token")
                expr_values[":meraki_token"] = encrypted_meraki
            except EncryptionError as e:
                logger.error(f"Failed to encrypt Meraki token for {email}: {e}")
                raise DynamoDBError(f"Failed to encrypt Meraki token: {str(e)}")
        
        # Org ID isn't a secret, so store it in plain text alongside the encrypted token.
        if meraki_org_id:
            set_clauses.append("meraki_org_id = :meraki_org_id")
            expr_values[":meraki_org_id"] = meraki_org_id
        
        # Splunk's MCP server URL differs per student (local laptop, tunnel, or
        # facilitator-hosted), so unlike ThousandEyes/Meraki it's part of what
        # each user configures. The URL isn't a secret, so store it in plain
        # text; the token/API key (if the server requires one) is encrypted.
        if splunk_url:
            set_clauses.append("splunk_mcp_url = :splunk_url")
            expr_values[":splunk_url"] = splunk_url
        
        if splunk_token:
            try:
                encrypted_splunk = encrypt_token(splunk_token, email)
                set_clauses.append("splunk_token = :splunk_token")
                expr_values[":splunk_token"] = encrypted_splunk
            except EncryptionError as e:
                logger.error(f"Failed to encrypt Splunk token for {email}: {e}")
                raise DynamoDBError(f"Failed to encrypt Splunk token: {str(e)}")
        
        # Set created_at if this is the first save
        set_clauses.insert(0, "#created = if_not_exists(#created, :created_at)")
        expr_values[":created_at"] = current_time
        update_expr = "SET " + ", ".join(set_clauses)
        
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
                "meraki_org_id": None,
                "splunk_url": None,
                "splunk_token": None,
                "te_connected": False,
                "meraki_connected": False,
                "splunk_connected": False,
                "created_at": None,
                "updated_at": None
            }
        
        item = response['Item']
        result = {
            "te_connected": item.get("te_connected", False),
            "meraki_connected": item.get("meraki_connected", False),
            "meraki_org_id": item.get("meraki_org_id"),
            "splunk_connected": item.get("splunk_connected", False),
            "splunk_url": item.get("splunk_mcp_url"),
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
        
        try:
            if "splunk_token" in item and item["splunk_token"]:
                result["splunk_token"] = decrypt_token(item["splunk_token"], email)
            else:
                result["splunk_token"] = None
        except EncryptionError as e:
            logger.warning(f"Failed to decrypt Splunk token for {email}: {e}")
            result["splunk_token"] = None
        
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
    Test ThousandEyes connectivity by listing tools on the real ThousandEyes
    MCP server (https://api.thousandeyes.com/mcp) with the user's token.
    This matches exactly what the chat feature uses, so a passing test here
    guarantees the chat's tool-calling will work.
    
    Args:
        email: User's email address
        
    Returns:
        Dict with keys: valid (bool), error (str, optional), tool_count (int, optional)
        
    Raises:
        DynamoDBError: If credential retrieval fails
    """
    try:
        credentials = get_user_credentials(email)
        token = credentials.get("te_token")
        
        if not token:
            return {"valid": False, "error": "ThousandEyes token not configured"}
        
        try:
            tools = list_mcp_tools(THOUSANDEYES_MCP_URL, token)
            logger.info(f"ThousandEyes MCP connectivity test passed for {email} ({len(tools)} tools)")
            return {"valid": True, "tool_count": len(tools)}
        except MCPClientError as e:
            error_str = str(e)
            if "401" in error_str:
                logger.warning(f"ThousandEyes token invalid for {email}")
                return {"valid": False, "error": "Invalid or expired ThousandEyes token"}
            elif "403" in error_str:
                return {"valid": False, "error": "ThousandEyes token lacks the API Access permission required for the MCP server"}
            else:
                logger.error(f"ThousandEyes MCP connectivity test error for {email}: {e}")
                return {"valid": False, "error": f"ThousandEyes MCP server error: {error_str}"}
    
    except DynamoDBError as e:
        raise DynamoDBError(f"Failed to retrieve credentials: {str(e)}")


def test_meraki_connectivity(email: str) -> Dict:
    """
    Test Meraki connectivity by listing tools on the real Meraki MCP server
    (https://mcp.meraki.com/mcp) with the user's Dashboard API key.
    This matches exactly what the chat feature uses, so a passing test here
    guarantees the chat's tool-calling will work.
    
    Args:
        email: User's email address
        
    Returns:
        Dict with keys: valid (bool), error (str, optional), tool_count (int, optional)
        
    Raises:
        DynamoDBError: If credential retrieval fails
    """
    try:
        credentials = get_user_credentials(email)
        token = credentials.get("meraki_token")
        
        if not token:
            return {"valid": False, "error": "Meraki token not configured"}
        
        try:
            tools = list_mcp_tools(MERAKI_MCP_URL, token)
            logger.info(f"Meraki MCP connectivity test passed for {email} ({len(tools)} tools)")
            return {"valid": True, "tool_count": len(tools)}
        except MCPClientError as e:
            error_str = str(e)
            if "401" in error_str:
                logger.warning(f"Meraki token invalid for {email}")
                return {"valid": False, "error": "Invalid or expired Meraki Dashboard API key"}
            elif "403" in error_str:
                return {"valid": False, "error": "Meraki API key lacks required permissions"}
            else:
                logger.error(f"Meraki MCP connectivity test error for {email}: {e}")
                return {"valid": False, "error": f"Meraki MCP server error: {error_str}"}
    
    except DynamoDBError as e:
        raise DynamoDBError(f"Failed to retrieve credentials: {str(e)}")


def test_splunk_connectivity(email: str) -> Dict:
    """
    Test connectivity to the user's own Splunk MCP server. Unlike ThousandEyes
    and Meraki (fixed, Cisco-hosted URLs), each student's Splunk MCP server
    lives at a different URL - their own laptop (via a tunnel), or a shared
    host the facilitator provides. The auth token/API key is optional since
    some self-hosted servers don't require one.
    
    Args:
        email: User's email address
        
    Returns:
        Dict with keys: valid (bool), error (str, optional), tool_count (int, optional)
        
    Raises:
        DynamoDBError: If credential retrieval fails
    """
    try:
        credentials = get_user_credentials(email)
        url = credentials.get("splunk_url")
        token = credentials.get("splunk_token")
        
        if not url:
            return {"valid": False, "error": "Splunk MCP server URL not configured"}
        
        try:
            tools = list_mcp_tools(url, token, require_token=False)
            logger.info(f"Splunk MCP connectivity test passed for {email} ({len(tools)} tools)")
            return {"valid": True, "tool_count": len(tools)}
        except MCPClientError as e:
            error_str = str(e)
            if "401" in error_str or "403" in error_str:
                return {"valid": False, "error": "Splunk MCP server rejected the auth token/API key"}
            else:
                logger.error(f"Splunk MCP connectivity test error for {email}: {e}")
                return {"valid": False, "error": f"Could not reach Splunk MCP server: {error_str}"}
    
    except DynamoDBError as e:
        raise DynamoDBError(f"Failed to retrieve credentials: {str(e)}")


def update_connection_status(email: str, service: str, connected: bool) -> bool:
    """
    Update the connection status for a service.
    
    Args:
        email: User's email address
        service: Service name ('thousandeyes', 'meraki', or 'splunk')
        connected: True if connected, False if disconnected
        
    Returns:
        bool: True if successful
        
    Raises:
        DynamoDBError: If update fails
    """
    if service not in ["thousandeyes", "meraki", "splunk"]:
        raise DynamoDBError(f"Unknown service: {service}")
    
    if not email:
        raise DynamoDBError("Email is required")
    
    try:
        table = get_table()
        
        attr_name = {
            "thousandeyes": "te_connected",
            "meraki": "meraki_connected",
            "splunk": "splunk_connected"
        }[service]
        
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
        service: Service name ('thousandeyes', 'meraki', or 'splunk')
        
    Returns:
        bool: True if successful
        
    Raises:
        DynamoDBError: If delete fails
    """
    if service not in ["thousandeyes", "meraki", "splunk"]:
        raise DynamoDBError(f"Unknown service: {service}")
    
    if not email:
        raise DynamoDBError("Email is required")
    
    try:
        table = get_table()
        
        if service == "thousandeyes":
            remove_attrs = ["thousandeyes_token"]
            status_attr = "te_connected"
        elif service == "meraki":
            remove_attrs = ["meraki_token", "meraki_org_id"]
            status_attr = "meraki_connected"
        else:
            remove_attrs = ["splunk_token", "splunk_mcp_url"]
            status_attr = "splunk_connected"
        
        remove_expr = "REMOVE " + ", ".join(remove_attrs)
        
        table.update_item(
            Key={"email": email},
            UpdateExpression=f"{remove_expr} SET {status_attr} = :false, updated_at = :updated_at",
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
