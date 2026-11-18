#!/usr/bin/env bash
# Fails when a double-quoted sentence in a tutorial matches a literal in gateway or App Shell source.
# Canned responses are literals in that source. A tutorial that quotes one describes output the
# code returns as fixed text (TASK-0658). Usage: check_tutorial_strings.sh [tutorial.md ...]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ $# -eq 0 ]]; then
  set -- docs/tutorials/02-running-your-first-session.md
fi

status=0
check_sentence() {
  local tutorial="$1" sentence="$2"
  if grep -rqF --exclude-dir=node_modules -- "$sentence" gateway/api/src frontend/src; then
    echo "FAIL: $tutorial quotes text that the source returns as a literal: $sentence" >&2
    status=1
  fi
}

for tutorial in "$@"; do
  while IFS= read -r quoted; do
    body="${quoted:1:${#quoted}-2}"
    # Check each sentence on its own. Source literals often hold one sentence each.
    while IFS= read -r sentence; do
      if (( ${#sentence} >= 12 )); then
        check_sentence "$tutorial" "$sentence"
      fi
    done < <(printf '%s\n' "$body" | sed -e 's/\. /.\n/g')
  done < <(grep -oE '"[^"]{12,}"' "$tutorial" || true)
done

if [[ $status -eq 0 ]]; then
  echo "OK: no tutorial quotes a source literal"
fi
exit "$status"
