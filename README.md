# Software Factory

Maintain many software products with a small team, using Claude Code.

A client reports a bug in Jira or GitHub Issues. The factory picks it up, moves it to In Progress,
fixes it on a branch with a test, opens a PR, has a separate reviewer agent check it, merges and
verifies the deploy **when your approval rules allow**, moves the ticket to Done and replies.
It asks you only when it's blocked.

> Status: early (0.1). The ticket loop, setup interview, approval rules and safety guard work;
> more channels and monitors are coming.

## Install

Paste this into Claude Code:

```
Install the Software Factory plugin from github.com/Abhinivesh2729/software-factory-plugin and set it up for me.
```

Or by hand:

```bash
claude plugin marketplace add Abhinivesh2729/software-factory-plugin
claude plugin install software-factory@software-factory
```

Then say **"set up the software factory"**. Claude interviews you: what you maintain, where tickets
land, your stack, CI/CD and how much it may do alone. Skip anything; it guides you through what you
don't know and picks up later.

## What you can say

| Say | What happens |
|---|---|
| set up the software factory | Setup interview (resumable) |
| work on the next ticket / pick up BA-2408 | One ticket end to end |
| run triage | Sweep all channels for one workspace, act, digest |
| what needs me | Open asks, PRs waiting, blocked tickets |
| change approvals: auto-merge low priority bugs | Updates your rules |

## Your data stays yours

- **This plugin** is the engine: skills, a reviewer agent, guard hooks, small tools. It holds no
  customer data.
- **Your factory home** (default `~/factory`, created during setup) holds your projects, approval
  rules, decisions and memory. Keep it in a **private** repo. Its path is in `~/.factory/config.json`.
- Run state, token ledger and audit log live in `~/.factory/` on your machine.
- Each factory run serves **one workspace** (a client or product line). The guard blocks a run from
  touching another workspace's repos or folders.

## Approval presets

- **cautious**: agent fixes, opens PRs, reviews; a human merges. Start here.
- **balanced**: docs, tests, minor dependency bumps and small low-priority bug fixes merge and
  deploy on green CI; the rest waits for a human.
- **autonomous**: everything that passes CI and review merges; asks only for risky changes
  (new dependencies, auth, CI files, money, deletion).

Never, in any preset: force-push, tag releases, delete repos or branches, change repo settings,
bypass required checks.

## Safety guard

The plugin's hooks are inactive in normal sessions. During a factory run (`factory-run start`) they
enforce time and token budgets, stop loops (same call repeated), block destructive commands, keep the
run inside one workspace, and write an audit log. Limits are in `factory.json › budget`.

## Running when your laptop is off

The factory runs wherever Claude Code runs: your machine (scheduled tasks), an always-on box, or
GitHub Actions triggered by ticket events. Setup explains the options.

## Contributing

Maintainers: run `sh scripts/install-git-hook.sh` once. Every commit then runs
`scripts/privacy-check.sh`, which blocks secrets, absolute home paths and anything in your private
pattern list (`~/.factory/private-patterns.txt`, never committed).

MIT licence.
