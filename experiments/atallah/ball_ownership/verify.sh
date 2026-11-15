#!/usr/bin/env bash
# Runs farabi over every claims file in claims/ and prints one line per file: verdict, receipt hash,
# reasons, exit code. Deterministic checks only (--no-llm; farabi.yaml also has llm.enabled false).
#
#   experiments/atallah/ball_ownership/verify.sh            # all claims/*.md except README.md
#   experiments/atallah/ball_ownership/verify.sh proofs.md  # one file (name inside claims/, or a path)
#
# Target form: `farabi verify text:<file>`. The claims files are plain text, and the `text:` source
# checks file:line citations and runs allowlisted test commands against the files on disk, committed
# or not (farabi.yaml policy `claims-text`). The alternative for uncommitted work,
# `farabi verify git:worktree --message <file>`, treats every untracked file in the repo as the
# change, so while farabi.yaml itself is untracked its integrity check reports a protected-file edit
# and every verdict is needs_human. Switch to git:worktree once the tree is committed.
#
# Exit code: the worst verdict seen (0 pass, 1 fail, 2 needs_human, 3 error).
set -u
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/../../.." && pwd)"
cd "$root" || exit 3

if [ $# -gt 0 ]; then
  files=()
  for f in "$@"; do
    case "$f" in */*) files+=("$f") ;; *) files+=("$here/claims/$f") ;; esac
  done
else
  files=("$here"/claims/*.md)
fi

worst=0
for f in "${files[@]}"; do
  [ "$(basename "$f")" = "README.md" ] && continue
  [ -f "$f" ] || { echo "missing: $f"; worst=3; continue; }
  case "$f" in /*) rel="${f#$root/}" ;; *) rel="$f" ;; esac
  out="$(farabi verify "text:$rel" --json --no-llm 2>&1)"
  code=$?
  if json="$(printf '%s' "$out" | python3 -c '
import json, sys
raw = sys.stdin.read()
r = json.loads(raw[raw.index("{"):])
reasons = r.get("reasons") or []
print(r.get("verdict", "?"), r.get("hash", "?"), "|", "; ".join(str(x) for x in reasons)[:300] or "-")
' 2>/dev/null)"; then
    echo "$rel: $json (exit $code)"
  else
    echo "$rel: exit $code (no JSON receipt)"; echo "$out" | tail -5
  fi
  [ "$code" -gt "$worst" ] && worst=$code
done
exit $worst
