#!/usr/bin/env bash
# Syntax check for figma sandbox scripts.
#
# use_figma wraps a script in an async function to run it, so top-level await and return
# are both allowed. node cannot take that combination directly (CommonJS rejects await,
# ESM rejects return). So it is wrapped the same way before checking. The wrapping shifts
# error line numbers by one.
set -u
dir="$(cd "$(dirname "$0")/.." && pwd)"
fail=0
for f in "$dir"/*.js; do
  tmp="$(mktemp /tmp/figchk.XXXXXX).js"
  { echo "(async function(){"; cat "$f"; echo "})();"; } > "$tmp"
  if node --check "$tmp" 2>/tmp/figchk.err; then
    printf 'PASS  %-22s %s lines\n' "$(basename "$f")" "$(wc -l < "$f" | tr -d ' ')"
  else
    printf 'FAIL  %s\n' "$(basename "$f")"
    sed -n '1,6p' /tmp/figchk.err | sed 's/^/      /'
    fail=1
  fi
  rm -f "$tmp"
done
exit $fail
