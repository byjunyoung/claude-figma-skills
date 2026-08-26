#!/usr/bin/env bash
# figma 샌드박스 스크립트 문법 검사.
#
# use_figma 는 스크립트를 async 함수로 감싸 실행하므로 top-level 의 await 와 return 이
# 둘 다 허용된다. node 는 그 조합을 직접 못 받는다(CommonJS 는 await 거부, ESM 은 return 거부).
# 그래서 같은 방식으로 감싼 뒤 검사한다. 감싸느라 오류 줄 번호가 1 밀린다.
set -u
dir="$(cd "$(dirname "$0")/.." && pwd)"
fail=0
for f in "$dir"/*.js; do
  tmp="$(mktemp /tmp/figchk.XXXXXX).js"
  { echo "(async function(){"; cat "$f"; echo "})();"; } > "$tmp"
  if node --check "$tmp" 2>/tmp/figchk.err; then
    printf 'PASS  %-22s %s줄\n' "$(basename "$f")" "$(wc -l < "$f" | tr -d ' ')"
  else
    printf 'FAIL  %s\n' "$(basename "$f")"
    sed -n '1,6p' /tmp/figchk.err | sed 's/^/      /'
    fail=1
  fi
  rm -f "$tmp"
done
exit $fail
