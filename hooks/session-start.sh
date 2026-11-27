#!/bin/sh
# SessionStart: if the setup interview was started but not finished, remind Claude once per day
# so it can offer (not force) to continue. Silent otherwise.
cfg="$HOME/.factory/config.json"
[ -f "$cfg" ] || exit 0
home="$(sed -n 's/.*"home"[^"]*"\([^"]*\)".*/\1/p' "$cfg" | head -1)"
case "$home" in "~/"*) home="$HOME/${home#~/}";; esac
state="$home/setup-state.md"
[ -f "$state" ] || exit 0
grep -q '^status: complete' "$state" && exit 0
stamp="$HOME/.factory/.setup-reminded"
today="$(date +%Y-%m-%d)"
[ "$(cat "$stamp" 2>/dev/null)" = "$today" ] && exit 0
printf '%s' "$today" > "$stamp"
echo "Software Factory setup is not finished (see $state). If the user's request allows, offer once, in one line, to continue the setup interview with the software-factory:setup skill. Don't push."
exit 0
