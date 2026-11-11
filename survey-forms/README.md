# Pre/Post-Event Survey Forms

Version-controlled backup of the two standalone survey pages students use at
the end (and start) of an AI & MCP Day event. **These are reference copies for
safety/history only — editing them here does NOT change the live site.**

## Where these actually live and run

- **Live URLs:** `https://ai.thousandeyeschannel.com/survey/pre` and `/survey/post`
- **Real files:** `/var/www/html/survey/pre.html` and `post.html` **on the EC2
  instance** (`i-02a82951f964e8576`), served directly by an nginx `alias` -
  this is a *separate* static-file location block, entirely outside the Flask
  app (`app.py` has no `/survey` route at all).
- **Not part of `deploy.sh` / git-pull.** The main app deploys via
  `git pull && systemctl restart flask-app` on every instance in the ASG (see
  `TECHNICAL_REFERENCE.md`). These two files are **not** touched by that flow
  at all - they were placed on the instance by hand and nginx just serves
  them as static content. A `git push` to `main` alone does **nothing** to
  these pages.

This mirrors the `thread_watchdog.sh` situation documented in
`TECHNICAL_REFERENCE.md` - infra/content that lives only on the instance,
invisible to normal deploys - except these files previously had **no backup
anywhere**, not even on the instance filesystem's own history. Pulled into
git here on 2026-11-11 for exactly that reason, confirmed byte-for-byte
identical to the live files via `md5sum` at the time of import.

## How each form works

Self-contained HTML + vanilla JS, no backend of its own. All questions live
in a single `QUESTIONS` array near the top of the `<script>` block - each
entry is `{id, type, title, options/low/high/descriptors, required, ...}`
depending on `type` (`dropdown`, `rating`, `text`, `multi`, `choice`,
`scale_desc`). On submit, the whole set of answers is POSTed as JSON straight
to a hardcoded Power Automate webhook URL (`WEBHOOK_URL` near the top of the
script), which writes the response into the corresponding SharePoint List -
see the `ai-day-reports` skill for which list and the exact field mapping.

## THE ONE RULE THAT MATTERS: question order is a contract

The destination SharePoint list columns are generic, positional `field_N`
names (`field_4`, `field_5`, ...) with **no semantic names of their own** -
their meaning is defined entirely by "whichever question was in that slot
when the Power Automate flow and the reporting skill's field-mapping table
were written." This means:

- **Safe to edit freely:** question wording, `placeholder` text, `subtitle`,
  rating label text (`low`/`high`), `descriptors` text. None of this affects
  field position.
- **Only safe for `question "event"` (always question #1):** adding new
  values to its `options` array (e.g. a new event location) - this changes
  what can be *selected*, not the field's position, so it's always safe
  on its own.
- **NOT safe without coordinated changes elsewhere:** adding, removing, or
  reordering a *question* anywhere in the `QUESTIONS` array. This shifts
  every `field_N` after the change point, which will silently corrupt the
  field mapping for every response collected after the edit, and the
  `ai-day-reports` skill's hardcoded field-mapping table (in this workspace's
  skills directory, not this repo) will need to be updated to match, or
  every report built after that point will misattribute answers to the
  wrong questions with no error raised anywhere.

If a structural change (not just option-list growth) is ever needed, update
the Power Automate flow's field mapping and the reporting skill's
documentation in the same change, and note the cutover date so historical
reports built on the old mapping aren't silently reread with the new one.

## How to actually deploy an edit (today - no automation exists yet)

There is currently no scripted way to push a change to the live files. Until
that's built:

1. Edit the file here in the repo (for review/history), commit, push as
   normal.
2. Manually copy the updated content to the instance via SSM, e.g.:
   ```bash
   aws ssm send-command --region us-east-1 \
     --instance-ids i-02a82951f964e8576 \
     --document-name "AWS-RunShellScript" \
     --parameters 'commands=["echo BASE64_CONTENT | base64 -d > /var/www/html/survey/post.html"]'
   ```
   (base64-encode the file locally first to avoid shell-escaping the HTML/JS).
3. Verify via `curl` against the live URL and an `md5sum` comparison against
   this repo's copy, the same way this import was verified.

A proper fix (discussed 2026-11-11, not yet built): either wire these into
`deploy.sh` as a second rsync/SSM step, or move the event dropdown's option
list to pull live from `AIAssuranceLab-Classes` instead of being hand-edited
at all.
