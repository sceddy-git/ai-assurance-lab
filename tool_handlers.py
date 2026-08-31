"""
MCP tool handlers for ThousandEyes and Meraki API calls.
Executes tools on behalf of Claude using user-provided API tokens.
"""

import logging
import json
import requests
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ToolError(Exception):
    """Custom exception for tool execution errors."""
    pass


def handle_thousandeyes_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    token: str
) -> Dict[str, Any]:
    """
    Execute a ThousandEyes API tool call using user's token.
    
    Args:
        tool_name: Name of the tool (e.g., 'get_account_groups', 'get_alerts')
        arguments: Tool arguments as dict
        token: User's ThousandEyes API token
        
    Returns:
        Dict: API response or error message
    """
    if not token:
        return {
            "error": "ThousandEyes token not configured",
            "hint": "Please add your ThousandEyes API token in the Credentials page"
        }
    
    base_url = "https://api.thousandeyes.com/v6"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        # Map tool names to API endpoints
        if tool_name == "get_account_groups":
            url = f"{base_url}/account-groups"
            response = requests.get(url, headers=headers, timeout=15)
        
        elif tool_name == "get_agents":
            url = f"{base_url}/agents"
            response = requests.get(url, headers=headers, timeout=15)
        
        elif tool_name == "get_alerts":
            url = f"{base_url}/alerts"
            params = {k: v for k, v in arguments.items() if k in ['window', 'limit']}
            response = requests.get(url, headers=headers, params=params, timeout=15)
        
        elif tool_name == "get_alert_rules":
            url = f"{base_url}/alert-rules"
            response = requests.get(url, headers=headers, timeout=15)
        
        elif tool_name == "get_tests":
            url = f"{base_url}/tests"
            params = {k: v for k, v in arguments.items() if k in ['type', 'enabled']}
            response = requests.get(url, headers=headers, params=params, timeout=15)
        
        elif tool_name == "get_test_results":
            test_id = arguments.get("test_id")
            if not test_id:
                return {"error": "test_id is required"}
            url = f"{base_url}/test-results/{test_id}"
            params = {k: v for k, v in arguments.items() if k in ['window', 'limit']}
            response = requests.get(url, headers=headers, params=params, timeout=15)
        
        elif tool_name == "get_outages":
            url = f"{base_url}/outages"
            params = {k: v for k, v in arguments.items() if k in ['window']}
            response = requests.get(url, headers=headers, params=params, timeout=15)
        
        elif tool_name == "get_endpoint_agents":
            url = f"{base_url}/endpoint-agents"
            response = requests.get(url, headers=headers, timeout=15)
        
        else:
            return {"error": f"Unknown ThousandEyes tool: {tool_name}"}
        
        # Handle response
        if response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"data": response.text}
        
        elif response.status_code == 401:
            return {"error": "ThousandEyes token is invalid or expired"}
        
        elif response.status_code == 403:
            return {"error": "ThousandEyes token lacks required permissions for this operation"}
        
        elif response.status_code == 404:
            return {"error": "ThousandEyes resource not found"}
        
        else:
            logger.warning(f"ThousandEyes API error: {response.status_code} - {response.text[:200]}")
            return {"error": f"ThousandEyes API returned status {response.status_code}"}
    
    except requests.exceptions.Timeout:
        return {"error": "ThousandEyes API request timed out"}
    except requests.exceptions.ConnectionError:
        return {"error": "Unable to connect to ThousandEyes API"}
    except Exception as e:
        logger.error(f"ThousandEyes tool execution error: {type(e).__name__} - {str(e)}")
        return {"error": f"Tool execution failed: {type(e).__name__}"}


def handle_meraki_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    token: str
) -> Dict[str, Any]:
    """
    Execute a Meraki API tool call using user's token.
    
    Args:
        tool_name: Name of the tool (e.g., 'list_organizations', 'list_networks')
        arguments: Tool arguments as dict
        token: User's Meraki API token
        
    Returns:
        Dict: API response or error message
    """
    if not token:
        return {
            "error": "Meraki token not configured",
            "hint": "Please add your Meraki API token in the Credentials page"
        }
    
    base_url = "https://api.meraki.com/api/v1"
    headers = {
        "X-Cisco-Meraki-API-Key": token,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        # Map tool names to API endpoints
        if tool_name == "list_organizations":
            url = f"{base_url}/organizations"
            response = requests.get(url, headers=headers, timeout=15)
        
        elif tool_name == "get_organization":
            org_id = arguments.get("organization_id")
            if not org_id:
                return {"error": "organization_id is required"}
            url = f"{base_url}/organizations/{org_id}"
            response = requests.get(url, headers=headers, timeout=15)
        
        elif tool_name == "list_networks":
            org_id = arguments.get("organization_id")
            if not org_id:
                return {"error": "organization_id is required"}
            url = f"{base_url}/organizations/{org_id}/networks"
            response = requests.get(url, headers=headers, timeout=15)
        
        elif tool_name == "get_network":
            network_id = arguments.get("network_id")
            if not network_id:
                return {"error": "network_id is required"}
            url = f"{base_url}/networks/{network_id}"
            response = requests.get(url, headers=headers, timeout=15)
        
        elif tool_name == "list_devices":
            network_id = arguments.get("network_id")
            if not network_id:
                return {"error": "network_id is required"}
            url = f"{base_url}/networks/{network_id}/devices"
            response = requests.get(url, headers=headers, timeout=15)
        
        elif tool_name == "get_device":
            device_serial = arguments.get("device_serial")
            if not device_serial:
                return {"error": "device_serial is required"}
            url = f"{base_url}/devices/{device_serial}"
            response = requests.get(url, headers=headers, timeout=15)
        
        elif tool_name == "list_network_clients":
            network_id = arguments.get("network_id")
            if not network_id:
                return {"error": "network_id is required"}
            url = f"{base_url}/networks/{network_id}/clients"
            response = requests.get(url, headers=headers, timeout=15)
        
        elif tool_name == "get_network_health":
            network_id = arguments.get("network_id")
            if not network_id:
                return {"error": "network_id is required"}
            url = f"{base_url}/networks/{network_id}/uplink"
            response = requests.get(url, headers=headers, timeout=15)
        
        elif tool_name == "get_switch_ports":
            device_serial = arguments.get("device_serial")
            if not device_serial:
                return {"error": "device_serial is required"}
            url = f"{base_url}/devices/{device_serial}/switch/ports"
            response = requests.get(url, headers=headers, timeout=15)
        
        else:
            return {"error": f"Unknown Meraki tool: {tool_name}"}
        
        # Handle response
        if response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"data": response.text}
        
        elif response.status_code == 401:
            return {"error": "Meraki API key is invalid or expired"}
        
        elif response.status_code == 403:
            return {"error": "Meraki API key lacks required permissions for this operation"}
        
        elif response.status_code == 404:
            return {"error": "Meraki resource not found"}
        
        else:
            logger.warning(f"Meraki API error: {response.status_code} - {response.text[:200]}")
            return {"error": f"Meraki API returned status {response.status_code}"}
    
    except requests.exceptions.Timeout:
        return {"error": "Meraki API request timed out"}
    except requests.exceptions.ConnectionError:
        return {"error": "Unable to connect to Meraki API"}
    except Exception as e:
        logger.error(f"Meraki tool execution error: {type(e).__name__} - {str(e)}")
        return {"error": f"Tool execution failed: {type(e).__name__}"}


def get_available_tools(te_enabled: bool = False, meraki_enabled: bool = False) -> list:
    """
    Generate list of available MCP tools based on configured credentials.
    
    Args:
        te_enabled: True if user has valid ThousandEyes token
        meraki_enabled: True if user has valid Meraki token
        
    Returns:
        list: Available tool definitions for Claude
    """
    tools = []
    
    if te_enabled:
        tools.extend([
            {
                "name": "get_account_groups",
                "description": "Get ThousandEyes account groups",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_agents",
                "description": "List ThousandEyes agents",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_alerts",
                "description": "Get ThousandEyes alerts with optional time window",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "window": {"type": "integer", "description": "Time window in minutes"},
                        "limit": {"type": "integer", "description": "Maximum results"}
                    },
                    "required": []
                }
            },
            {
                "name": "get_alert_rules",
                "description": "List ThousandEyes alert rules",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_tests",
                "description": "List ThousandEyes tests",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "description": "Test type filter"},
                        "enabled": {"type": "boolean", "description": "Filter by enabled status"}
                    },
                    "required": []
                }
            },
            {
                "name": "get_test_results",
                "description": "Get results for a specific ThousandEyes test",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "test_id": {"type": "integer", "description": "Test ID"},
                        "window": {"type": "integer", "description": "Time window in minutes"},
                        "limit": {"type": "integer", "description": "Maximum results"}
                    },
                    "required": ["test_id"]
                }
            },
            {
                "name": "get_outages",
                "description": "Get ThousandEyes outage data",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "window": {"type": "integer", "description": "Time window in minutes"}
                    },
                    "required": []
                }
            },
            {
                "name": "get_endpoint_agents",
                "description": "List ThousandEyes Endpoint Agents",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ])
    
    if meraki_enabled:
        tools.extend([
            {
                "name": "list_organizations",
                "description": "List Meraki organizations",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_organization",
                "description": "Get details for a Meraki organization",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "organization_id": {"type": "string", "description": "Organization ID"}
                    },
                    "required": ["organization_id"]
                }
            },
            {
                "name": "list_networks",
                "description": "List networks in a Meraki organization",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "organization_id": {"type": "string", "description": "Organization ID"}
                    },
                    "required": ["organization_id"]
                }
            },
            {
                "name": "get_network",
                "description": "Get details for a Meraki network",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "network_id": {"type": "string", "description": "Network ID"}
                    },
                    "required": ["network_id"]
                }
            },
            {
                "name": "list_device",
                "description": "List devices in a Meraki network",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "network_id": {"type": "string", "description": "Network ID"}
                    },
                    "required": ["network_id"]
                }
            },
            {
                "name": "get_device",
                "description": "Get details for a Meraki device",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "device_serial": {"type": "string", "description": "Device serial number"}
                    },
                    "required": ["device_serial"]
                }
            },
            {
                "name": "list_network_clients",
                "description": "List clients connected to a Meraki network",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "network_id": {"type": "string", "description": "Network ID"}
                    },
                    "required": ["network_id"]
                }
            },
            {
                "name": "get_network_health",
                "description": "Get uplink health status for a Meraki network",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "network_id": {"type": "string", "description": "Network ID"}
                    },
                    "required": ["network_id"]
                }
            },
            {
                "name": "get_switch_ports",
                "description": "Get switch port information for a Meraki device",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "device_serial": {"type": "string", "description": "Device serial number"}
                    },
                    "required": ["device_serial"]
                }
            }
        ])
    
    return tools
