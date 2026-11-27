#!/bin/sh
# Maintainers: run once per clone. Blocks commits that fail the privacy check.
set -eu
hook="$(git rev-parse --git-path hooks)/pre-commit"
printf '#!/bin/sh\nexec sh "$(git rev-parse --show-toplevel)/scripts/privacy-check.sh"\n' > "$hook"
chmod +x "$hook"
echo "installed $hook"
