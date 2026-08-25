#!/usr/bin/env bash
# claude-figma-skills 설치
#
#   git clone https://github.com/byjunyoung/claude-figma-skills /tmp/cfs && /tmp/cfs/install.sh
#
# 하는 일 — 전제 확인 → 스킬 10개와 공용 층 복사 → 설정 씨앗 배치 → 정합성 검사.
# 이미 있는 스킬은 덮어쓰기 전에 묻는다.
set -u

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
CONF="$HOME/.claude/figma-conventions.yaml"
SKILLS=(figma-setup figma-read figma-prep figma-arrows figma-lint
        figma-tokens figma-sync figma-diff figma-proto figma-code)

say() { printf '%s\n' "$*"; }
warn() { printf '  ! %s\n' "$*"; }

say "== 전제 확인 =="
missing=0
command -v python3 >/dev/null || { warn "python3 없음 — 설정 해석에 필요합니다"; missing=1; }
command -v node    >/dev/null || { warn "node 없음 — 스크립트 문법 검사에 필요합니다"; missing=1; }
if command -v python3 >/dev/null; then
  python3 -c 'import yaml' 2>/dev/null || { warn "PyYAML 없음 — pip3 install pyyaml"; missing=1; }
fi
[ "$missing" = 0 ] && say "  python3 · PyYAML · node  OK"
say "  Figma MCP 플러그인(plugin:figma) 연결은 Claude Code 안에서 따로 확인하세요"
say ""

say "== 복사 =="
mkdir -p "$DEST" || { warn "$DEST 를 만들 수 없습니다"; exit 1; }

copy_dir() {                      # $1 = 디렉터리 이름
  local name="$1" src="$SRC/$1" dst="$DEST/$1"
  [ -d "$src" ] || { warn "원본 없음: $name"; return 1; }
  if [ -e "$dst" ]; then
    printf '  %s 이(가) 이미 있습니다. 덮어쓸까요? [y/N] ' "$name"
    read -r a </dev/tty || a=n
    case "$a" in y|Y) ;; *) say "  건너뜀: $name"; return 0 ;; esac
  fi
  rm -rf "$dst" && cp -R "$src" "$dst" && say "  설치: $name"
}

copy_dir _figma-common
for s in "${SKILLS[@]}"; do copy_dir "$s"; done
say ""

say "== 설정 =="
mkdir -p "$(dirname "$CONF")"
if [ -f "$CONF" ]; then
  say "  이미 있음: $CONF  (건드리지 않습니다)"
elif cp "$SRC/_figma-common/conventions.example.yaml" "$CONF"; then
  say "  씨앗 배치: $CONF"
  say "  ! 이건 내장 기본값입니다. 대상 파일에서 /figma-setup 을 돌려 관례를 채우세요 —"
  say "    그 전까지는 네이밍·간격·색이 남의 팀 기준으로 돕니다."
else
  warn "설정 씨앗을 배치하지 못했습니다: $CONF"
fi
say ""

say "== 검사 =="
if command -v python3 >/dev/null && python3 -c 'import yaml' 2>/dev/null; then
  CLAUDE_SKILLS_DIR="$DEST" python3 "$DEST/_figma-common/verify.py" || warn "정합성 검사에서 위반이 나왔습니다"
else
  warn "전제가 갖춰지지 않아 건너뜁니다"
fi
say ""
say "다음 세션부터 /figma-setup · /figma-lint 로 부를 수 있습니다."
