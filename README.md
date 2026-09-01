# AI Assurance Lab

A web app for students to learn network troubleshooting with Claude AI, using
live MCP (Model Context Protocol) integrations to ThousandEyes, Meraki, and
(optionally) Splunk.

**Live at: https://ai.thousandeyeschannel.com**

- Running a lab session (adding students, credentials, troubleshooting)?
  → [`PROCTOR_GUIDE.md`](./PROCTOR_GUIDE.md)
- Working on the app / deploying a code change / architecture details?
  → [`TECHNICAL_REFERENCE.md`](./TECHNICAL_REFERENCE.md)

## Features

- Email-based login via AWS Cognito, each student manages their own
  encrypted API credentials — never shared, never sent to the frontend
- Claude (Sonnet 4.5) via AWS Bedrock, with agentic multi-step tool use
- ThousandEyes and Meraki via Cisco's hosted MCP servers; Splunk via a
  user-supplied MCP server URL
- File attachments (images, PDF, Excel/CSV) and downloadable HTML report
  generation in chat
- In-app lab guide sidebar with pop-out tab
- Proctor tools built into the app: bulk/single student add via CSV/Excel,
  system status, logs, restart, and git-pull-to-deploy — no AWS CLI needed
  day-to-day

## Local development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in Cognito, DynamoDB, encryption key, etc.
./START_DEV.sh          # or: python3 app.py
```

Visit `http://localhost:5000`. See `TECHNICAL_REFERENCE.md` for the full
architecture, environment variables, and how the production instance is
deployed and updated.

## Project layout

```
app.py                 Flask app: routes, auth, chat/tool-use loop, admin APIs
dynamo_db.py           DynamoDB CRUD + per-service connectivity tests
mcp_client.py          MCP client (Streamable HTTP) for TE/Meraki/Splunk
crypto.py              Fernet encryption for stored tokens
attachments.py         In-memory file upload processing for chat
templates/             lab.html, credentials.html, guide.html, admin_*.html
ec2-setup.sh           One-time EC2 bootstrap script
```

Resetting students between cohorts is done via the **Students** admin page in
the app (Delete All + bulk re-upload), not a CLI script — see
`PROCTOR_GUIDE.md`.
