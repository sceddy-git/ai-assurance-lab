"""
Optional Splunk Agent Observability (splunk-ao) integration.

Splunk Agent Observability is built directly on Galileo (the SDK's own
SplunkAOLogger class is implemented using galileo_core schemas internally,
and its error messages still reference app.galileo.ai) - it's effectively
Galileo under new Splunk/Cisco branding.

This module used to run alongside a separate galileo_telemetry.py (both
sending the same data to two backends). Galileo was removed 2026-11-10 -
Splunk AO alone now covers the same trace/span/cost data, so there was no
reason to keep paying for and maintaining a duplicate integration.

Design goals:
- Zero impact when SPLUNK_AO_REALM/SPLUNK_AO_O11Y_TOKEN aren't set.
- Never let a Splunk AO SDK error/outage break a student's chat response -
  every public function here swallows and logs its own exceptions.
- Don't send raw student email as free-text metadata; hash it first.
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
_AgentType = None

_Projects = None
_AgentStreams = None
_AnnotationQueues = None
_LikeDislikeConstraints = None
_AnnotationRatingCreate = None
_LikeDislikeRating = None
_create_rating_sync = None
_SplunkAOConfig = None

if ENABLED:
    try:
        from splunk_ao import SplunkAOLogger as _SplunkAOLogger  # noqa: N812
        from galileo_core.schemas.logging.agent import AgentType as _AgentType  # noqa: N812
        from splunk_ao.projects import Projects as _Projects  # noqa: N812
        from splunk_ao.agent_streams import AgentStreams as _AgentStreams  # noqa: N812
        from splunk_ao.annotation_queues import AnnotationQueues as _AnnotationQueues  # noqa: N812
        from splunk_ao.resources.models.like_dislike_constraints import LikeDislikeConstraints as _LikeDislikeConstraints  # noqa: N812
        from splunk_ao.resources.models.annotation_rating_create import AnnotationRatingCreate as _AnnotationRatingCreate  # noqa: N812
        from splunk_ao.resources.models.like_dislike_rating import LikeDislikeRating as _LikeDislikeRating  # noqa: N812
        from splunk_ao.resources.api.annotation_queue_records.create_annotation_queue_record_rating_annotation_queues_queue_id_records_record_id_rating_put import sync as _create_rating_sync  # noqa: N812
        from splunk_ao.configuration import SplunkAOConfig as _SplunkAOConfig  # noqa: N812
    except Exception as e:  # pragma: no cover - defensive, package may not be installed yet
        logger.warning(f"Splunk AO SDK not available, disabling telemetry: {e}")
        ENABLED = False

    # KNOWN SPLUNK AO BUG (confirmed 2026-11-10, splunk-ao 0.4.0): any API
    # response embedding a UserDB object (annotation-queue owner/creator,
    # collaborators, etc.) for an API-token identity fails to parse with
    # "'capability_based' is not a valid UserRole" -
    # splunk_ao.resources.models.user_db.UserDB.from_dict() does strict
    # `UserRole(_role)` enum construction, but this SDK version's UserRole
    # enum (admin/manager/read_only/user) predates Splunk's newer
    # "capability_based" RBAC role, which the backend now returns for API
    # tokens. Confirmed via direct SSM testing against the real annotation
    # queue API - every other code path in this module (projects, agent
    # streams, scorers, traces/spans) is unaffected, since none of those
    # responses embed a UserDB. Only the feedback/annotation-queue
    # functions below hit this. Worked around narrowly by making just
    # user_db.py's local UserRole binding tolerant of unknown values
    # (falls back to the raw string instead of raising) rather than
    # patching the shared UserRole class itself, so nothing else in the
    # SDK is affected. Safe to delete once Splunk ships a fixed SDK
    # version with a matching UserRole member.
    try:
        from splunk_ao.resources.models import user_db as _user_db_module
        from splunk_ao.resources.models.user_role import UserRole as _RealUserRole

        def _lenient_user_role(value):
            try:
                return _RealUserRole(value)
            except ValueError:
                logger.info(f"Splunk AO SDK bug workaround: unknown UserRole '{value}', using raw value")
                return value

        _user_db_module.UserRole = _lenient_user_role
    except Exception as e:
        logger.warning(f"Failed to apply Splunk AO UserRole workaround: {e}")


def hash_user(email: Optional[str]) -> str:
    """SHA-256 hash of a lowercased/stripped email, truncated to 16 chars -
    keeps students identifiable/groupable in Splunk AO without sending raw
    PII as free-text metadata."""
    if not email:
        return "unknown"
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:16]


def setup_metrics() -> None:
    """Bootstrap the configured Splunk AO project/agent stream so they exist
    before the first real chat request needs them. Call once at app startup.
    No-op if Splunk AO isn't configured.

    This used to also auto-enable the 5 preset LLM-judge evaluators
    (tool_selection_quality, tool_error_rate, instruction_adherence,
    correctness, action_completion) here. Removed 2026-11-10: judge-model
    scoring via the AWS Bedrock integration is blocked by a confirmed
    Splunk-side bug (see TECHNICAL_REFERENCE.md - Splunk double-URL-encodes
    the colon in Bedrock model IDs, breaking SigV4 signing for every Bedrock
    judge model), and the facilitator has since manually disabled evaluators
    in the Splunk UI. Auto-enabling them here on every app startup would
    silently fight that choice the moment Splunk ever fixes the underlying
    bug or the API token's permissions change. If evaluators are wanted
    again, enable them directly in the Splunk AO UI rather than re-adding
    this - the API token this app uses doesn't have permission to toggle
    project metrics anyway (confirmed via live testing: HTTP 403, error code
    8508, "You do not have permission to toggle metrics in this project.")."""
    if not ENABLED:
        return
    try:
        # The project/agent stream need to exist before any trace can be
        # logged against them, and they're normally auto-created lazily on
        # first use - so bootstrap one here with a throwaway trace instead
        # of leaving that to whichever student's chat request happens first.
        bootstrap = _SplunkAOLogger(project=SPLUNK_AO_PROJECT, agent_stream=SPLUNK_AO_AGENT_STREAM)
        bootstrap.start_trace(input="__startup_bootstrap__")
        bootstrap.conclude(output="ok")
        bootstrap.flush()
    except Exception as e:
        logger.warning(f"Splunk AO project/agent-stream bootstrap failed: {e}")


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
        # Group traces into one session per student per day - Action
        # Completion/Action Advancement are session-only metrics and never
        # fire on a bare trace.
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


# Cap on how much of any single input/output value gets sent to Splunk AO -
# large tool results shouldn't bloat telemetry payloads or hit SDK limits.
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
    """Converts Bedrock/Anthropic tool defs into the OpenAI-style shape
    add_llm_span's tools= parameter expects, so tool_selection_quality/
    tool_error_rate have something to judge selection against."""
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


def add_llm_span(ao_logger, request_body: dict, result: dict, model_id: str) -> Optional[str]:
    """Log one LLM span. Returns the span's record id (str) so a caller can
    later attach student thumbs up/down feedback to this exact span via
    submit_feedback() below, or None if telemetry is disabled/failed."""
    if ao_logger is None:
        return None
    try:
        usage = (result or {}).get('usage', {})
        span = ao_logger.add_llm_span(
            input=_truncate_for_logging(request_body.get('messages', '')),
            output=_truncate_for_logging(result.get('content', '')),
            model=model_id,
            tools=_anthropic_tools_to_openai_schema(request_body.get('tools')),
            num_input_tokens=usage.get('input_tokens'),
            num_output_tokens=usage.get('output_tokens'),
        )
        return str(getattr(span, 'id', '')) or None
    except Exception as e:
        logger.warning(f"Splunk AO add_llm_span failed: {e}")
        return None


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


# Student thumbs up/down feedback is modeled as a Splunk AO "annotation
# queue" rating. Splunk AO's annotation queues are built for curated human-review
# workflows (create a queue, explicitly add specific record ids to it, then
# rate a record already in the queue) rather than live per-message
# feedback - so this does all three steps on demand, lazily creating the
# queue/field once and caching their ids for the life of the process.
_FEEDBACK_QUEUE_NAME = "chat-message-feedback"
_FEEDBACK_FIELD_NAME = "helpful"
_feedback_queue_id: Optional[str] = None
_feedback_template_id: Optional[str] = None
_feedback_project_id: Optional[str] = None
_feedback_agent_stream_id: Optional[str] = None


def _ensure_feedback_queue() -> Optional[tuple]:
    """Lazily create (or find) the annotation queue + like/dislike field used
    for student chat feedback. Returns
    (queue_id, template_id, project_id, agent_stream_id), or None if setup
    fails. Cached in module globals after the first call."""
    global _feedback_queue_id, _feedback_template_id, _feedback_project_id, _feedback_agent_stream_id
    if _feedback_queue_id and _feedback_template_id and _feedback_project_id and _feedback_agent_stream_id:
        return (_feedback_queue_id, _feedback_template_id, _feedback_project_id, _feedback_agent_stream_id)
    try:
        project = _Projects().get_with_env_fallbacks(name=SPLUNK_AO_PROJECT)
        _feedback_project_id = project.id
        agent_stream = _AgentStreams().get(name=SPLUNK_AO_AGENT_STREAM, project_name=project.name)
        _feedback_agent_stream_id = agent_stream.id

        queues_client = _AnnotationQueues()
        queue = queues_client.get(name=_FEEDBACK_QUEUE_NAME)
        if queue is None:
            queue = queues_client.create(
                name=_FEEDBACK_QUEUE_NAME,
                description="Student thumbs up/down feedback on individual chat responses (AI Assurance Lab).",
            )
        _feedback_queue_id = queue.id

        template_id = None
        for field in queues_client.list_fields(queue.id):
            if getattr(field, 'name', None) == _FEEDBACK_FIELD_NAME:
                template_id = field.id
                break
        if template_id is None:
            field = queues_client.create_field(
                queue.id,
                name=_FEEDBACK_FIELD_NAME,
                constraints=_LikeDislikeConstraints(annotation_type="like_dislike"),
            )
            template_id = field.id
        _feedback_template_id = template_id

        return (_feedback_queue_id, _feedback_template_id, _feedback_project_id, _feedback_agent_stream_id)
    except Exception as e:
        logger.warning(f"Splunk AO feedback queue setup failed: {e}")
        return None


def submit_feedback(record_id: str, liked: bool) -> bool:
    """Record a student's thumbs up/down on one LLM span (identified by the
    record_id returned from add_llm_span) as a Splunk AO annotation-queue
    rating. Returns True if recorded, False if telemetry is disabled or the
    call fails - never raises."""
    if not ENABLED or not record_id:
        return False
    try:
        setup = _ensure_feedback_queue()
        if setup is None:
            return False
        queue_id, template_id, project_id, agent_stream_id = setup

        try:
            added = _AnnotationQueues().add_records(
                queue_id=queue_id, project_id=project_id, agent_stream_id=agent_stream_id, record_ids=[record_id]
            )
            if not added:
                # 0 added usually just means it's already in the queue from
                # a repeat vote on the same message - not fatal, still try
                # to write the rating below.
                logger.info(f"Splunk AO add_records_to_annotation_queue added 0 records for {record_id} (likely already queued)")
        except Exception as e:
            logger.info(f"Splunk AO add_records_to_annotation_queue non-fatal issue: {e}")

        config = _SplunkAOConfig.get()
        body = _AnnotationRatingCreate(rating=_LikeDislikeRating(value=liked))
        _create_rating_sync(
            queue_id=queue_id,
            record_id=record_id,
            client=config.api_client,
            body=body,
            annotation_template_id=template_id,
        )
        return True
    except Exception as e:
        logger.warning(f"Splunk AO submit_feedback failed: {e}")
        return False


_console_url_cache: Optional[str] = None


def get_console_url() -> Optional[str]:
    """Best-effort deep link to the Splunk AO console for proctors. No API
    round-trip needed to resolve project/log-stream UUIDs - the O11y Cloud
    console URL is a pure function of the realm
    (app.<realm>.observability.splunkcloud.com), per
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
    console URL."""
    return get_console_url()
