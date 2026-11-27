---
name: factory
description: Entry point for the Software Factory - answers "what needs me" and "status", adds or parks projects, changes approval rules, and routes to setup, triage or ticket work. Use for any Software Factory request that isn't clearly setup, triage or working a single ticket.
---

# Software Factory

The factory maintains software products for a long time with a small team: tickets come in from
the team's tracker, the agent fixes, reviews, merges and verifies deploys under approval rules the
owner sets, and asks only when blocked.

- **Engine** = this plugin (skills, reviewer agent, guard hooks, `bin/` tools). Public, shared.
- **Factory home** = the owner's private folder, path in `~/.factory/config.json`. Holds
  `factory.json` (projects, trackers, approvals, budget), `policy.md`, `profile.md`,
  `decisions.md`, `memory/`, `digests/`, `setup-state.md`. Never copy anything from it into the
  plugin, a public repo, or another workspace.

No `~/.factory/config.json`, or `setup-state.md` not complete → offer `software-factory:setup`.

## Requests
| User says | Do |
|---|---|
| "set up" / "continue setup" | `software-factory:setup` |
| "work on the next ticket" / "pick up KEY-123" | `software-factory:work` |
| "run triage" | `software-factory:triage` |
| "what needs me" / "status" | Latest digests' Asks + tickets waiting on the owner + PRs waiting for approval, across active projects. Short list with links. Add `bin/factory-run status` if a run is live. |
| "usage" | `bin/factory-usage` (tokens by model, activity, project, item). |
| "add project ..." | Detect repo and stack, ask the tracker and deploy check, add to `factory.json › projects`, create `memory/<id>.md`, log in `decisions.md`. |
| "park / archive <project>" | Set its `status`, log it. Archiving a repo on GitHub needs the owner's explicit yes. |
| "change approvals: ..." | Edit `factory.json › approvals` (see `references/approvals.md`), log the decision with the owner's reason. |
| "approve <PR/ticket>" | Log it in `decisions.md`, then continue the ticket with the work skill from step 7. |

## Project entry shape
See `references/approvals.md` for `approvals`. A project in `factory.json › projects`:
```json
"shop-web": {
  "workspace": "acme",
  "status": "active",
  "repo": "acme/shop-web",
  "path": "~/work/shop-web",
  "stack": "Next.js, Postgres",
  "tracker": { "type": "jira", "project": "BA", "statuses": { "todo": "To Do", "in_progress": "In Progress", "review": "Ready for Review", "done": "Done" } },
  "deploy": { "pipeline": "deploy.yml", "url": "https://shop.example.com", "check": "GET /version returns the merge commit" }
}
```
A workspace in `factory.json › workspaces` (the guard keeps runs inside one):
```json
"acme": { "name": "Acme Textiles", "projects": ["shop-web"], "paths": ["~/work/shop-web"], "repos": ["acme/shop-web"] }
```

## Reporting
Lead with what changed and what needs the owner. Links for every PR and ticket.
