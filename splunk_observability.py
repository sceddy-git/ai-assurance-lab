"""
Optional Splunk Observability Cloud (APM) integration, sent via OpenTelemetry
OTLP/HTTP directly to Splunk's ingest endpoint - no local Collector required.

This runs ALONGSIDE galileo_telemetry.py, not instead of it: Galileo's
judge-model metrics (tool_selection_quality, action_completion, correctness,
etc.) have no equivalent here, since Splunk O11y Cloud doesn't run an LLM
judge over traces. What this module adds is traces/spans/latency/error-rate
visibility in Splunk APM, using the OpenTelemetry GenAI semantic
conventions so spans render correctly in Splunk's AI Observability views.

One trace per /api/chat request, mirroring galileo_telemetry.py's shape:
    root span   "chat_turn"            (gen_ai.operation.name=chat)
      -> child  "chat <model>"         one per Bedrock invoke_model call
      -> child  "execute_tool <name>"  one per MCP tool call

Design goals (same as galileo_telemetry.py):
- Zero impact when SPLUNK_REALM/SPLUNK_ACCESS_TOKEN aren't set.
- Never let an exporter error break a student's chat response - every
  public function here swallows and logs its own exceptions.
- Don't send raw student email to Splunk as a free-text attribute; hash it
  the same way galileo_telemetry.py does so the two systems can eventually
  be cross-referenced by the same opaque per-student identifier.
- Spans are created with an explicit parent context passed around in a
  plain dict (not ambient/"current span" contextvars) so concurrent
  requests on different gunicorn threads can never cross-contaminate each
  other's trace trees.
"""

import hashlib
import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

SPLUNK_REALM = os.getenv("SPLUNK_REALM")
SPLUNK_ACCESS_TOKEN = os.getenv("SPLUNK_ACCESS_TOKEN")
ENABLED = bool(SPLUNK_REALM and SPLUNK_ACCESS_TOKEN)

_tracer = None
_StatusCode = None
_Status = None
_set_span_in_context = None

if ENABLED:
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.trace import Status, StatusCode

        _Status = Status
        _StatusCode = StatusCode
        _set_span_in_context = trace.set_span_in_context

        _endpoint = f"https://ingest.{SPLUNK_REALM}.observability.splunkcloud.com/v2/trace/otlp"
        _exporter = OTLPSpanExporter(endpoint=_endpoint, headers={"X-SF-Token": SPLUNK_ACCESS_TOKEN})
        _provider = TracerProvider(resource=Resource.create({
            "service.name": "ai-assurance-lab",
            "deployment.environment": os.getenv("DEPLOY_ENV", "production"),
        }))
        # SimpleSpanProcessor exports synchronously on span.end() - no
        # background batching thread, no risk of losing spans on a worker
        # restart. Traffic here is low (one trace per chat message across
        # at most a few dozen concurrent students), so the extra per-span
        # HTTP POST is a non-issue; it also means there's nothing to flush
        # at the end of a request, unlike a BatchSpanProcessor.
        _provider.add_span_processor(SimpleSpanProcessor(_exporter))
        trace.set_tracer_provider(_provider)
        _tracer = trace.get_tracer("ai-assurance-lab.chat")
        logger.info(f"Splunk Observability tracing enabled -> {_endpoint}")
    except Exception as e:
        logger.warning(f"Failed to initialize Splunk Observability tracing (continuing without it): {e}")
        ENABLED = False
        _tracer = None


# Same cap/rationale as galileo_telemetry.MAX_LOGGED_CHARS - keep large tool
# payloads from bloating span attributes (Splunk APM spans aren't meant to
# carry hundreds of KB of raw JSON), independent of whatever cap Galileo
# applies on its own copy.
MAX_LOGGED_CHARS = 24_000


def _truncate(value: Any) -> str:
    try:
        text = value if isinstance(value, str) else json.dumps(value, default=str)
    except Exception:
        text = str(value)
    if len(text) > MAX_LOGGED_CHARS:
        omitted = len(text) - MAX_LOGGED_CHARS
        text = text[:MAX_LOGGED_CHARS] + f"\n...[truncated {omitted} chars for Splunk span logging only]"
    return text


def hash_user(email: Optional[str]) -> str:
    """Same hashing scheme as galileo_telemetry.hash_user() - kept as an
    independent copy rather than importing from there, so this module has
    zero dependency on Galileo being configured/available."""
    if not email:
        return "unknown"
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:16]


def new_context() -> Optional[dict]:
    """Return a fresh, empty trace-context holder for one chat request, or
    None if Splunk tracing is disabled. Every call site must handle None
    the same way they already handle a None Galileo logger."""
    if not ENABLED:
        return None
    return {}


def start_trace(ctx: Optional[dict], email: str, user_message: str, labs_matched: Any,
                 is_proctor: bool = False) -> Optional[str]:
    """Start the root 'chat_turn' span for one request. Returns the trace's
    hex trace_id, or None if disabled/failed."""
    if ctx is None or _tracer is None:
        return None
    try:
        labs = ",".join(labs_matched or [])
        root_span = _tracer.start_span(
            name="chat_turn",
            attributes={
                "gen_ai.operation.name": "chat",
                "gen_ai.provider.name": "aws.bedrock",
                "user.hash": hash_user(email),
                "user.role": "proctor" if is_proctor else "student",
                "lab.checkpoints_matched": labs,
                "gen_ai.input.messages": _truncate(user_message or ""),
            },
        )
        ctx["root_span"] = root_span
        ctx["parent_ctx"] = _set_span_in_context(root_span)
        return format(root_span.get_span_context().trace_id, "032x")
    except Exception as e:
        logger.warning(f"Splunk start_trace failed: {e}")
        return None


def add_llm_span(ctx: Optional[dict], request_body: dict, result: dict, model_id: str) -> None:
    if ctx is None or ctx.get("parent_ctx") is None or _tracer is None:
        return
    try:
        usage = (result or {}).get("usage", {})
        span = _tracer.start_span(
            name=f"chat {model_id}",
            context=ctx["parent_ctx"],
            attributes={
                "gen_ai.operation.name": "chat",
                "gen_ai.provider.name": "aws.bedrock",
                "gen_ai.request.model": model_id,
                "gen_ai.usage.input_tokens": usage.get("input_tokens") or 0,
                "gen_ai.usage.output_tokens": usage.get("output_tokens") or 0,
                "gen_ai.input.messages": _truncate(request_body.get("messages", "")),
                "gen_ai.output.messages": _truncate(result.get("content", "")),
            },
        )
        span.end()
    except Exception as e:
        logger.warning(f"Splunk add_llm_span failed: {e}")


def add_tool_span(ctx: Optional[dict], tool_name: str, tool_input: dict, tool_result: Any,
                   tool_use_id: str, module: Optional[str], had_error: bool) -> None:
    if ctx is None or ctx.get("parent_ctx") is None or _tracer is None:
        return
    try:
        span = _tracer.start_span(
            name=f"execute_tool {tool_name}",
            context=ctx["parent_ctx"],
            attributes={
                "gen_ai.operation.name": "execute_tool",
                "gen_ai.tool.name": tool_name,
                "gen_ai.tool.call.id": tool_use_id or "",
                "gen_ai.tool.call.arguments": _truncate(tool_input),
                "gen_ai.tool.call.result": _truncate(tool_result),
                "lab.module": module or "",
            },
        )
        if had_error and _Status is not None and _StatusCode is not None:
            span.set_status(_Status(_StatusCode.ERROR))
        span.end()
    except Exception as e:
        logger.warning(f"Splunk add_tool_span failed: {e}")


def conclude_and_flush(ctx: Optional[dict], assistant_message: str) -> None:
    """End the root span. Named to mirror galileo_telemetry.conclude_and_flush,
    though with SimpleSpanProcessor there's nothing separate to flush -
    every child span already exported synchronously on its own .end()."""
    if ctx is None:
        return
    root_span = ctx.get("root_span")
    if root_span is None:
        return
    try:
        root_span.set_attribute("gen_ai.output.messages", _truncate(assistant_message or ""))
        root_span.end()
    except Exception as e:
        logger.warning(f"Splunk conclude_and_flush failed: {e}")
