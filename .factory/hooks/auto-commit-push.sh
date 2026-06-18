#!/usr/bin/env bash
# Stop-hook: commit and push everything when Droid finishes responding.
set -euo pipefail

REPO_DIR="${FACTORY_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
cd "$REPO_DIR"

# Only act inside a git repo.
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

# Nothing to do if the working tree is clean.
if [ -z "$(git status --porcelain)" ]; then
  exit 0
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"

git add -A
git commit -m "chore: auto-commit on stop hook ($(date -u +%Y-%m-%dT%H:%M:%SZ))

Co-authored-by: factory-droid[bot] <138933559+factory-droid[bot]@users.noreply.github.com>"

git push origin "$BRANCH"
