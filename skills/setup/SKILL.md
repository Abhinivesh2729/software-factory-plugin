---
name: setup
description: Set up the Software Factory for the user - a friendly interview that learns their products, ticket systems, stack, CI/CD and approval preferences, connects what's missing step by step, and creates their private factory home. Use right after the plugin is installed, when the user says "set up the software factory", or to continue an unfinished setup.
---

# Software Factory setup

You are a companion, not a form. The user may be a solo founder or a team lead; they may not know
every answer. Your job is to leave them with a working factory for **one project end to end**, then
widen it later.

## Rules for the interview
- **Detect before you ask.** Check what you can see yourself first, and only ask what you can't find.
- **One or two questions at a time**, in plain words. Offer likely answers as choices.
- **Every question is skippable.** "Skip", "not sure" or silence is fine: mark it `skipped` or
  `unknown` in `setup-state.md` and move on. Never ask the same thing twice in one session.
- **"I don't know" gets guidance**, not a lecture: tell them exactly where to find it or what to
  click, then wait for "done". If it needs someone else (an admin, a client), note it and move on.
- **Never ask for secrets in chat** (passwords, API tokens). Tell the user where to put them
  (an environment variable, their password manager, a connector sign-in) and verify by use.
- **Verify every connection with a real read** before marking it `answered`.
- Save progress in `setup-state.md` after each answer, so setup survives a closed session.
- Keep it short. A first setup should take 10 to 20 minutes.

## Step 0: where things live
Explain in two lines: the plugin is the engine (public, shared); the **factory home** is their
private folder with their config, policy, decisions and memory. Nothing of theirs goes into the plugin.

- If `~/.factory/config.json` exists, read it, open the home, and resume from `setup-state.md`.
- Otherwise propose `~/factory` (or a folder they name), copy `templates/home/` from this plugin
  (two levels up from this skill's folder) into it, `git init` it, and write
  `~/.factory/config.json` as `{"home": "<path>"}`. Suggest a **private** git remote later.

## Step 1: what they maintain
Ask what they look after: products, client projects, or both. For each, gather (detect first):
- Repo: try `gh repo list --limit 50` and local folders; ask them to pick.
- Stack: read the repo (package.json, pubspec.yaml, go.mod, *.csproj, requirements.txt...). Confirm, don't quiz.
- Workspace: group projects by client or product line. One factory run serves one workspace, so
  one client's code and tickets never leak into another's run.

Start with **one** project for the first loop. Others go in as `status: "later"`.

## Step 2: where tickets land
Ask where bug reports and requests arrive today: GitHub Issues, Jira / Jira Service Management,
email, WhatsApp, other. Then follow `references/connectors.md` for each one to connect and verify.
Every project needs exactly **one work tracker** (GitHub Issues or Jira). Other channels (email,
WhatsApp) feed tickets into it.

Ask how the agent should appear in the tracker: a separate user such as "Factory Agent" (their
choice of name) is clearest for the team. The connectors reference explains how.

Ask for the workflow statuses (To Do, In Progress, Ready for Review, Done or their names) by
reading them from the tracker, and confirm.

## Step 3: CI/CD and "is it really fixed"
Detect workflows (`.github/workflows/*`, other CI files). Ask how a merge reaches production and
how to check the live version (URL, health endpoint, a version string, a deploy dashboard).
If there is no automated deploy, say so plainly: the factory can still fix and merge, but "verified
in production" needs a pipeline. Offer to set one up later as a separate task; don't do it now.

## Step 4: approvals
Explain the three presets in `../factory/references/approvals.md` in one line each and recommend
**cautious** for the first week. Ask: who reviews PRs (agent, human, both)? May the agent reply to
clients or only draft? Write the result into `factory.json › approvals`.

## Step 5: how to reach them
Ask how they want asks: Claude app push notification (default), the tracker (a comment mentioning
them), or email. Ask only when blocked, at most a few yes/no questions at a time.

## Step 6: always-on (explain, don't force)
The factory runs when Claude Code runs. Explain the options in plain words and let them choose
(or skip for now):
1. **This machine** - scheduled tasks in the Claude desktop app; works while it's on and awake.
2. **A small always-on machine or VM** running Claude Code.
3. **GitHub Actions** - Claude Code runs on GitHub when a ticket or label event happens; no
   machine of theirs needs to be on. Needs an API key or a Claude token stored as a repo secret.
Record the choice; setting it up is a follow-up task.

## Step 7: dry run, then live
With `mode: "dry-run"`, run the `software-factory:work` skill on one real ticket: it reports what
it would do without writing anything. Walk the user through the result. When they're happy, set
`mode: "live"` and log it in `decisions.md`. Set `status: complete` at the top of `setup-state.md`
only when one project has a verified tracker, repo access and approval preset.

## Finish
Summarise in a few lines: what's connected, what's skipped (and how to finish it later), and the
commands they can say from now on: "work on the next ticket", "run triage", "what needs me",
"continue setup".
