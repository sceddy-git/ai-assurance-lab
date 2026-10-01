"""
Optional Splunk Agent Observability (splunk-ao) integration.

Splunk Agent Observability is built directly on Galileo (the SDK's own
SplunkAOLogger class is implemented using galileo_core schemas internally,
and its error messages still reference app.galileo.ai) - it's effectively
Galileo under new Splunk/Cisco branding. Because of that, this module is a
near 1:1 port of galileo_telemetry.py: same shape, same call sites in
app.py, same env-var pattern, just SplunkAOLogger instead of GalileoLogger
and Splunk's O11y Cloud deployment env vars instead of Galileo's.

This runs ALONGSIDE galileo_telemetry.py, not instead of it, for as long as
both are configured - there's no reason to lose the existing Galileo history
while Splunk AO is still "not yet generally available" (per its own docs,
as of this integration).

Design goals (identical to galileo_telemetry.py):
- Zero impact when SPLUNK_AO_REALM/SPLUNK_AO_O11Y_TOKEN aren't set.
- Never let a Splunk AO SDK error/outage break a student's chat response -
  every public function here swallows and logs its own exceptions.
- Don't send raw student email as free-text metadata; hash it the same way
  galileo_telemetry.py does.
"""

import datetime
import hashlib
import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Splunk Observability Cloud deployment env vars (see splunk-ao README) -
# distinct from the on-premises/standalone Agent Observability deployment,
# which instead uses SPLUNK_AO_API_KEY + SPLUNK_AO_CONSOLE_URL. This lab
# only supports the O11y Cloud flavor, since that's what's configured here.
SPLUNK_AO_REALM = os.getenv('SPLUNK_AO_REALM')
SPLUNK_AO_O11Y_TOKEN = os.getenv('SPLUNK_AO_O11Y_TOKEN')
SPLUNK_AO_PROJECT = os.getenv('SPLUNK_AO_PROJECT', 'ai-assurance-lab')
SPLUNK_AO_AGENT_STREAM = os.getenv('SPLUNK_AO_AGENT_STREAM', 'production')

ENABLED = bool(SPLUNK_AO_REALM and SPLUNK_AO_O11Y_TOKEN)

_SplunkAOLogger = None
_SplunkAOEvaluators = None
_enable_evaluators_fn = None
_AgentType = None

if ENABLED:
    try:
        from splunk_ao import SplunkAOLogger as _SplunkAOLogger  # noqa: N812
        from splunk_ao.schema.metrics import SplunkAOEvaluators as _SplunkAOEvaluators  # noqa: N812
        from splunk_ao.agent_streams import enable_evaluators as _enable_evaluators_fn
        from galileo_core.schemas.logging.agent import AgentType as _AgentType  # noqa: N812
    except Exception as e:  # pragma: no cover - defensive, package may not be installed yet
        logger.warning(f"Splunk AO SDK not available, disabling telemetry: {e}")
        ENABLED = False


def hash_user(email: Optional[str]) -> str:
    """Same hashing scheme as galileo_telemetry.hash_user() - independent
    copy so this module has zero import-time dependency on Galileo."""
    if not email:
        return "unknown"
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:16]


def setup_metrics() -> None:
    """Enable evaluation metrics on the configured agent stream. Call once
    at app startup. No-op if Splunk AO isn't configured."""
    if not ENABLED:
        return
    try:
        # Same rationale as galileo_telemetry.setup_metrics(): the
        # project/agent stream need to exist before metrics can be enabled
        # on them, and they're normally auto-created lazily on first use.
        bootstrap = _SplunkAOLogger(project=SPLUNK_AO_PROJECT, agent_stream=SPLUNK_AO_AGENT_STREAM)
        bootstrap.start_trace(input="__startup_bootstrap__")
        bootstrap.conclude(output="ok")
        bootstrap.flush()
    except Exception as e:
        logger.warning(f"Splunk AO project/agent-stream bootstrap failed (metrics may not enable): {e}")

    try:
        _enable_evaluators_fn(
            project_name=SPLUNK_AO_PROJECT,
            agent_stream_name=SPLUNK_AO_AGENT_STREAM,
            metrics=[
                _SplunkAOEvaluators.tool_selection_quality,
                _SplunkAOEvaluators.tool_error_rate,
                _SplunkAOEvaluators.action_completion,
                _SplunkAOEvaluators.instruction_adherence,
                _SplunkAOEvaluators.correctness,
            ],
        )
        logger.info(f"Splunk AO metrics enabled for {SPLUNK_AO_PROJECT}/{SPLUNK_AO_AGENT_STREAM}")
    except Exception as e:
        logger.warning(f"Failed to enable Splunk AO metrics: {e}")


def new_logger():
    """Return a fresh SplunkAOLogger for one chat request, or None if
    telemetry is disabled/unavailable. Every call site must handle None."""
    if not ENABLED:
        return None
    try:
        return _SplunkAOLogger(project=SPLUNK_AO_PROJECT, agent_stream=SPLUNK_AO_AGENT_STREAM)
    except Exception as e:
        logger.warning(f"Failed to create Splunk AO logger: {e}")
        return None


def start_trace(ao_logger, email: str, user_message: str, labs_matched: Any,
                 is_proctor: bool = False) -> Optional[str]:
    """Start a trace for one chat request. Returns the trace's id (as a
    string), or None if telemetry is disabled or trace creation fails."""
    if ao_logger is None:
        return None
    try:
        # Same per-student-per-day session grouping as galileo_telemetry.py,
        # for the same reason: Action Completion/Action Advancement are
        # session-only metrics and never fire on a bare trace.
        session_external_id = f"{hash_user(email)}:{datetime.date.today().isoformat()}"
        try:
            ao_logger.start_session(
                name=f"Student session {session_external_id}",
                external_id=session_external_id,
            )
        except Exception as e:
            logger.warning(f"Splunk AO start_session failed (continuing without a session): {e}")

        trace = ao_logger.start_trace(
            input=user_message or "",
            tags=[
                f"user:{hash_user(email)}",
                f"role:{'proctor' if is_proctor else 'student'}",
            ] + [f"lab:{lab}" for lab in (labs_matched or [])],
        )
        if _AgentType is not None:
            try:
                ao_logger.add_agent_span(
                    input=user_message or "",
                    name="chat_turn",
                    agent_type=_AgentType.react,
                )
            except Exception as e:
                logger.warning(f"Splunk AO add_agent_span failed (continuing without it): {e}")
        return str(getattr(trace, 'id', '')) or None
    except Exception as e:
        logger.warning(f"Splunk AO start_trace failed: {e}")
        return None


# Same cap/rationale as galileo_telemetry.MAX_LOGGED_CHARS.
MAX_LOGGED_CHARS = 24_000


def _truncate_for_logging(value: Any) -> str:
    """Stringify and cap a value before sending it to Splunk AO. Never
    raises - telemetry formatting must never be the reason a chat request
    fails."""
    try:
        text = value if isinstance(value, str) else json.dumps(value, default=str)
    except Exception:
        text = str(value)
    if len(text) > MAX_LOGGED_CHARS:
        omitted = len(text) - MAX_LOGGED_CHARS
        text = text[:MAX_LOGGED_CHARS] + f"\n...[truncated {omitted} chars for Splunk AO logging only - full data was still sent to Claude]"
    return text


def _anthropic_tools_to_openai_schema(anthropic_tools: Optional[list]) -> Optional[list]:
    """Same conversion as galileo_telemetry._anthropic_tools_to_openai_schema
    - Bedrock/Anthropic tool defs into the OpenAI-style shape add_llm_span's
    tools= parameter expects, so tool_selection_quality/tool_error_rate have
    something to judge selection against."""
    if not anthropic_tools:
        return None
    converted = []
    for t in anthropic_tools:
        try:
            converted.append({
                "type": "function",
                "function": {
                    "name": t.get("name"),
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
                },
            })
        except Exception:
            continue
    return converted or None


def add_llm_span(ao_logger, request_body: dict, result: dict, model_id: str) -> None:
    if ao_logger is None:
        return
    try:
        usage = (result or {}).get('usage', {})
        ao_logger.add_llm_span(
            input=_truncate_for_logging(request_body.get('messages', '')),
            output=_truncate_for_logging(result.get('content', '')),
            model=model_id,
            tools=_anthropic_tools_to_openai_schema(request_body.get('tools')),
            num_input_tokens=usage.get('input_tokens'),
            num_output_tokens=usage.get('output_tokens'),
        )
    except Exception as e:
        logger.warning(f"Splunk AO add_llm_span failed: {e}")


def add_tool_span(ao_logger, tool_name: str, tool_input: dict, tool_result: Any,
                   tool_use_id: str, module: Optional[str], had_error: bool) -> None:
    if ao_logger is None:
        return
    try:
        ao_logger.add_tool_span(
            input=_truncate_for_logging(tool_input),
            output=_truncate_for_logging(tool_result),
            name=tool_name,
            tool_call_id=tool_use_id,
            status_code=500 if had_error else 200,
            tags=[module] if module else None,
        )
    except Exception as e:
        logger.warning(f"Splunk AO add_tool_span failed: {e}")


def conclude_and_flush(ao_logger, assistant_message: str) -> None:
    if ao_logger is None:
        return
    try:
        ao_logger.conclude(output=_truncate_for_logging(assistant_message or ""), conclude_all=True)
        ao_logger.flush()
    except Exception as e:
        logger.warning(f"Splunk AO conclude/flush failed: {e}")


_console_url_cache: Optional[str] = None


def get_console_url() -> Optional[str]:
    """Best-effort deep link to the Splunk AO console for proctors. Unlike
    Galileo's version, this doesn't need an API round-trip to resolve
    project/log-stream UUIDs - the O11y Cloud console URL is a pure
    function of the realm (app.<realm>.observability.splunkcloud.com), per
    splunk_ao.deployment.O11yConfig.require_console_url."""
    global _console_url_cache
    if not ENABLED:
        return None
    if _console_url_cache:
        return _console_url_cache
    _console_url_cache = f"https://app.{SPLUNK_AO_REALM}.observability.splunkcloud.com/"
    return _console_url_cache


def get_dashboard_url() -> Optional[str]:
    """No agent-stream-specific dashboard deep link is exposed by the SDK
    yet (Agent Observability on O11y Cloud is pre-GA) - fall back to the
    console URL, same as galileo_telemetry.get_dashboard_url() falls back
    when its own trends-deep-link lookup fails."""
    return get_console_url()
