#!/bin/sh
# PostToolUse hook (user level): append one JSON line per tool call to ~/.factory/audit/YYYY-MM.jsonl,
# only for factory operator runs (sessions that ran `factory-run start`). Never records tool output.
input="$(cat)"
sid="$(printf '%s' "$input" | jq -r '.session_id // empty' 2>/dev/null)"
[ -n "$sid" ] && [ -f "$HOME/.factory/run/$sid.json" ] || exit 0
grep -q '"engine": "software-factory-plugin"' "$HOME/.factory/run/$sid.json" || exit 0
dir="$HOME/.factory/audit"
mkdir -p "$dir"
printf '%s' "$input" | jq -c '{ts: (now | todate), session: .session_id, cwd: .cwd, tool: .tool_name,
        input: (.tool_input | tostring | .[0:400])}' >> "$dir/$(date +%Y-%m).jsonl" 2>/dev/null
exit 0
