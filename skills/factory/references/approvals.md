# Approval rules

`factory.json › approvals`:
- `review`: `agent` (reviewer subagent), `human`, or `agent+human`.
- `client_replies`: `draft` (agent writes, a human sends) or `send`.
- `rules`: checked top to bottom; the first whose `when` matches decides.
  - `when.class`: any of `docs tests lint deps-minor deps-major bugfix hotfix feature refactor`.
  - `when.priority` (optional): tracker priorities, lowercased, e.g. `["low","medium"]`.
  - `when.max_lines` (optional): changed lines excluding tests.
  - `merge` and `deploy`: `auto` or `ask`.
  No rule matches → `ask`.

`policy.md › Never` and `Always ask` win over any rule.

## Presets

**cautious** (first weeks; client projects): agent fixes, opens PRs and reviews; a human merges.
```json
"rules": [ { "when": { "class": ["docs","tests","lint","deps-minor","deps-major","bugfix","hotfix","feature","refactor"] }, "merge": "ask", "deploy": "ask" } ]
```

**balanced**: low-risk work flows; anything bigger waits for a human.
```json
"rules": [
  { "when": { "class": ["docs","tests","lint","deps-minor"] }, "merge": "auto", "deploy": "auto" },
  { "when": { "class": ["bugfix"], "priority": ["lowest","low","medium"], "max_lines": 50 }, "merge": "auto", "deploy": "auto" },
  { "when": { "class": ["bugfix","hotfix","feature","refactor","deps-major"] }, "merge": "ask", "deploy": "ask" }
]
```

**autonomous**: the agent merges and deploys whatever passes CI and review; asks only for the
`policy.md › Always ask` list.
```json
"rules": [ { "when": { "class": ["docs","tests","lint","deps-minor","deps-major","bugfix","hotfix","feature","refactor"] }, "merge": "auto", "deploy": "auto" } ]
```
