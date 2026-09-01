"""
Client for Cisco's hosted MCP servers (ThousandEyes and Meraki).

Each user's decrypted API token is sent as a Bearer token to the vendor's
own hosted MCP server over Streamable HTTP. We never proxy raw REST calls
ourselves - the vendor's MCP server does that, using the requesting user's
own token, so all existing ThousandEyes/Meraki access controls and rate
limits are enforced exactly as they are for the vendor's official clients.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger(__name__)

THOUSANDEYES_MCP_URL = "https://api.thousandeyes.com/mcp"
MERAKI_MCP_URL = "https://mcp.meraki.com/mcp"


class MCPClientError(Exception):
    """Raised when an MCP server call fails."""
    pass


async def _list_tools_async(url: str, token: Optional[str]) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": tool.inputSchema or {"type": "object", "properties": {}}
                }
                for tool in result.tools
            ]


async def _call_tool_async(url: str, token: Optional[str], tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)

            # Flatten MCP content blocks into a single JSON-serializable result
            text_parts = []
            for block in result.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
                else:
                    text_parts.append(str(block))

            if result.isError:
                return {"error": "\n".join(text_parts) or "Tool call failed"}

            return {"result": "\n".join(text_parts)}


def _unwrap(e: BaseException) -> BaseException:
    """Unwrap ExceptionGroup/TaskGroup wrappers to find the real underlying error."""
    exceptions = getattr(e, "exceptions", None)
    if exceptions:
        return _unwrap(exceptions[0])
    return e


def _run(coro):
    """Run an async MCP coroutine from sync Flask request handlers."""
    try:
        return asyncio.run(coro)
    except Exception as e:
        real_error = _unwrap(e)
        logger.error(f"MCP client error: {type(real_error).__name__} - {real_error}")
        raise MCPClientError(f"{type(real_error).__name__}: {str(real_error)}")


def list_mcp_tools(url: str, token: Optional[str] = None, require_token: bool = True) -> List[Dict[str, Any]]:
    """
    List available tools from a hosted MCP server, in Claude tool format.

    Most MCP servers we integrate with (ThousandEyes, Meraki) require a
    Bearer token, so by default we no-op if one isn't configured. Some
    self-hosted servers (e.g. a student's local Splunk MCP server) may not
    require auth at all - pass require_token=False to allow calling with no
    token.
    """
    if not url:
        return []
    if require_token and not token:
        return []
    return _run(_list_tools_async(url, token))


def call_mcp_tool(url: str, token: Optional[str], tool_name: str, arguments: Optional[Dict[str, Any]] = None,
                   require_token: bool = True) -> Dict[str, Any]:
    """Call a tool on a hosted MCP server using the user's own token."""
    if not url:
        return {"error": "MCP server URL not configured"}
    if require_token and not token:
        return {"error": "Token not configured"}
    return _run(_call_tool_async(url, token, tool_name, arguments or {}))
