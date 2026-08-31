#!/usr/bin/env bash
# Every check CI runs, in one command.
#
#     bash tools/verify-all.sh
#
# The list of checks lives here and nowhere else. .github/workflows/verify.yml calls this script,
# so the local command and CI can no longer disagree about what gets run — which is how a red build
# got through once: the workflow knew about a fixture the local command never touched.
#
# Nothing is listed by hand. It discovers tools/verify.py, each plugin's script-syntax check, and
# every *.test.py / *.test.js / *.test.mjs under tools/test and plugins/ — so a new fixture runs in
# CI the moment it is committed, with no workflow edit.
#
# Unlike the workflow it replaces, a failure does not stop the run: everything that is broken shows
# up in one pass. Exit code 0 pass / 1 any failure.
set -uo pipefail
cd "$(dirname "$0")/.."

in_ci() { [ -n "${GITHUB_ACTIONS:-}" ]; }

failed=()
total=0
run() {  # run <label> <command...>
    local label=$1; shift
    total=$((total + 1))
    if in_ci; then echo "::group::$label"; else echo; echo "── $label"; fi
    "$@" || failed+=("$label")
    if in_ci; then echo "::endgroup::"; fi
    return 0
}

run "repository consistency" python3 tools/verify.py

# Each plugin may keep a syntax check for the scripts it hands to a sandbox
for f in plugins/*/_common/scripts/lib/check.sh; do
    [ -f "$f" ] || continue
    run "script syntax — ${f#plugins/}" bash "$f"
done

while IFS= read -r f; do
    case "$f" in
        *.test.py) run "$f" python3 "$f" ;;
        *)         run "$f" node --test "$f" ;;
    esac
done < <(find tools/test plugins \
    \( -name '*.test.py' -o -name '*.test.js' -o -name '*.test.mjs' \) \
    -not -path '*/node_modules/*' | sort)

echo
echo "============================================================"
if [ ${#failed[@]} -eq 0 ]; then
    echo "$total checks · PASS"
else
    printf 'FAILED  %s\n' "${failed[@]}"
    echo "${#failed[@]} of $total checks failed · FAIL"
    exit 1
fi
