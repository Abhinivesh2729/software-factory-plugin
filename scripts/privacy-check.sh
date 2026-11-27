#!/bin/sh
# Fails if any tracked file contains a pattern from the maintainer's PRIVATE list.
# The list lives outside the repo (default ~/.factory/private-patterns.txt, one
# case-insensitive regex per line) so the patterns themselves are never published.
# Also blocks common secret shapes. Run before every commit/push (see scripts/install-git-hook.sh).
set -eu
root="$(git rev-parse --show-toplevel)"
list="${FACTORY_PRIVATE_PATTERNS:-$HOME/.factory/private-patterns.txt}"
fail=0
cd "$root"
files="$(git ls-files -co --exclude-standard)"
check() {
  # $1 = regex, $2 = label
  hits="$(printf '%s\n' "$files" | xargs grep -n -i -E -e "$1" -- 2>/dev/null | grep -v '^scripts/privacy-check.sh:' || true)"
  if [ -n "$hits" ]; then echo "PRIVACY: $2"; printf '%s\n' "$hits" | sed 's/^/  /'; fail=1; fi
}
check 'sk-ant-[a-z0-9_-]{10,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|xox[bp]-[A-Za-z0-9-]{10,}|ATATT[A-Za-z0-9_-]{20,}' "secret-looking token"
check '/Users/[a-z0-9._-]+/|/home/[a-z0-9._-]+/' "absolute home path"
if [ -f "$list" ]; then
  while IFS= read -r p; do
    case "$p" in ''|'#'*) continue;; esac
    check "$p" "private pattern (from $list)"
  done < "$list"
else
  echo "NOTE: no private pattern list at $list; only generic checks ran."
fi
[ "$fail" = 0 ] && echo "privacy check: clean" || { echo "privacy check: FAILED"; exit 1; }
