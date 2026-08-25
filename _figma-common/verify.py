#!/usr/bin/env python3
"""figma-* 스킬 묶음 정합성 검사.

    python3 ~/.claude/skills/_figma-common/verify.py

스킬을 고친 뒤 이걸 돌린다. `plugin eval` 이 얼리 액세스라 못 쓰는 동안의 회귀 게이트다.
검사하는 것은 '문서와 실제가 어긋났는가' 하나다 —
스킬이 참조하는 설정 키가 스키마에 없거나, 가리키는 스킬이 없거나, 고유값이 남았거나.

종료 코드 0 통과 / 1 위반.
"""
import json, re, subprocess, sys
from pathlib import Path

SKILLS = Path.home() / ".claude" / "skills"
COMMON = SKILLS / "_figma-common"
EXAMPLE = COMMON / "conventions.example.yaml"
TEAM = Path.home() / ".claude" / "figma-conventions.yaml"
NAMES = ["figma-arrows", "figma-code", "figma-diff", "figma-lint", "figma-prep",
         "figma-proto", "figma-read", "figma-setup", "figma-sync", "figma-tokens"]

# 팀·환경 고유값. **패턴을 하나씩 따로 돌린다** — 여럿을 | 로 이어 붙이면
# 이스케이프가 꼬여 조용히 0 을 낸다(실측으로 한 건을 놓쳤다).
TEAM_STRINGS = ["8306FF", "XDS", "1560", "BarisON", "[UI]", "[Update]",
                "바리스", "라운지", "36131847b3e5", "매 실행 시 fetch"]

fails, warns = [], []


def leaf_paths(o, prefix=""):
    if isinstance(o, dict) and o:
        for k, v in o.items():
            p = f"{prefix}.{k}" if prefix else k
            yield p
            yield from leaf_paths(v, p)


def main():
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML 필요")

    if not EXAMPLE.exists():
        sys.exit(f"스키마 없음: {EXAMPLE}")
    schema = yaml.safe_load(EXAMPLE.read_text()) or {}
    known = set(leaf_paths(schema))

    # 1. 설정 2벌 파싱 + 팀 설정 키가 스키마 안에 있는가
    if TEAM.exists():
        team = yaml.safe_load(TEAM.read_text()) or {}
        for p in leaf_paths(team):
            if p.startswith("files."):        # 파일별 오버레이는 자유 키
                continue
            if p not in known:
                fails.append(f"[스키마] 팀 설정에만 있는 키: {p}")
    else:
        warns.append(f"팀 설정 없음 ({TEAM}) — 내장 기본값으로 동작")

    # 2. 스크립트 문법
    chk = COMMON / "scripts" / "lib" / "check.sh"
    if chk.exists():
        r = subprocess.run([str(chk)], capture_output=True, text=True)
        if r.returncode != 0:
            fails.append("[문법] check.sh 실패:\n" + r.stdout + r.stderr)
    else:
        fails.append("[문법] check.sh 없음")

    # 3. 스킬별 검사
    cfg_ref = re.compile(r"`([a-z_]+(?:\.[a-z_]+)+)`")
    # 뒤에 확장자가 붙으면 스킬 참조가 아니라 파일 경로다 (`./figma-conventions.yaml`)
    # 이름 끝을 고정한다. `(?!\.)` 만 두면 그리디가 한 글자 물러나 확장자 검사를 빠져나간다
    # (`/figma-conventions.yaml` → `figma-convention` 으로 매치돼 오탐이 났다).
    skill_ref = re.compile(r"/(figma-[a-z-]+)(?![a-z-])(?!\.[a-z])")
    for name in NAMES:
        f = SKILLS / name / "SKILL.md"
        if not f.exists():
            fails.append(f"[누락] {name}/SKILL.md 없음")
            continue
        s = f.read_text()

        # frontmatter
        m = re.search(r"^---\n(.*?)\n---", s, re.S)
        if not m:
            fails.append(f"[frontmatter] {name}: 없음")
        else:
            fm = m.group(1)
            got = re.search(r"^name:\s*(\S+)", fm, re.M)
            if not got or got.group(1) != name:
                fails.append(f"[frontmatter] {name}: name 이 디렉터리와 불일치 ({got.group(1) if got else '없음'})")
            if "description:" not in fm:
                fails.append(f"[frontmatter] {name}: description 없음")

        # 설정 키 참조가 스키마에 있는가
        for ref in set(cfg_ref.findall(s)):
            root = ref.split(".")[0]
            if root not in schema:            # 설정 경로가 아닌 코드 표현은 건너뛴다
                continue
            if ref not in known:
                fails.append(f"[설정참조] {name}: `{ref}` 가 스키마에 없음")

        # 가리키는 스킬이 실재하는가
        for ref in set(skill_ref.findall(s)):
            if ref == name:
                continue
            if not (SKILLS / ref / "SKILL.md").exists():
                fails.append(f"[상호참조] {name} → /{ref} 가 없음")

        # 고유값
        for w in TEAM_STRINGS:
            if w in s:
                fails.append(f"[고유값] {name}: '{w}'")

    print("=" * 60)
    for x in warns:
        print("WARN ", x)
    for x in fails:
        print("FAIL ", x)
    print("=" * 60)
    print(f"스킬 {len(NAMES)}개 · 스키마 키 {len(known)}개 · 위반 {len(fails)}건 · 경고 {len(warns)}건")
    print("PASS" if not fails else "FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
