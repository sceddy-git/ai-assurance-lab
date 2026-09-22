"""
ThousandEyes v7 Administrative API client - account group and user
provisioning for the class/QR self-registration feature.

Unlike mcp_client.py (which uses each student's own personal Bearer token
against the hosted MCP server), this module uses a single admin-level API
token to create/delete Account Groups and Users via the plain REST
Administrative API - a capability the hosted MCP server's tool catalog
doesn't expose at all. That token is the requesting proctor's own personal
ThousandEyes token (the same one they save on their own Credentials page) -
there is deliberately no separate service-account credential stored in
.env. Callers (app.py) fetch it from the proctor's stored credentials and
pass it into every function here.

Hard org lock: every provisioning/cleanup call is verified against
REQUIRED_ORG_NAME before it does anything. If the supplied token belongs to
any other ThousandEyes organization, the call is refused outright. This is
intentional and must never be relaxed/parameterized - the whole point is
that this module can only ever touch one specific training org, regardless
of whose personal token is used to drive it.
"""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

TE_ADMIN_BASE_URL = "https://api.thousandeyes.com/v7"

# Hard requirement: this module must NEVER create/delete resources in any
# ThousandEyes organization other than this one, no matter whose personal
# token is passed in. Every provisioning/cleanup call re-verifies the
# token's organization against this exact name first.
REQUIRED_ORG_NAME = "AI-Powered Network Observability Day"

# Built-in role name to grant each auto-provisioned student on their own new
# Account Group. "Account Admin" is scoped to that one group only, unlike
# "Organization Admin" which would grant access across the entire org - so
# it's the safe default for a training account.
DEFAULT_ROLE_NAME = "Account Admin"


class ThousandEyesAdminError(Exception):
    """Raised when a ThousandEyes Administrative API call fails, including
    when the token's organization doesn't match REQUIRED_ORG_NAME."""
    pass


class WrongOrganizationError(ThousandEyesAdminError):
    """Raised specifically when the supplied token belongs to a
    ThousandEyes organization other than REQUIRED_ORG_NAME. Callers should
    treat this the same as any other provisioning failure (log + surface
    to the proctor), but it gets its own type so it's unmistakable in logs
    that this was a deliberate safety refusal, not a transient API error."""
    pass


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def get_organization_name(token: str) -> Optional[str]:
    """Return the ThousandEyes organization name this token belongs to, by
    inspecting the account groups it can see (every account group response
    includes its parent organizationName). Returns None if it can't be
    determined (e.g. the token has zero visible account groups)."""
    try:
        r = requests.get(f"{TE_ADMIN_BASE_URL}/account-groups", headers=_headers(token), timeout=15)
        r.raise_for_status()
        groups = r.json().get("accountGroups", [])
    except requests.RequestException as e:
        raise ThousandEyesAdminError(f"Could not verify ThousandEyes organization for this token: {e}")

    for group in groups:
        name = group.get("organizationName")
        if name:
            return name
    return None


def _verify_org(token: str) -> None:
    """Refuse to proceed unless this token's organization is exactly
    REQUIRED_ORG_NAME. This is the single choke point every provisioning/
    cleanup function must call first - never bypass it."""
    org_name = get_organization_name(token)
    if org_name is None:
        raise WrongOrganizationError(
            "Could not determine the ThousandEyes organization for this token - "
            f"refusing to provision/modify anything outside '{REQUIRED_ORG_NAME}'."
        )
    if org_name.strip() != REQUIRED_ORG_NAME:
        raise WrongOrganizationError(
            f"This ThousandEyes token belongs to organization '{org_name}', not the "
            f"required '{REQUIRED_ORG_NAME}'. Refusing to provision/modify anything - "
            "auto-provisioning is locked to this one training organization only."
        )


def is_org_token(token: Optional[str]) -> bool:
    """Best-effort, non-raising check of whether a token belongs to
    REQUIRED_ORG_NAME - used by the UI to show a clear "not configured for
    the right org" banner instead of a raw error. Returns False on any
    failure (missing token, network error, wrong org)."""
    if not token:
        return False
    try:
        _verify_org(token)
        return True
    except ThousandEyesAdminError:
        return False


_role_id_cache: Optional[str] = None


def _resolve_default_role_id(token: str) -> str:
    """Look up and cache the role ID for DEFAULT_ROLE_NAME. Raises if it
    can't be found - a misconfigured role name should fail loudly rather
    than silently create users with no permissions."""
    global _role_id_cache
    if _role_id_cache:
        return _role_id_cache

    try:
        r = requests.get(f"{TE_ADMIN_BASE_URL}/roles", headers=_headers(token), timeout=15)
        r.raise_for_status()
        roles = r.json().get("roles", r.json() if isinstance(r.json(), list) else [])
    except requests.RequestException as e:
        raise ThousandEyesAdminError(f"Could not list ThousandEyes roles: {e}")

    for role in roles:
        if (role.get("name") or "").strip().lower() == DEFAULT_ROLE_NAME.strip().lower():
            role_id = role.get("roleId") or role.get("id")
            if role_id:
                _role_id_cache = role_id
                return _role_id_cache

    raise ThousandEyesAdminError(
        f"Could not find a ThousandEyes role named '{DEFAULT_ROLE_NAME}' in "
        f"'{REQUIRED_ORG_NAME}'."
    )


def create_account_group(token: str, name: str) -> str:
    """Create a new ThousandEyes Account Group and return its ID. Caller
    must have already passed _verify_org() for this token."""
    try:
        r = requests.post(
            f"{TE_ADMIN_BASE_URL}/account-groups",
            headers=_headers(token), json={"name": name}, timeout=15
        )
        r.raise_for_status()
        data = r.json()
        group_id = data.get("id") or data.get("aid")
        if not group_id:
            raise ThousandEyesAdminError(f"Account group created but no ID in response: {data}")
        logger.info(f"Created ThousandEyes account group '{name}' (id={group_id}) in '{REQUIRED_ORG_NAME}'")
        return str(group_id)
    except requests.RequestException as e:
        detail = getattr(e.response, "text", "") if getattr(e, "response", None) else ""
        raise ThousandEyesAdminError(f"Failed to create account group '{name}': {e} {detail}")


def create_user(token: str, name: str, email: str, account_group_id: str) -> str:
    """Create a new ThousandEyes user, logging into and scoped to
    account_group_id with the default role. Returns the new user's uid.
    Caller must have already passed _verify_org() for this token."""
    role_id = _resolve_default_role_id(token)
    try:
        r = requests.post(
            f"{TE_ADMIN_BASE_URL}/users",
            headers=_headers(token),
            json={
                "name": name,
                "email": email,
                "loginAccountGroupId": account_group_id,
                "accountGroupRoles": [
                    {"accountGroupId": account_group_id, "roleIds": [role_id]}
                ],
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        uid = data.get("uid") or data.get("id")
        if not uid:
            raise ThousandEyesAdminError(f"User created but no uid in response: {data}")
        logger.info(f"Created ThousandEyes user for {email} (uid={uid}, group={account_group_id})")
        return str(uid)
    except requests.RequestException as e:
        detail = getattr(e.response, "text", "") if getattr(e, "response", None) else ""
        raise ThousandEyesAdminError(f"Failed to create ThousandEyes user for {email}: {e} {detail}")


def provision_student(token: str, name: str, email: str) -> dict:
    """Create a dedicated Account Group + User for one student, in that
    order, strictly within REQUIRED_ORG_NAME. Returns
    {"account_group_id": ..., "user_id": ...}.

    Raises WrongOrganizationError (a ThousandEyesAdminError subclass)
    before creating anything if the token isn't for the required org -
    this check happens first, every time, no caching across calls.
    """
    _verify_org(token)
    group_id = create_account_group(token, f"{name} ({email})" if name else email)
    user_id = create_user(token, name or email, email, group_id)
    return {"account_group_id": group_id, "user_id": user_id}


def delete_user(token: str, uid: str) -> None:
    try:
        r = requests.delete(f"{TE_ADMIN_BASE_URL}/users/{uid}", headers=_headers(token), timeout=15)
        if r.status_code not in (200, 202, 204, 404):
            r.raise_for_status()
        logger.info(f"Deleted ThousandEyes user {uid}")
    except requests.RequestException as e:
        raise ThousandEyesAdminError(f"Failed to delete ThousandEyes user {uid}: {e}")


def delete_account_group(token: str, group_id: str) -> None:
    try:
        r = requests.delete(f"{TE_ADMIN_BASE_URL}/account-groups/{group_id}", headers=_headers(token), timeout=15)
        if r.status_code not in (200, 202, 204, 404):
            r.raise_for_status()
        logger.info(f"Deleted ThousandEyes account group {group_id}")
    except requests.RequestException as e:
        raise ThousandEyesAdminError(f"Failed to delete ThousandEyes account group {group_id}: {e}")


def deprovision_student(token: str, account_group_id: Optional[str], user_id: Optional[str]) -> None:
    """Tear down one student's TE resources, strictly within
    REQUIRED_ORG_NAME. Deletes the user first - a user's
    loginAccountGroupId must not point at a group that still exists when
    the group is deleted, so order matters. Raises on the first failure;
    callers doing a bulk class cleanup should catch per-student and
    continue rather than let one failure abort the whole class.
    """
    _verify_org(token)
    if user_id:
        delete_user(token, user_id)
    if account_group_id:
        delete_account_group(token, account_group_id)
