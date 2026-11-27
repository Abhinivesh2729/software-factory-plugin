# Connecting channels

Each channel needs a few abilities: **read** new tickets, **comment**, **change status**,
**assign**, **close**. Use whatever is already connected; check before asking the user to do anything.

## GitHub (code host and/or tracker)
- Check: `gh auth status`. If it fails, tell the user to run `gh auth login` in their terminal
  (browser login, no token pasted in chat).
- Verify: `gh repo view <owner>/<repo> --json name,defaultBranchRef`.
- Tracker statuses on GitHub are labels: create `factory:in-progress`, `factory:review`,
  `factory:done` with `gh label create <name> -R <repo> --force`.
- Agent identity: a separate GitHub machine user is optional. Most teams use the owner's account
  and label factory work.

## Jira / Jira Service Management
Two ways; pick with the user.

**A. Atlassian connector (easiest).** In the Claude app: Settings → Connectors → Atlassian → Connect,
sign in, allow access. In Claude Code the tools then appear as `mcp__*Atlassian*__*`
(search tools for "jira" if unsure). Actions show up as **whoever signed in to the connector**.

**B. Jira REST with an agent account (shows the agent as its own user).**
1. In Jira, invite a new user with a mailbox you control, e.g. `factory-agent@yourcompany.com`,
   display name of their choice ("Factory Agent", or any name). On Jira Cloud Free this uses one of
   10 seats.
2. Log in as that user once at id.atlassian.com → Security → API tokens → Create token.
3. The user stores it outside chat as environment variables `JIRA_BASE_URL`, `JIRA_EMAIL`,
   `JIRA_API_TOKEN` (shell profile, a secrets manager, or the CI secret store).
4. Verify: `curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" "$JIRA_BASE_URL/rest/api/3/myself"` returns
   the agent's display name.
Useful calls: search `GET /rest/api/3/search/jql?jql=...`, transitions
`GET|POST /rest/api/3/issue/<KEY>/transitions`, comment `POST /rest/api/3/issue/<KEY>/comment`,
assign `PUT /rest/api/3/issue/<KEY>/assignee`.

Either way:
- Read the project's workflow statuses and transition names; map them in `factory.json`
  (`tracker.statuses`: todo, in_progress, review, done).
- To change status, list the issue's transitions first and use the matching transition id.
- Jira Service Management: customer-visible replies are "Reply to customer" comments; internal
  notes are internal comments. Respect `client_replies: draft` (internal note with the draft).

## Email
Gmail connector (Settings → Connectors → Gmail) lets the agent read a support inbox or label and
draft replies. Each new report becomes a ticket in the project's tracker with a link back to the
thread. Replies go back as drafts unless `client_replies` is `send`.

## WhatsApp
Personal WhatsApp can't be automated within WhatsApp's rules. Options: WhatsApp Business Platform
(Cloud API, needs Meta business verification and a dedicated number) feeding a webhook, or the
team forwards client messages to the support email. Mark as `skipped` unless the user already has
the Business Platform.

## Error monitoring (optional)
Sentry, Crashlytics, uptime checks: if a connector or CLI is available, the triage skill turns new
production errors into tickets. Otherwise skip.

## Deploy verification
Record in `factory.json › projects.<id>.deploy`:
`{"pipeline": "<workflow file or name>", "url": "<live URL>", "check": "<what proves the new version is live>"}`.
Examples of `check`: a `/version` endpoint returning the commit SHA, a string that only exists in
the new code, or the deploy job's success plus a 200 from the URL.
