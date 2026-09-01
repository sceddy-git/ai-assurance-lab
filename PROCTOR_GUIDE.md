# AI Assurance Lab — Proctor Guide

This is the **single source of truth** for running the lab. Everything else you might
find in this repo's git history (Docker/AppRunner/CodeBuild instructions, multiple
overlapping README files) is obsolete — the lab now runs on a single always-on EC2
instance, managed entirely through the web app or AWS CLI/SSM. No Docker, no CI/CD
pipeline, no local builds.

For how the system is built (architecture, file layout, deploying code changes), see
[`TECHNICAL_REFERENCE.md`](./TECHNICAL_REFERENCE.md). This guide is about **running a
lab session**.

---

## 1. What's already live

| Thing | Value |
|---|---|
| Student URL | **https://ai.thousandeyeschannel.com** |
| Login | AWS Cognito (email + password), Hosted UI |
| AI backend | AWS Bedrock, Claude Sonnet 4.5 |
| Credential storage | Encrypted per-user in DynamoDB (`AIAssuranceLab-UserMCPCredentials`) |
| MCP integrations | ThousandEyes (hosted), Meraki (hosted), Splunk (student/facilitator-provided URL) |
| Infra | 1× EC2 `t3.micro` (`i-09cdb070a8b829165`), Elastic IP `54.198.247.24`, Nginx + Let's Encrypt TLS, Flask/Gunicorn via systemd, managed via AWS SSM (no SSH) |

The lab is **designed to stay running between sessions** — you don't need to
redeploy anything to run another cohort. You only need to reset the student list
(Section 3).

---

## 2. Before a lab session

### 2.1 Add students

Go to **https://ai.thousandeyeschannel.com/admin/students** (log in as a proctor
first — see `PROCTOR_EMAILS` in Section 5 for who counts as a proctor).

- **Bulk add**: upload a `.csv`, `.xlsx`, or `.xls` file with columns `email,
  first_name, last_name` (header row required). Every row becomes a Cognito user
  with a random temporary password (they set their own on first login).
- **Single add**: use the "Add a Single Student" form on the same page — email,
  first name, last name.
- **List / delete all**: the same page shows current students and has a
  "Delete All Students" button for a full reset.

### 2.2 Reset between different cohorts

If you're running back-to-back sessions with different attendee lists, use
**Delete All Students** on `/admin/students`, then bulk-upload the new roster.
This clears Cognito **student** users only — it does **not** touch the EC2
instance (no downtime, nothing to redeploy) and it **never deletes proctors**
(see 2.3) — those accounts are meant to persist across every cohort.

Each deleted student's encrypted API credentials in DynamoDB become orphaned
(keyed by email) but harmless — a re-added student with the same email will
just re-enter their credentials on the Credentials page as normal.

### 2.3 Proctors vs. students

Proctors are a protected class of account, managed from the **🛡️ Proctors**
section on `/admin/students`:

- **Add a proctor**: any existing proctor can promote/create another proctor
  by email. This creates a Cognito login for them (if they don't already have
  one) and adds them to the protected list. Only proctors can add other
  proctors.
- **Remove a proctor**: any proctor can remove another proctor, which deletes
  their account and revokes proctor access.
- **`sceddy@cisco.com` is a permanent super admin** — hardcoded in the app so
  it can never be deleted or demoted, even if `PROCTOR_EMAILS` is emptied by
  mistake. This is the account-owner backstop; it never needs to be re-added.
- **Delete All Students never touches proctors.** Proctors are excluded from
  that operation automatically — there's nothing extra you need to do to
  protect them.

Adding/removing a proctor restarts the Flask service (a few seconds of
downtime for anyone actively chatting) so the change takes effect for every
worker process immediately, rather than only on the next full redeploy.

### 2.4 Give students their instructions

Send students only:
1. The URL: **https://ai.thousandeyeschannel.com**
2. Their email (as added above).

**There is no default/shared password.** Each account is created with a
random one-time password that is never emailed or shown to anyone. On first
visit, students should:

1. Go to the URL above → click through to the sign-in page.
2. Click **"Forgot your password?"** (right under the password field).
3. Enter their email → Cognito emails them a verification code.
4. Enter the code + choose their own password → they're logged in.

Tell students to check spam/junk if the code doesn't arrive within a minute —
these come from Cognito's own mailer, which occasionally lands there.

**Capacity note:** Cognito's built-in email service is capped at **50
emails/day for the whole pool** (not per student). A single ~40-student
session fits, but running two sessions the same day, or students needing
multiple reset attempts, can hit that cap. If a student says they never
received their code and it's not in spam, check `⚙️ Settings` → Logs, or ask
whoever manages the AWS account whether the daily email cap was hit (see
`TECHNICAL_REFERENCE.md` for the fix — switching to SES removes the cap).

The in-app **📘 Lab Guide** sidebar (and a "pop out to new tab" button) contains
everything else: how to connect ThousandEyes/Meraki/Splunk, and all lab prompts.
You don't need to distribute a separate PDF/HTML file.

---

## 3. Credentials students will need to bring

| Service | What they need | Where it's entered |
|---|---|---|
| ThousandEyes | Personal OAuth Bearer token (Account Settings → Users and Roles → User API Tokens, or your org's shared demo token) | Credentials page → ThousandEyes card |
| Meraki | Dashboard API key **and** Organization ID | Credentials page → Meraki card (**both** fields — see note below) |
| Splunk (optional module) | MCP server URL (yours, or one you host for the class) + optional auth token | Credentials page → Splunk card |

**Important — Meraki Organization ID:** the Meraki MCP server's tools require an
org ID on almost every call, and there's no reliable way for the AI to
self-discover it. Students must paste their Org ID (visible in the Meraki
Dashboard URL, e.g. `.../o/712812/...`) into the **Organization ID** field on
the Credentials page, once. If you're using a shared demo Meraki org for the
whole class, tell students the org ID directly (e.g. "712812") rather than
having them look it up.

**Splunk MCP server:** unlike ThousandEyes/Meraki, there's no Cisco-hosted MCP
server for Splunk — someone has to run one. Options:
- Provide one shared, facilitator-hosted MCP server URL to the whole class.
- Have each student run their own locally and expose it via a tunnel (e.g.
  `ngrok http 8000`), then paste the resulting `https://…ngrok.io/mcp` URL.

If you're not running the Splunk module this session, students can simply skip
that card — it's optional and has no effect on the ThousandEyes/Meraki modules.

---

## 4. Day-of-lab operations (all via the web app, no AWS CLI needed)

Proctors see two extra links in the chat header: **👥 Students** and **⚙️ Settings**.

- **👥 Students** (`/admin/students`): add/reset students (Section 2).
- **⚙️ Settings** (`/admin/settings`):
  - View live system status (CPU, memory, Flask service state).
  - View recent application logs (last 100 lines) — first place to check if a
    student reports an error.
  - **Restart Flask** — use this if the app seems stuck; it's a ~5 second
    interruption for anyone actively chatting.
  - **Pull latest code from Git + restart** — use this if you've been told a
    code fix has been pushed to the `main` branch (see `TECHNICAL_REFERENCE.md`
    for how updates get pushed).

If the web app itself is down and you can't reach `/admin/settings`, fall back
to AWS Systems Manager (SSM) from your own machine — see
`TECHNICAL_REFERENCE.md` Section "Emergency access without the web UI".

---

## 5. Proctor access

Use the **🛡️ Proctors** section on `/admin/students` to add/remove proctors
(Section 2.3) — this is the normal way to manage proctor access day-to-day.

The underlying `PROCTOR_EMAILS` environment variable can also be edited
directly via `⚙️ Settings` (Configuration section) as a fallback, but prefer
the Proctors UI since it also creates/deletes the Cognito login for you and
restarts Flask automatically.

If you're bootstrapping a brand-new deployment and have no proctor login yet
at all, the account owner can create the very first one directly, from a
machine with AWS CLI access:

```bash
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_3aL2Ylduc \
  --username YOUR_EMAIL \
  --user-attributes Name=email,Value=YOUR_EMAIL Name=email_verified,Value=true \
  --message-action SUPPRESS --region us-east-1

aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_3aL2Ylduc \
  --username YOUR_EMAIL --password 'YourP@ssw0rd123' \
  --permanent --region us-east-1
```

Then add `YOUR_EMAIL` to `PROCTOR_EMAILS` as above.

---

## 6. Troubleshooting during a live session

| Symptom | Likely cause | Fix |
|---|---|---|
| Student sees Cognito login redirect errors | Rare, usually a one-off Cognito propagation blip | Have them retry after a minute |
| "This model has no tools" for TE/Meraki | Token not saved, or Test Connection failed | Credentials page → re-paste token → Test Connection |
| Meraki responses ask for an Organization ID | Org ID not saved | Credentials page → Meraki card → fill in Organization ID → Save |
| Chat hangs then shows a Bad Gateway / 502 | Was a gunicorn/nginx timeout bug — **fixed** (180s timeouts). If it recurs, check `⚙️ Settings` → Logs for `WORKER TIMEOUT` | Restart Flask from Settings; report if it recurs, may indicate a very slow upstream API |
| AI gives a wrong/outdated date when asked about "the last N hours" | Was a bug (model guessed the date) — **fixed**, current UTC time is now injected into every request | Shouldn't happen; if it does, note the exact prompt and report it |
| A student's file upload fails | File >60MB, or unsupported type | Supported: images, PDF, XLS/XLSX/CSV, up to 60MB total per message |
| Whole app is unreachable | EC2 instance issue | See `TECHNICAL_REFERENCE.md` Section "Emergency access" |

---

## 7. Cost while idle

The instance is a single `t3.micro` — leaving it running between sessions
costs roughly $7–8/month (EC2) + a few cents/month (Elastic IP, Route 53,
DynamoDB on-demand). Bedrock and any per-request costs only accrue when
students actually chat. There's no need to shut it down between lab sessions
unless you want to; startup/teardown isn't automated and isn't necessary given
the low idle cost.
