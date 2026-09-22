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


def _list_account_groups(token: str) -> list:
    try:
        r = requests.get(f"{TE_ADMIN_BASE_URL}/account-groups", headers=_headers(token), timeout=15)
        r.raise_for_status()
        return r.json().get("accountGroups", [])
    except requests.RequestException as e:
        raise ThousandEyesAdminError(f"Could not list ThousandEyes account groups for this token: {e}")


def get_organization_name(token: str) -> Optional[str]:
    """Return the first organization name visible to this token, purely
    for display purposes (e.g. an error message). NOT used for the actual
    org-lock check - a token can see account groups across several
    organizations at once (ThousandEyes supports "users in multiple
    organizations"), so checking only the first one is wrong; see
    _find_anchor_account_group() for the real check."""
    groups = _list_account_groups(token)
    for group in groups:
        name = group.get("organizationName")
        if name:
            return name
    return None


def _find_anchor_account_group(token: str) -> str:
    """Find the account group ID that belongs to REQUIRED_ORG_NAME among
    ALL account groups visible to this token (not just the first one/the
    token's default login account group). This ID is required as the
    `aid` query parameter on every subsequent Administrative API call
    (account-group creation, role lookup, user creation) - without it,
    ThousandEyes silently operates in the token's default login account
    group's organization instead of the one we actually asked for.

    Raises WrongOrganizationError if no account group in
    REQUIRED_ORG_NAME is visible to this token at all - this is the single
    choke point every provisioning/cleanup function must call first, and
    it must never be bypassed or cached across different tokens.
    """
    groups = _list_account_groups(token)
    visible_orgs = sorted({g.get("organizationName") for g in groups if g.get("organizationName")})
    for group in groups:
        if group.get("organizationName") == REQUIRED_ORG_NAME:
            aid = group.get("aid") or group.get("id")
            if aid:
                return str(aid)

    raise WrongOrganizationError(
        f"This ThousandEyes token has no account group in the required organization "
        f"'{REQUIRED_ORG_NAME}'. Organizations visible to this token: {visible_orgs or 'none'}. "
        "Refusing to provision/modify anything - auto-provisioning is locked to this one "
        "training organization only."
    )


def is_org_token(token: Optional[str]) -> bool:
    """Best-effort, non-raising check of whether a token can see an
    account group in REQUIRED_ORG_NAME - used by the UI to show a clear
    "not configured for the right org" banner instead of a raw error.
    Returns False on any failure (missing token, network error, wrong org)."""
    if not token:
        return False
    try:
        _find_anchor_account_group(token)
        return True
    except ThousandEyesAdminError:
        return False


_role_id_cache: Optional[str] = None


def _resolve_default_role_id(token: str, anchor_aid: str) -> str:
    """Look up and cache the role ID for DEFAULT_ROLE_NAME, scoped to the
    target org via ?aid=anchor_aid (roles are organization-specific).
    Raises if it can't be found - a misconfigured role name should fail
    loudly rather than silently create users with no permissions."""
    global _role_id_cache
    if _role_id_cache:
        return _role_id_cache

    try:
        r = requests.get(
            f"{TE_ADMIN_BASE_URL}/roles", headers=_headers(token),
            params={"aid": anchor_aid}, timeout=15
        )
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


def create_account_group(token: str, name: str, anchor_aid: str) -> str:
    """Create a new ThousandEyes Account Group inside REQUIRED_ORG_NAME
    and return its ID. `?aid=anchor_aid` is required - without it this
    request operates in the token's default login account group, which
    may belong to a completely different organization. `accountGroupName`
    (not `name`) is the field the v7 API actually expects in the body."""
    try:
        r = requests.post(
            f"{TE_ADMIN_BASE_URL}/account-groups",
            headers=_headers(token), params={"aid": anchor_aid},
            json={"accountGroupName": name}, timeout=15
        )
        r.raise_for_status()
        data = r.json()
        group_id = data.get("aid") or data.get("id")
        if not group_id:
            raise ThousandEyesAdminError(f"Account group created but no ID in response: {data}")
        logger.info(f"Created ThousandEyes account group '{name}' (aid={group_id}) in '{REQUIRED_ORG_NAME}'")
        return str(group_id)
    except requests.RequestException as e:
        detail = getattr(e.response, "text", "") if getattr(e, "response", None) else ""
        raise ThousandEyesAdminError(f"Failed to create account group '{name}': {e} {detail}")


def create_user(token: str, name: str, email: str, account_group_id: str, anchor_aid: str) -> str:
    """Create a new ThousandEyes user, logging into and scoped to
    account_group_id (the newly-created group, inside REQUIRED_ORG_NAME)
    with the default role. Returns the new user's uid. `?aid=anchor_aid`
    keeps this call in the required org's context, same as account-group
    creation above."""
    role_id = _resolve_default_role_id(token, anchor_aid)
    try:
        r = requests.post(
            f"{TE_ADMIN_BASE_URL}/users",
            headers=_headers(token), params={"aid": anchor_aid},
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
    before creating anything if this token has no visibility into the
    required org at all - this check happens first, every time.
    """
    anchor_aid = _find_anchor_account_group(token)
    group_id = create_account_group(token, f"{name} ({email})" if name else email, anchor_aid)
    user_id = create_user(token, name or email, email, group_id, anchor_aid)
    return {"account_group_id": group_id, "user_id": user_id}


def delete_user(token: str, uid: str, anchor_aid: str) -> None:
    try:
        r = requests.delete(
            f"{TE_ADMIN_BASE_URL}/users/{uid}", headers=_headers(token),
            params={"aid": anchor_aid}, timeout=15
        )
        if r.status_code not in (200, 202, 204, 404):
            r.raise_for_status()
        logger.info(f"Deleted ThousandEyes user {uid}")
    except requests.RequestException as e:
        raise ThousandEyesAdminError(f"Failed to delete ThousandEyes user {uid}: {e}")


def delete_account_group(token: str, group_id: str, anchor_aid: str) -> None:
    try:
        r = requests.delete(
            f"{TE_ADMIN_BASE_URL}/account-groups/{group_id}", headers=_headers(token),
            params={"aid": anchor_aid}, timeout=15
        )
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
    anchor_aid = _find_anchor_account_group(token)
    if user_id:
        delete_user(token, user_id, anchor_aid)
    if account_group_id:
        delete_account_group(token, account_group_id, anchor_aid)
