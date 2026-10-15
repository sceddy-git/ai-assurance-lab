"""
Client for Cisco's hosted MCP servers (ThousandEyes and Meraki).

Each user's decrypted API token is sent as a Bearer token to the vendor's
own hosted MCP server over Streamable HTTP. We never proxy raw REST calls
ourselves - the vendor's MCP server does that, using the requesting user's
own token, so all existing ThousandEyes/Meraki access controls and rate
limits are enforced exactly as they are for the vendor's official clients.
"""

import asyncio
import concurrent.futures
import logging
import threading
from typing import Any, Dict, List, Optional

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger(__name__)

THOUSANDEYES_MCP_URL = "https://api.thousandeyes.com/mcp"
MERAKI_MCP_URL = "https://mcp.meraki.com/mcp"


class MCPClientError(Exception):
    """Raised when an MCP server call fails."""
    pass


def _httpx_client_factory(verify_tls: bool):
    """Build an httpx AsyncClient factory matching the MCP SDK's expected
    signature (headers, timeout, auth) -> httpx.AsyncClient, but with TLS
    verification optionally disabled.

    This only matters for self-hosted Splunk MCP servers - ThousandEyes and
    Meraki always use real, verifiable certs and are never called with
    verify_tls=False. Some self-hosted setups (e.g. Splunk "Show" training
    instances) only offer a self-signed cert, so a student/facilitator can
    opt in to skipping verification for their own Splunk connection via the
    Credentials page. This is never a default - it must be explicitly
    enabled per-user for the Splunk MCP URL they configured.
    """
    def factory(headers: Optional[dict] = None, timeout: Optional[httpx.Timeout] = None,
                auth: Optional[httpx.Auth] = None) -> httpx.AsyncClient:
        kwargs: Dict[str, Any] = {"follow_redirects": True, "verify": verify_tls}
        kwargs["timeout"] = timeout if timeout is not None else httpx.Timeout(30.0)
        if headers is not None:
            kwargs["headers"] = headers
        if auth is not None:
            kwargs["auth"] = auth
        return httpx.AsyncClient(**kwargs)
    return factory


async def _list_tools_async(url: str, token: Optional[str], verify_tls: bool = True) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with streamablehttp_client(url, headers=headers, httpx_client_factory=_httpx_client_factory(verify_tls)) as (read, write, _):
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


async def _call_tool_async(url: str, token: Optional[str], tool_name: str, arguments: Dict[str, Any],
                            verify_tls: bool = True) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with streamablehttp_client(url, headers=headers, httpx_client_factory=_httpx_client_factory(verify_tls)) as (read, write, _):
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


# Hard wall-clock ceiling for an entire MCP call (connect + initialize +
# tool execution), independent of the transport-level httpx timeout.
#
# Why this is needed: _httpx_client_factory() sets a 30s httpx timeout, but
# that only bounds the gap *between* bytes on a streaming connection - a
# vendor MCP server that trickles data slowly (without ever going fully
# silent for 30s straight) can hold this open far longer than 30s, with no
# exception ever raised. Since app.py calls this synchronously from a
# gunicorn gthread worker (--timeout 180), a hang like that ties up the
# thread for the full 180s with zero app-level error logged, and worse,
# gunicorn's --timeout is a per-WORKER watchdog, not per-thread: if it
# fires, the entire worker process (and every other request it happened to
# be concurrently serving) gets killed. Discovered 2026-10-13 from a string
# of /api/chat 504s with no corresponding exception in the app logs.
MCP_CALL_TIMEOUT_SECONDS = 25

# Persistent background event loop, one per gunicorn worker process, used for
# every MCP call made by any of that worker's request-handling threads.
#
# Previously _run() called asyncio.run() fresh for every single MCP call -
# each one spinning up a brand-new event loop (and the anyio thread pool
# streamablehttp_client/httpx offload blocking work like DNS/TLS onto). When
# a call was cancelled mid-flight by the MCP_CALL_TIMEOUT_SECONDS wait_for
# (or the underlying blocking op just never returned), the orphaned OS
# thread had no event loop left to rejoin and just sat there - over a long
# enough uptime and high enough call volume, this accumulated into 50-70+
# leaked threads on the busiest worker, exhausting memory and causing 504s
# even on trivial static-asset requests. Root-caused 2026-10-14 via thread
# counts correlating with per-worker request volume.
#
# Using one long-lived loop/thread pool for the whole process lifetime
# means anyio's thread offload pool is created once and properly reused
# instead of being torn down and recreated (potentially incompletely) on
# every call.
_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None
_loop_lock = threading.Lock()


def _get_loop() -> asyncio.AbstractEventLoop:
    """Return this process's persistent MCP event loop, starting it (once)
    on first use. Thread-safe - multiple gthread request threads in the same
    worker call this concurrently."""
    global _loop, _loop_thread
    with _loop_lock:
        if _loop is None or not _loop_thread.is_alive():
            _loop = asyncio.new_event_loop()

            def _run_forever(loop: asyncio.AbstractEventLoop):
                asyncio.set_event_loop(loop)
                loop.run_forever()

            _loop_thread = threading.Thread(
                target=_run_forever, args=(_loop,), daemon=True, name="mcp-event-loop"
            )
            _loop_thread.start()
        return _loop


def _run(coro):
    """Run an async MCP coroutine from sync Flask request handlers, bounded
    by MCP_CALL_TIMEOUT_SECONDS regardless of how the transport behaves.

    Dispatches onto the persistent per-process loop (see _get_loop) instead
    of asyncio.run()'ing a fresh one each call. On timeout, explicitly
    cancels the in-flight task - this is the documented pattern for
    run_coroutine_threadsafe (concurrent.futures.Future.cancel() after a
    TimeoutError propagates the cancellation back into the coroutine running
    on the loop), so a hung call gets torn down instead of continuing to
    occupy the loop/thread pool in the background indefinitely."""
    future = asyncio.run_coroutine_threadsafe(coro, _get_loop())
    try:
        return future.result(timeout=MCP_CALL_TIMEOUT_SECONDS)
    except concurrent.futures.TimeoutError:
        future.cancel()
        logger.error(f"MCP client error: call exceeded {MCP_CALL_TIMEOUT_SECONDS}s hard timeout")
        raise MCPClientError(
            f"MCP server did not respond within {MCP_CALL_TIMEOUT_SECONDS}s"
        )
    except Exception as e:
        real_error = _unwrap(e)
        logger.error(f"MCP client error: {type(real_error).__name__} - {real_error}")
        raise MCPClientError(f"{type(real_error).__name__}: {str(real_error)}")


def list_mcp_tools(url: str, token: Optional[str] = None, require_token: bool = True,
                    verify_tls: bool = True) -> List[Dict[str, Any]]:
    """
    List available tools from a hosted MCP server, in Claude tool format.

    Most MCP servers we integrate with (ThousandEyes, Meraki) require a
    Bearer token, so by default we no-op if one isn't configured. Some
    self-hosted servers (e.g. a student's local Splunk MCP server) may not
    require auth at all - pass require_token=False to allow calling with no
    token. Pass verify_tls=False for self-hosted servers with a self-signed
    cert (e.g. Splunk "Show" training instances) - never used for
    ThousandEyes/Meraki, which always have real certs.
    """
    if not url:
        return []
    if require_token and not token:
        return []
    return _run(_list_tools_async(url, token, verify_tls))


def call_mcp_tool(url: str, token: Optional[str], tool_name: str, arguments: Optional[Dict[str, Any]] = None,
                   require_token: bool = True, verify_tls: bool = True) -> Dict[str, Any]:
    """Call a tool on a hosted MCP server using the user's own token."""
    if not url:
        return {"error": "MCP server URL not configured"}
    if require_token and not token:
        return {"error": "Token not configured"}
    return _run(_call_tool_async(url, token, tool_name, arguments or {}, verify_tls))
