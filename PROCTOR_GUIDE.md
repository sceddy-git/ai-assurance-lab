# AI Assurance Lab — Proctor Guide

This is the **single source of truth** for running the lab. Everything else you might
find in this repo's git history (Docker/AppRunner/CodeBuild instructions, multiple
overlapping README files) is obsolete — the lab now runs on an always-on Auto
Scaling Group behind a load balancer (1-3 EC2 instances, scaling with class
load), managed entirely through the web app or AWS CLI/SSM. No Docker, no CI/CD
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
| AI backend | AWS Bedrock, Claude Haiku 4.5 |
| Credential storage | Encrypted per-user in DynamoDB (`AIAssuranceLab-UserMCPCredentials`) |
| MCP integrations | ThousandEyes (hosted), Meraki (hosted), Splunk (student/facilitator-provided URL) |
| Class scheduling | `/admin/classes` - QR self-registration per class, roster view, disable/TE-cleanup actions |
| Infra | Auto Scaling Group `ai-assurance-lab-asg` (1-3x `m6i.large` behind ALB `ai-assurance-lab-alb`, scales on CPU), Nginx + Let's Encrypt TLS, Flask/Gunicorn via systemd, managed via AWS SSM (no SSH). See `TECHNICAL_REFERENCE.md` for the full infra table. |

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

### 2.3.5 Schedule a class with QR self-registration (optional alternative to 2.1)

Instead of (or in addition to) uploading a roster yourself, you can let
students register themselves by scanning a QR code. Go to
**🏫 Classes** (`/admin/classes`):

1. **Create Class** — name, date, location. This generates a unique join
   link/QR code for that specific class only.
2. Click **QR** on the class row to display/print/project the QR code.
   Students scan it, fill in name/company/email, and get a Cognito login
   the same way as any other student (temp password emailed via SES) —
   fully self-service, nothing for you to click per student.
3. Click **Roster** to see who's joined, their company, and their TE/Meraki/
   Splunk connection status for that class.
4. **When the class is over**, from the Roster view:
   - **Disable Class Access** — soft-disables login for every enrolled
     student in one click. Their credentials, chat history, and progress
     are all kept; you (or they) can be re-enabled anytime from
     `/admin/students` (per-student Enable/Disable button in the last
     column).
   - **Delete ThousandEyes Account Groups** — a **separate, destructive**
     action that permanently deletes each student's auto-provisioned
     ThousandEyes Account Group and user (see 2.3.6). Only use this once
     you're sure you don't need those TE sandboxes anymore — there's no
     undo.

Classes and self-registration work independently of the Delete All
Students / bulk-upload flow in 2.1-2.2 - you can mix both approaches across
different cohorts.

### 2.3.6 Auto-provisioned ThousandEyes accounts (optional)

If the super admin (`sceddy@cisco.com`) has saved their **own** ThousandEyes
token on their own Credentials page, every student who self-registers via a
class QR code automatically gets their **own** dedicated ThousandEyes
Account Group + login (scoped to just that group, via the "Account Admin"
role) - in addition to their AI Assurance Lab account. There's no separate
admin-token setting anywhere in `.env` — it deliberately reuses that one
personal token instead. This is separate from the ThousandEyes *personal
token* each student pastes into their own Credentials page for the chat's
MCP integration - that's still needed either way.

**Hard org lock:** this only ever works against the ThousandEyes
organization named exactly **"AI-Powered Network Observability Day"**. If
the super admin's saved token belongs to any other organization, every
auto-provisioning attempt is refused (logged, never silently ignored) and
the `/admin/classes` page shows a warning banner. This lock is in code
(`thousandeyes_admin.py`), not configurable via `.env` — it cannot
accidentally point at the wrong org.

If no valid token is available, class scheduling and QR signup still work
fine; students just won't get an auto-created ThousandEyes account.

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
| A student's QR signup says "Link not available" | The class was disabled/deleted, or the QR is from an old class | Create a new class and re-share its QR code |
| Some students get "Too many signup attempts from this network" while scanning the QR together | Anti-bot rate limit on the public join page, keyed by IP — everyone on the same venue Wi-Fi shares one IP. Raised to 100/hour on 2026-09-27 specifically to cover a full ~40-student class, but a very large or slow-trickling cohort could still theoretically hit it | Wait a few minutes and retry, or have the last few students join from cellular data / a different network |
| Registration feels slow when many students join at once | Gunicorn now runs 2 workers × 6 threads (12 concurrent slots) so a burst just queues briefly instead of failing — with ~40 students it may take a couple of minutes to fully drain, that's expected | No action needed; if it takes much longer than that, check `⚙️ Settings` → Logs for repeated ThousandEyes API errors slowing down provisioning |
| ThousandEyes account group wasn't created for a QR signup | The super admin hasn't saved a ThousandEyes token on their own Credentials page, that token belongs to a different org than "AI-Powered Network Observability Day", or the API call failed (check `⚙️ Settings` → Logs) | Cognito login still works either way; the student can be provisioned manually later, or just use their own TE token on the Credentials page as normal |

---

## 7. Student-facing features added since this guide was last reviewed (Nov 2026)

These don't require you to do anything to enable, but are useful to know
about when a student asks:

- **Collapsed "explainer" rows in chat** — each tool call (🔧) and
  reasoning step (💭) Claude takes is shown as a collapsible row above its
  final answer, so students can inspect exactly which MCP tool was called
  and with what inputs. The Lab Guide tells students about this.
- **Token usage badge** — students see a progress bar in the sidebar
  tracking their cumulative token usage against a **10M token soft
  budget**. This is informational only — it never blocks chat, even if a
  student goes over. You can see every student's running total on the
  `/admin/progress` dashboard (new "Tokens" column), color-coded amber at
  80% and red at 95% of budget, in case anyone is burning through usage
  unusually fast.
- **End-of-lab feedback nudge** — after a student completes *any* lab
  checkpoint (not just the last one in a module), the chat asks "did you
  enjoy this lab?" once per lab per student. Replies are recorded to
  DynamoDB and visible on `/admin/progress` (feedback table now has a
  "Lab" column showing which specific lab each comment is about).
- **Post-event survey link** — the "My Progress" sidebar now shows a link
  to the anonymous post-event survey (`/survey/post`) after a student's
  module checklists.
- **Docked, resizable Lab Guide** — the Lab Guide is now docked to the left
  of the chat by default (not a pop-out tab you have to click to open), and
  students can drag the divider between the guide and chat to resize it.
  Their chosen width is remembered across reloads.
- **Create a Class entry for every cohort, even CSV-only ones.** The
  post/pre-event survey's "which event did you attend?" dropdown (Question
  1) is now synced live to whatever locations exist in `/admin/classes` —
  you don't need to actually share the QR code or use self-registration,
  just creating the Class entry (Section 2.3.5) is enough for its location
  to show up in the survey. If you only bulk-upload a roster via
  `/admin/students` and never create a matching Class entry, that cohort's
  location won't appear as a survey option.

## 8. Cost while idle

Since the 2026-11-09 move to an Auto Scaling Group behind an ALB, the floor
cost is higher than the old single `t3.micro`: the ASG normally runs **one**
`m6i.large` instance at idle (desired capacity 1, scaling up to 3 only when
class load pushes average CPU above the 55% target), plus the ALB itself
(hourly charge + LCU usage) and DynamoDB on-demand. Bedrock and any
per-request costs only accrue when students actually chat. There's no need to
scale the ASG down to 0 between lab sessions unless you want to; nothing
about idle scale-to-zero is automated, so leaving it as-is is the simplest
default given class sessions can be scheduled with little notice.

A pre-ASG standalone EC2 instance (`i-09cdb070a8b829165`) was left running
after the Nov 9 migration, fully orphaned from live traffic — it was stopped
on 2026-11-13 and its Elastic IP released (pending termination). If you ever
see an EC2 instance that isn't a member of `ai-assurance-lab-asg`, treat it
as leftover and safe to investigate for shutdown the same way.
