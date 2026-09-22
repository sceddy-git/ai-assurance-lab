"""
ThousandEyes v7 Administrative API client - account group and user
provisioning for the class/QR self-registration feature.

Unlike mcp_client.py (which uses each student's own personal Bearer token
against the hosted MCP server), this module uses a single org-admin-level
API token, held only server-side (THOUSANDEYES_ADMIN_TOKEN env var), to
create/delete Account Groups and Users via the plain REST Administrative
API - a capability the hosted MCP server's tool catalog doesn't expose at
all. This is a genuinely privileged credential: never log it, never send
it to the frontend, and keep .env at 600 perms like the app's other
secrets (SECRET_KEY, ENCRYPTION_KEY, COGNITO_CLIENT_SECRET).
"""

import os
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

TE_ADMIN_BASE_URL = "https://api.thousandeyes.com/v7"

# Built-in role name to grant each auto-provisioned student on their own new
# Account Group. "Account Admin" is scoped to that one group only, unlike
# "Organization Admin" which would grant access across the entire org - so
# it's the safe default for a training account. Override via env var if a
# different default role is preferred.
DEFAULT_ROLE_NAME = os.getenv('THOUSANDEYES_DEFAULT_ROLE_NAME', 'Account Admin')


class ThousandEyesAdminError(Exception):
    """Raised when a ThousandEyes Administrative API call fails."""
    pass


def _admin_token() -> Optional[str]:
    return os.getenv('THOUSANDEYES_ADMIN_TOKEN')


def is_configured() -> bool:
    """Whether an org-admin token is set up at all - callers should skip TE
    auto-provisioning (without erroring the whole signup) if this is False,
    since not every facilitator will have this configured."""
    return bool(_admin_token())


def _headers() -> dict:
    token = _admin_token()
    if not token:
        raise ThousandEyesAdminError(
            "THOUSANDEYES_ADMIN_TOKEN is not configured - cannot manage ThousandEyes "
            "account groups/users. Set it in .env to enable TE auto-provisioning."
        )
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


_role_id_cache: Optional[str] = None


def _resolve_default_role_id() -> str:
    """Look up and cache the role ID for DEFAULT_ROLE_NAME. Raises if it
    can't be found - a misconfigured role name should fail loudly rather
    than silently create users with no permissions."""
    global _role_id_cache
    if _role_id_cache:
        return _role_id_cache

    try:
        r = requests.get(f"{TE_ADMIN_BASE_URL}/roles", headers=_headers(), timeout=15)
        r.raise_for_status()
        roles = r.json().get("roles", r.json() if isinstance(r.json(), list) else [])
    except requests.RequestException as e:
        raise ThousandEyesAdminError(f"Could not list ThousandEyes roles: {e}")

    for role in roles:
        if (role.get("name") or "").strip().lower() == DEFAULT_ROLE_NAME.strip().lower():
            _role_id_cache = role.get("roleId") or role.get("id")
            if _role_id_cache:
                return _role_id_cache

    raise ThousandEyesAdminError(
        f"Could not find a ThousandEyes role named '{DEFAULT_ROLE_NAME}'. "
        "Set THOUSANDEYES_DEFAULT_ROLE_NAME to a role that exists in your org."
    )


def create_account_group(name: str) -> str:
    """Create a new ThousandEyes Account Group and return its ID.

    Raises ThousandEyesAdminError on failure.
    """
    try:
        r = requests.post(
            f"{TE_ADMIN_BASE_URL}/account-groups",
            headers=_headers(), json={"name": name}, timeout=15
        )
        r.raise_for_status()
        data = r.json()
        group_id = data.get("id") or data.get("aid")
        if not group_id:
            raise ThousandEyesAdminError(f"Account group created but no ID in response: {data}")
        logger.info(f"Created ThousandEyes account group '{name}' (id={group_id})")
        return str(group_id)
    except requests.RequestException as e:
        detail = getattr(e.response, "text", "") if getattr(e, "response", None) else ""
        raise ThousandEyesAdminError(f"Failed to create account group '{name}': {e} {detail}")


def create_user(name: str, email: str, account_group_id: str) -> str:
    """Create a new ThousandEyes user, logging into and scoped to
    account_group_id with the default role. Returns the new user's uid.

    ThousandEyes is expected to email the new user a registration/welcome
    link automatically (mirroring Cognito's own invite-email flow for
    students) - this hasn't been exercised against a real account yet, so
    verify with one real signup before relying on it for a live class.

    Raises ThousandEyesAdminError on failure.
    """
    role_id = _resolve_default_role_id()
    try:
        r = requests.post(
            f"{TE_ADMIN_BASE_URL}/users",
            headers=_headers(),
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


def provision_student(name: str, email: str) -> dict:
    """Create a dedicated Account Group + User for one student, in that
    order. Returns {"account_group_id": ..., "user_id": ...}.

    Best-effort partial cleanup on failure: if the account group was
    created but the user create fails, we leave the group in place rather
    than risk a second failure on delete - the caller/proctor can retry or
    manually clean it up via the admin UI.
    """
    group_id = create_account_group(f"{name} ({email})" if name else email)
    user_id = create_user(name or email, email, group_id)
    return {"account_group_id": group_id, "user_id": user_id}


def delete_user(uid: str) -> None:
    try:
        r = requests.delete(f"{TE_ADMIN_BASE_URL}/users/{uid}", headers=_headers(), timeout=15)
        if r.status_code not in (200, 202, 204, 404):
            r.raise_for_status()
        logger.info(f"Deleted ThousandEyes user {uid}")
    except requests.RequestException as e:
        raise ThousandEyesAdminError(f"Failed to delete ThousandEyes user {uid}: {e}")


def delete_account_group(group_id: str) -> None:
    try:
        r = requests.delete(f"{TE_ADMIN_BASE_URL}/account-groups/{group_id}", headers=_headers(), timeout=15)
        if r.status_code not in (200, 202, 204, 404):
            r.raise_for_status()
        logger.info(f"Deleted ThousandEyes account group {group_id}")
    except requests.RequestException as e:
        raise ThousandEyesAdminError(f"Failed to delete ThousandEyes account group {group_id}: {e}")


def deprovision_student(account_group_id: Optional[str], user_id: Optional[str]) -> None:
    """Tear down one student's TE resources. Deletes the user first - a
    user's loginAccountGroupId must not point at a group that still exists
    when the group is deleted, so order matters. Raises on the first
    failure; callers doing a bulk class cleanup should catch per-student
    and continue rather than let one failure abort the whole class.
    """
    if user_id:
        delete_user(user_id)
    if account_group_id:
        delete_account_group(account_group_id)
