"""
Optional Galileo (rungalileo.io) observability integration.

This app calls Bedrock and MCP tool servers directly via boto3/httpx rather
than through a framework Galileo has a built-in callback for (e.g. LangChain),
so this wraps Galileo's manual GalileoLogger SDK around the existing chat
loop: one trace per /api/chat request, one LLM span per Bedrock call, one
tool span per MCP tool call.

Design goals:
- Zero impact when GALILEO_API_KEY isn't set (the lab must work without it -
  Galileo is instrumentation, not a dependency of the lab itself).
- Never let a Galileo SDK error/outage break a student's chat response. Every
  public function here swallows and logs its own exceptions.
- Don't send raw student email to Galileo as free-text metadata; hash it so
  a proctor can still tell "this is the same student across traces" without
  a training-lab log stream containing a plaintext roster of corporate email
  addresses forever.
"""

import hashlib
import logging
import os
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

GALILEO_API_KEY = os.getenv('GALILEO_API_KEY')
GALILEO_PROJECT = os.getenv('GALILEO_PROJECT', 'ai-assurance-lab')
GALILEO_LOG_STREAM = os.getenv('GALILEO_LOG_STREAM', 'production')
GALILEO_API_BASE = os.getenv('GALILEO_API_BASE', 'https://api.galileo.ai')

# Name of the "like/dislike" annotation template created once via the
# Galileo API for thumbs up/down student feedback (see submit_feedback()).
# Looked up lazily and cached, so a fresh Galileo project without this
# template yet doesn't break chat - feedback submission just no-ops.
FEEDBACK_TEMPLATE_NAME = os.getenv('GALILEO_FEEDBACK_TEMPLATE_NAME', 'Student Feedback')

ENABLED = bool(GALILEO_API_KEY)

_GalileoLogger = None
_GalileoMetrics = None
_enable_metrics_fn = None

if ENABLED:
    try:
        from galileo import GalileoLogger as _GalileoLogger  # noqa: N812
        from galileo import GalileoMetrics as _GalileoMetrics  # noqa: N812
        from galileo.log_streams import enable_metrics as _enable_metrics_fn
    except Exception as e:  # pragma: no cover - defensive, package may not be installed yet
        logger.warning(f"Galileo SDK not available, disabling telemetry: {e}")
        ENABLED = False


def hash_user(email: Optional[str]) -> str:
    """Stable, non-reversible identifier for a student, safe to send to a
    third-party observability platform instead of their real email."""
    if not email:
        return "unknown"
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:16]


def setup_metrics() -> None:
    """Enable evaluation metrics on the configured log stream. Call once at
    app startup. No-op if Galileo isn't configured."""
    if not ENABLED:
        return
    try:
        # enable_metrics() requires the project/log stream to already exist,
        # but they're normally auto-created lazily on the first real trace.
        # On a brand new Galileo project, that means enabling metrics at
        # startup (before any student has chatted) fails with "Project not
        # found". Bootstrap it here with a throwaway trace so metrics can be
        # turned on immediately, even before the first real conversation.
        bootstrap = _GalileoLogger(project=GALILEO_PROJECT, log_stream=GALILEO_LOG_STREAM)
        bootstrap.start_trace(input="__startup_bootstrap__")
        bootstrap.conclude(output="ok")
        bootstrap.flush()
    except Exception as e:
        logger.warning(f"Galileo project/log-stream bootstrap failed (metrics may not enable): {e}")

    try:
        _enable_metrics_fn(
            project_name=GALILEO_PROJECT,
            log_stream_name=GALILEO_LOG_STREAM,
            metrics=[
                _GalileoMetrics.tool_selection_quality,
                _GalileoMetrics.tool_error_rate,
                _GalileoMetrics.action_completion,
                _GalileoMetrics.instruction_adherence,
                _GalileoMetrics.correctness,
                # Custom metric (created once via the Galileo API - not a
                # GalileoMetrics enum member, referenced here by name)
                # specific to this lab: does the assistant's answer stay
                # grounded in real TE/Meraki/Splunk tool output instead of
                # fabricating a plausible-sounding diagnosis?
                "diagnostic_quality",
            ],
        )
        logger.info(f"Galileo metrics enabled for {GALILEO_PROJECT}/{GALILEO_LOG_STREAM}")
    except Exception as e:
        logger.warning(f"Failed to enable Galileo metrics: {e}")


def new_logger():
    """Return a fresh GalileoLogger for one chat request, or None if
    telemetry is disabled/unavailable. Every call site must handle None."""
    if not ENABLED:
        return None
    try:
        return _GalileoLogger(project=GALILEO_PROJECT, log_stream=GALILEO_LOG_STREAM)
    except Exception as e:
        logger.warning(f"Failed to create Galileo logger: {e}")
        return None


def start_trace(gl_logger, email: str, user_message: str, labs_matched: Any,
                 is_proctor: bool = False) -> Optional[str]:
    """Start a trace for one chat request. Returns the trace's UUID (as a
    string) so the caller can hand it back to the frontend and later attach
    thumbs up/down feedback to this exact trace via submit_feedback(). Returns
    None if telemetry is disabled or trace creation fails - callers must
    treat a None trace_id as "feedback isn't available for this message"."""
    if gl_logger is None:
        return None
    try:
        trace = gl_logger.start_trace(
            input=user_message or "",
            tags=[
                f"user:{hash_user(email)}",
                f"role:{'proctor' if is_proctor else 'student'}",
            ] + [f"lab:{lab}" for lab in (labs_matched or [])],
        )
        return str(getattr(trace, 'id', '')) or None
    except Exception as e:
        logger.warning(f"Galileo start_trace failed: {e}")
        return None


def add_llm_span(gl_logger, request_body: dict, result: dict, model_id: str) -> None:
    if gl_logger is None:
        return
    try:
        usage = (result or {}).get('usage', {})
        gl_logger.add_llm_span(
            input=str(request_body.get('messages', '')),
            output=str(result.get('content', '')),
            model=model_id,
            num_input_tokens=usage.get('input_tokens'),
            num_output_tokens=usage.get('output_tokens'),
        )
    except Exception as e:
        logger.warning(f"Galileo add_llm_span failed: {e}")


def add_tool_span(gl_logger, tool_name: str, tool_input: dict, tool_result: Any,
                   tool_use_id: str, module: Optional[str], had_error: bool) -> None:
    if gl_logger is None:
        return
    try:
        import json as _json
        gl_logger.add_tool_span(
            input=_json.dumps(tool_input) if not isinstance(tool_input, str) else tool_input,
            output=_json.dumps(tool_result) if not isinstance(tool_result, str) else tool_result,
            name=tool_name,
            tool_call_id=tool_use_id,
            status_code=500 if had_error else 200,
            tags=[module] if module else None,
        )
    except Exception as e:
        logger.warning(f"Galileo add_tool_span failed: {e}")


_console_url_cache: Optional[str] = None
_project_id_cache: Optional[str] = None
_feedback_template_id_cache: Optional[str] = None


def _resolve_project_id() -> Optional[str]:
    """Best-effort lookup of this project's UUID, cached for the life of the
    process. Needed for direct REST calls (feedback ratings) that the
    GalileoLogger SDK doesn't wrap. Returns None if unavailable."""
    global _project_id_cache
    if not ENABLED:
        return None
    if _project_id_cache:
        return _project_id_cache
    try:
        probe = _GalileoLogger(project=GALILEO_PROJECT, log_stream=GALILEO_LOG_STREAM)
        project_id = getattr(probe, 'project_id', None)
        if project_id:
            _project_id_cache = str(project_id)
    except Exception as e:
        logger.warning(f"Could not resolve Galileo project id: {e}")
    return _project_id_cache


def _resolve_feedback_template_id() -> Optional[str]:
    """Find (or create) the like/dislike annotation template used for
    student thumbs up/down feedback. Cached for the life of the process."""
    global _feedback_template_id_cache
    if not ENABLED:
        return None
    if _feedback_template_id_cache:
        return _feedback_template_id_cache
    project_id = _resolve_project_id()
    if not project_id:
        return None
    headers = {"Galileo-API-Key": GALILEO_API_KEY, "Content-Type": "application/json"}
    try:
        r = requests.get(
            f"{GALILEO_API_BASE}/v2/projects/{project_id}/annotation/templates",
            headers=headers, timeout=10,
        )
        r.raise_for_status()
        for t in r.json():
            if t.get("name") == FEEDBACK_TEMPLATE_NAME:
                _feedback_template_id_cache = t["id"]
                return _feedback_template_id_cache
        # Not found - create it once. Idempotent enough for our purposes
        # (worst case under a race, two templates with this name exist and
        # we always resolve to whichever the GET returns first).
        r = requests.post(
            f"{GALILEO_API_BASE}/v2/projects/{project_id}/annotation/templates",
            headers=headers, timeout=10,
            json={
                "name": FEEDBACK_TEMPLATE_NAME,
                "criteria": "Was this response helpful?",
                "constraints": {"annotation_type": "like_dislike"},
                "include_explanation": False,
            },
        )
        r.raise_for_status()
        _feedback_template_id_cache = r.json()["id"]
    except Exception as e:
        logger.warning(f"Could not resolve/create Galileo feedback template: {e}")
    return _feedback_template_id_cache


def submit_feedback(trace_id: str, liked: bool) -> bool:
    """Record a student's thumbs up/down on a specific chat response as a
    Galileo annotation rating on that trace. Best-effort: returns False
    (and logs a warning) on any failure rather than raising, since a failed
    feedback submission must never surface as an error to the student."""
    if not ENABLED or not trace_id:
        return False
    project_id = _resolve_project_id()
    template_id = _resolve_feedback_template_id()
    if not project_id or not template_id:
        return False
    try:
        r = requests.put(
            f"{GALILEO_API_BASE}/v2/projects/{project_id}/annotation/templates/"
            f"{template_id}/traces/{trace_id}/rating",
            headers={"Galileo-API-Key": GALILEO_API_KEY, "Content-Type": "application/json"},
            json={"rating": {"annotation_type": "like_dislike", "value": bool(liked)}},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        logger.warning(f"Galileo submit_feedback failed for trace {trace_id}: {e}")
        return False


def get_console_url() -> Optional[str]:
    """Best-effort deep link to this project's Log stream in the Galileo
    console, for proctors. Deep links need the project/log-stream UUIDs,
    which only exist once a logger has actually talked to Galileo - so this
    creates one throwaway logger to resolve them, then caches the result for
    the life of the process. Falls back to the generic console URL (or None)
    if Galileo isn't configured or the lookup fails, so a broken/slow
    Galileo API never breaks the proctor dashboard pages that link to it."""
    global _console_url_cache
    if not ENABLED:
        return None
    if _console_url_cache:
        return _console_url_cache
    console_base = os.getenv('GALILEO_CONSOLE_URL', 'https://app.galileo.ai').rstrip('/')
    try:
        probe = _GalileoLogger(project=GALILEO_PROJECT, log_stream=GALILEO_LOG_STREAM)
        project_id = getattr(probe, 'project_id', None)
        log_stream_id = getattr(probe, 'log_stream_id', None)
        if project_id and log_stream_id:
            _console_url_cache = f"{console_base}/project/{project_id}/log-streams/{log_stream_id}"
        elif project_id:
            _console_url_cache = f"{console_base}/project/{project_id}"
        else:
            _console_url_cache = console_base
    except Exception as e:
        logger.warning(f"Could not resolve Galileo console deep link, falling back to base URL: {e}")
        _console_url_cache = console_base
    return _console_url_cache


_dashboard_url_cache: Optional[str] = None


def get_dashboard_url() -> Optional[str]:
    """Best-effort deep link to the log stream's Trends dashboard (the
    Model Quality / Tool Usage / System Metrics charts set up for
    proctors), falling back to the plain log-stream console URL if the
    dashboard-specific link can't be resolved."""
    global _dashboard_url_cache
    if not ENABLED:
        return None
    if _dashboard_url_cache:
        return _dashboard_url_cache
    console_url = get_console_url()
    if not console_url:
        return None
    try:
        project_id = _resolve_project_id()
        probe = _GalileoLogger(project=GALILEO_PROJECT, log_stream=GALILEO_LOG_STREAM)
        log_stream_id = getattr(probe, 'log_stream_id', None)
        if project_id and log_stream_id:
            headers = {"Galileo-API-Key": GALILEO_API_KEY}
            r = requests.get(
                f"{GALILEO_API_BASE}/v2/projects/{project_id}/log_streams/{log_stream_id}/trends",
                headers=headers, timeout=10,
            )
            r.raise_for_status()
            # There's no query param that deep-links straight into the
            # Trends tab's saved "Default View" - the console picks that up
            # from its own client-side state. So we link to the log-stream
            # page itself; the nav label tells proctors to click
            # Trends -> Default View once there.
            if r.json().get("id"):
                _dashboard_url_cache = console_url
                return _dashboard_url_cache
    except Exception as e:
        logger.warning(f"Could not resolve Galileo dashboard deep link: {e}")
    _dashboard_url_cache = console_url
    return _dashboard_url_cache


def conclude_and_flush(gl_logger, assistant_message: str) -> None:
    if gl_logger is None:
        return
    try:
        gl_logger.conclude(output=assistant_message or "")
        gl_logger.flush()
    except Exception as e:
        logger.warning(f"Galileo conclude/flush failed: {e}")
