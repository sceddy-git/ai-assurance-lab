# Technical Reference

Architecture and maintenance reference for the AI Assurance Lab app. For
running a lab session day-to-day, see [`PROCTOR_GUIDE.md`](./PROCTOR_GUIDE.md)
instead.

## Architecture

```
Student browser
      │  HTTPS (443)
      ▼
  Nginx (reverse proxy, Let's Encrypt TLS, 180s proxy timeouts)
      │  proxy_pass → 127.0.0.1:5000
      ▼
  Gunicorn (3 workers, 180s timeout) → Flask app (app.py)
      │
      ├── AWS Cognito ──────── login / user management (Hosted UI, OAuth2 code flow)
      ├── AWS DynamoDB ─────── encrypted per-user MCP credentials
      ├── AWS Bedrock ──────── Claude Sonnet 4.5 (model calls + tool-use loop)
      ├── ThousandEyes MCP ─── https://api.thousandeyes.com/mcp   (hosted by Cisco)
      ├── Meraki MCP ───────── https://mcp.meraki.com/mcp         (hosted by Cisco)
      └── Splunk MCP ───────── user-supplied URL (local/tunneled or facilitator-hosted)
```

Everything runs on **one EC2 instance**. There is no container runtime, no
build pipeline, no load balancer — this is intentionally minimal for a
40-student lab, not a production multi-tenant SaaS.

### Live infra reference

| Resource | Value |
|---|---|
| EC2 instance | `i-09cdb070a8b829165` (t3.micro, us-east-1) |
| Elastic IP | `54.198.247.24` |
| Domain | `ai.thousandeyeschannel.com` (Route 53 A record → EIP) |
| Security group | `sg-07f716a418f2fb83d` (`ai-assurance-lab-sg`) — inbound 80, 443 only. No port 22. |
| IAM instance profile | `EC2-SSM-Profile` (SSM Core + app permissions — Bedrock invoke, DynamoDB CRUD, Cognito admin) |
| Cognito User Pool | `us-east-1_wUyz157rN` |
| Cognito App Client | `24ou7s3h56i851ofdjmadbkklm` (`ai-assurance-lab-app`), Hosted UI enabled, callback `https://ai.thousandeyeschannel.com/auth/callback` |
| Cognito email sending | **SES** (`EmailSendingAccount=DEVELOPER`), source `thousandeyeschannel.com` (verified domain, DKIM/SPF green, production access, 50,000/day quota). Sender: `no-reply@thousandeyeschannel.com`, reply-to `sceddy@cisco.com`. Switched from the old `COGNITO_DEFAULT` mailer (50/day cap, unreliable — see "Email delivery" below) on 2026-09-01. |
| DynamoDB table | `AIAssuranceLab-UserMCPCredentials` (partition key `email`, `PAY_PER_REQUEST`) |
| Bedrock model | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` |
| App path on instance | `/home/ubuntu/ai-assurance-lab` |
| systemd service | `flask-app` (Gunicorn, `--workers 3 --timeout 180`) |
| Git remote | `https://github.com/sceddy-git/ai-assurance-lab` (branch `main`) |

No SSH key is usable for login (port 22 closed); all instance access is via
**AWS SSM** (`aws ssm send-command`) or the web app's built-in admin routes.

### Email delivery (Cognito invite / password reset)

Two things had to be fixed on 2026-09-01 after a proctor got locked out:

1. **User creation no longer suppresses the invite email.** `app.py`'s
   `_create_cognito_student()` used to call `admin_create_user` with
   `MessageAction='SUPPRESS'` and a random temp password that was never
   shown to anyone. New accounts land in Cognito's `FORCE_CHANGE_PASSWORD`
   state, and **Cognito refuses "Forgot password" for accounts in that
   state** ("User password cannot be reset in the current state") — so a
   suppressed invite meant the account was permanently unreachable. Fixed by
   removing `MessageAction='SUPPRESS'` and adding
   `DesiredDeliveryMediums=['EMAIL']` so Cognito sends the real invite.
2. **Cognito's mailer was switched from `COGNITO_DEFAULT` to SES** (see
   table above) because the default mailer is low-volume/best-effort with no
   delivery guarantees and a 50/day cap.

Both the invite email and the password-reset code email were also given
custom templates so they include the login URL (`AdminCreateUserConfig.
InviteMessageTemplate` and `VerificationMessageTemplate` on the user pool —
these are **account config, not app code**, so they don't show up in git;
re-apply via `aws cognito-idp update-user-pool` if they ever need
recreating, e.g. after a `--email-configuration` update, which can silently
reset `AdminCreateUserConfig` back to null if it isn't included in that same
call):

```bash
aws cognito-idp update-user-pool --region us-east-1 \
  --user-pool-id us-east-1_wUyz157rN \
  --admin-create-user-config '{
    "AllowAdminCreateUserOnly": true,
    "InviteMessageTemplate": {
      "EmailSubject": "Your AI Assurance Lab account",
      "EmailMessage": "Welcome to the AI Assurance Lab!\n\nSign in here: https://ai.thousandeyeschannel.com/\n\nUsername: {username}\nTemporary password: {####}\n\nYou will be asked to set a new password on first login."
    }
  }'

aws cognito-idp update-user-pool --region us-east-1 \
  --user-pool-id us-east-1_wUyz157rN \
  --verification-message-template '{
    "DefaultEmailOption": "CONFIRM_WITH_CODE",
    "EmailSubject": "Your AI Assurance Lab password reset code",
    "EmailMessage": "Sign in here: https://ai.thousandeyeschannel.com/\n\nYour verification code is: {####}"
  }'
```

If a student reports a missing invite/reset email: check spam first (SES
delivery to `@cisco.com` has been confirmed working, but can be delayed a
few minutes); if it's truly missing, an admin can bypass email entirely with
`aws cognito-idp admin-set-user-password --permanent` to set a known
password directly.

## File layout (key files)

```
app.py                 Flask app: routes, auth, chat/tool-use loop, admin APIs
dynamo_db.py           DynamoDB CRUD + per-service connectivity tests
mcp_client.py          Generic MCP client (Streamable HTTP) used for TE/Meraki/Splunk
crypto.py              Fernet encryption helpers for stored tokens
attachments.py         In-memory file upload processing (images/PDF/Excel) for chat
templates/
  lab.html             Main chat UI (Claude-style rendering, guide sidebar, attachments)
  credentials.html     Per-user credential management (TE, Meraki+OrgID, Splunk)
  guide.html           In-app lab guide (rendered in an iframe sidebar + pop-out tab)
  admin_students.html  Student bulk/single add, list, delete-all
  admin_settings.html  Config, system status, logs, restart, git pull
ec2-setup.sh           One-time bootstrap script for a fresh EC2 instance
requirements.txt       Python deps (Flask, boto3, mcp SDK, pypdf, openpyxl, etc.)
```

## How credentials are stored

Per user (`dynamo_db.py`), keyed by email:

| Field | Notes |
|---|---|
| `thousandeyes_token` | Fernet-encrypted |
| `meraki_token` | Fernet-encrypted |
| `meraki_org_id` | Plaintext (not a secret) — required by nearly every Meraki MCP tool call, injected into the Bedrock system prompt per-request so the model never has to ask for it |
| `splunk_mcp_url` | Plaintext — varies per student/facilitator |
| `splunk_token` | Fernet-encrypted, optional |
| `te_connected` / `meraki_connected` / `splunk_connected` | Cached bool from last "Test Connection" |

Connectivity tests (`test_te_connectivity`, `test_meraki_connectivity`,
`test_splunk_connectivity`) work by actually calling `list_mcp_tools()` against
the real MCP server with the stored token — **not** a legacy REST endpoint —
so "Connected ✓" means the MCP server genuinely accepted the credential.

## Chat request flow (`/api/chat` in `app.py`)

1. Load the user's decrypted credentials from DynamoDB.
2. For each configured service (TE, Meraki, Splunk), call `list_mcp_tools()`
   to discover live tools; build a combined tool list + a `tool_name → (mcp_url,
   token, require_token)` routing table. Splunk tools use `require_token=False`
   since some self-hosted servers don't enforce auth.
3. Build the system prompt via `_build_system_prompt()`:
   - injects the current UTC date/time (prevents the model guessing dates for
     "last 2 hours"-style relative queries)
   - injects the user's `meraki_org_id` if set
   - includes instructions to emit downloadable output as fenced ` ```html `
     blocks (the frontend adds Download/Preview buttons for these)
4. Run an agentic loop (capped at `MAX_TOOL_ITERATIONS`, currently 6) against
   Bedrock: on each `tool_use` block, route the call via `call_mcp_tool()` to
   the correct MCP server and feed the result back, until Claude returns a
   final text response.
5. If attachments were included (multipart request), `attachments.py` converts
   images to vision content blocks and extracts text from PDF/Excel/CSV before
   they're added to the message.

## Proctor accounts

`PROCTOR_EMAILS` (comma-separated, in `.env`) is the authoritative list of
proctor emails, but the app never reads it raw — always via `_is_proctor()` /
`_get_proctor_emails()` in `app.py`, which unconditionally add
`SUPER_ADMIN_EMAIL = 'sceddy@cisco.com'` (hardcoded constant, not
configurable) so the account owner can never be locked out or deleted even if
`.env` is misconfigured or emptied.

Routes: `GET /api/admin/proctors/list`, `POST /api/admin/proctors/add`,
`POST /api/admin/proctors/delete` (all proctor-gated). Add/delete both call
`_persist_proctor_emails()` (rewrites `.env` + updates `os.environ` for the
current worker) followed by `_restart_flask_service()` so all Gunicorn
workers pick up the change immediately, rather than requiring a manual
restart or waiting for the next deploy. `delete_all_students()` computes
`_get_proctor_emails()` fresh and skips any Cognito user whose email is in
that set — proctors are never deleted by "Delete All Students".

## Deploying a code change

There is **no CI/CD pipeline** — deployment is a manual git pull + restart,
either from the web app or via SSM:

**Via the web app** (preferred, no AWS CLI needed): log in as a proctor →
`⚙️ Settings` → "Pull latest code from Git + restart".

**Via SSM** (from a machine with AWS CLI configured):

```bash
aws ssm send-command --region us-east-1 \
  --instance-ids i-09cdb070a8b829165 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=[
    "export HOME=/root",
    "git config --global --add safe.directory /home/ubuntu/ai-assurance-lab",
    "cd /home/ubuntu/ai-assurance-lab && git pull origin main",
    "systemctl restart flask-app",
    "sleep 2",
    "systemctl is-active flask-app"
  ]'
```

Then check the result with `aws ssm get-command-invocation --command-id ... 
--instance-id i-09cdb070a8b829165`.

If `requirements.txt` changed, also run
`venv/bin/pip install -r requirements.txt` before the restart.

## Emergency access without the web UI

If Nginx/Flask is fully down and `/admin/settings` is unreachable, use SSM
directly (same credentials/permissions as above):

```bash
# Check service status
aws ssm send-command --region us-east-1 --instance-ids i-09cdb070a8b829165 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["systemctl status flask-app --no-pager","systemctl status nginx --no-pager"]'

# Restart both
aws ssm send-command --region us-east-1 --instance-ids i-09cdb070a8b829165 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["systemctl restart flask-app","systemctl restart nginx"]'

# Tail logs
aws ssm send-command --region us-east-1 --instance-ids i-09cdb070a8b829165 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["journalctl -u flask-app -n 200 --no-pager"]'
```

Use `aws ssm get-command-invocation --command-id <id> --instance-id
i-09cdb070a8b829165` to retrieve output after sending.

## Known bugs found & fixed during verification (Sept 2026)

These were caught by an end-to-end pass through every lab guide prompt and are
already fixed on `main` / live:

1. **Admin `/admin/settings` system status 500** — `subprocess` calls to
   `systemctl`/`journalctl`/`git`/`sudo` used bare command names, which aren't
   on `PATH` inside gunicorn's restricted environment. Fixed by using absolute
   paths (`/usr/bin/systemctl`, etc.) in `app.py`.
2. **502 Bad Gateway on multi-tool chat turns** — default 30s gunicorn worker
   timeout was too short for multi-step Bedrock + MCP tool-use loops. Fixed by
   raising Gunicorn (`--timeout 180`) and Nginx (`proxy_*_timeout 180s`)
   timeouts. `ec2-setup.sh` updated to match for future instances.
3. **Claude fabricating dates** for relative time windows ("the last 2
   hours") because it had no ground truth for "now". Fixed by injecting the
   current UTC timestamp into the system prompt on every request
   (`_build_system_prompt()`).
4. **Meraki labs blocked** — Claude had no way to discover the required
   Organization ID and would either ask the user mid-conversation or guess
   wrong. Fixed by adding a `meraki_org_id` field to the Credentials page,
   stored per-user and injected into the system prompt.

## Adding a new MCP-backed service (e.g. a 4th tool)

Follow the Splunk pattern, since it's the "bring your own URL/token" template
(as opposed to TE/Meraki's fixed hosted URLs):

1. `dynamo_db.py`: add `save`/`get`/`delete` support for the new service's
   URL + optional token field.
2. `app.py`: add a branch in `/api/credentials/add` and `/api/credentials`
   (status), and add tool discovery + routing in `/api/chat` using
   `mcp_client.list_mcp_tools(url, token, require_token=...)`.
3. `templates/credentials.html`: add a new card with URL/token inputs.
4. `templates/guide.html`: document how to connect + a "Labs" section with
   prompts.
