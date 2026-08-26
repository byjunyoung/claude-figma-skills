#!/usr/bin/env python3
"""저장소 정합성 검사 — 마켓플레이스에 등록된 플러그인 전부.

    python3 tools/verify.py

스킬을 고친 뒤 이걸 돌린다. `plugin eval` 이 얼리 액세스라 못 쓰는 동안의 회귀 게이트다.
검사하는 것은 '문서와 실제가 어긋났는가' 하나다 —
스킬이 참조하는 설정 키가 스키마에 없거나, 가리키는 스킬이 없거나, 고유값이 남았거나.

이 파일은 저장소 개발 도구라 플러그인 안에 두지 않는다. 설치본에는 안 실린다.

종료 코드 0 통과 / 1 위반.
"""
import json, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MARKET = REPO / ".claude-plugin" / "marketplace.json"

# 팀 설정 파일명은 플러그인마다 다르다. fig 만 예전 이름을 지킨다(이미 쓰고 있는 파일이라)
TEAM_FILE = {"fig": "figma-conventions.yaml"}

# 플러그인 사이에서 사본으로 도는 파일. 갈리면 한쪽만 고쳐진 채 배포된다 —
# fig 개편 때 감사 코드가 세 벌로 갈라져 있던 걸 겪었다. 사본은 두되 같은지는 검사한다.
SHARED = ["_common/scripts/lib/resolve-config.py"]

# 고유값 검사. **패턴을 하나씩 따로 돌린다** — 여럿을 | 로 이어 붙이면
# 이스케이프가 꼬여 조용히 0 을 낸다(실측으로 한 건을 놓쳤다).
#
# 두 층으로 나눈다. 값이 팀마다 다른 것과, 팀을 **식별**하는 것은 다르다.
#   · SKILL.md 는 판단만 담으므로 값이 박혀 있으면 안 된다 → 전부 검사
#   · conventions 기본값·README 는 값을 담는 게 일이다. 다만 브랜드 색·제품명·문서 id 처럼
#     남의 회사를 가리키는 것은 배포본에 실리면 안 된다 → 식별자만 검사
TEAM_STRINGS = ["8306FF", "XDS", "1560", "BarisON", "[UI]", "[Update]",
                "바리스", "라운지", "36131847b3e5", "매 실행 시 fetch",
                "xyzcorp", "Pretendard", "townhall"]
IDENTITY_STRINGS = ["8306FF", "XDS", "BarisON", "바리스", "라운지", "36131847b3e5",
                    "xyzcorp"]

fails, warns, counts = [], [], []


def leaf_paths(o, prefix=""):
    if isinstance(o, dict) and o:
        for k, v in o.items():
            p = f"{prefix}.{k}" if prefix else k
            yield p
            yield from leaf_paths(v, p)


def check_plugin(name, root, yaml):
    """플러그인 하나를 검사한다. root 는 <repo>/plugins/<name>."""
    common = root / "_common"
    skills = root / "skills"
    example = common / "conventions.example.yaml"

    if not skills.is_dir():
        fails.append(f"[{name}] skills/ 없음")
        return
    # 스킬 목록은 디렉터리에서 읽는다 — 목록을 손으로 적으면 스킬을 늘릴 때 같이 안 늘어난다
    names = sorted(d.name for d in skills.iterdir() if (d / "SKILL.md").exists())
    if not names:
        fails.append(f"[{name}] SKILL.md 가 하나도 없음")
        return

    schema, known = {}, set()
    if example.exists():
        schema = yaml.safe_load(example.read_text()) or {}
        known = set(leaf_paths(schema))
    else:
        warns.append(f"[{name}] conventions.example.yaml 없음 — 설정 검사 건너뜀")

    # 매니페스트
    pj = root / ".claude-plugin" / "plugin.json"
    if not pj.exists():
        fails.append(f"[{name}] .claude-plugin/plugin.json 없음")
    else:
        try:
            d = json.loads(pj.read_text())
            if d.get("name") != name:
                fails.append(f"[{name}] plugin.json name 불일치: {d.get('name')}")
            if not d.get("version"):
                fails.append(f"[{name}] plugin.json version 없음")
        except Exception as e:
            fails.append(f"[{name}] plugin.json 파싱 실패: {e}")

    # 팀 설정 키가 스키마 안에 있는가
    team = Path.home() / ".claude" / TEAM_FILE.get(name, f"{name}-conventions.yaml")
    if team.exists() and known:
        for p in leaf_paths(yaml.safe_load(team.read_text()) or {}):
            if p.startswith("files."):        # 파일별 오버레이는 자유 키
                continue
            if p not in known:
                fails.append(f"[{name}] 팀 설정에만 있는 키: {p}")
    elif not team.exists():
        warns.append(f"[{name}] 팀 설정 없음 ({team.name}) — 내장 기본값으로 동작")

    # 스크립트에도 고유값이 샌다. SKILL.md 만 보다가 주석에 팀 폰트 이름이
    # 남은 채 배포된 적이 있다 — 검사 범위가 문서에만 걸려 있었기 때문이다.
    if (common / "scripts").is_dir():
        for f in sorted((common / "scripts").rglob("*")):
            if not f.is_file() or f.suffix not in (".js", ".py", ".sh"):
                continue
            t = f.read_text(errors="ignore")
            for w in TEAM_STRINGS:
                if w in t:
                    fails.append(f"[{name}] {f.name}: 고유값 '{w}'")

    # 스크립트 문법
    chk = common / "scripts" / "lib" / "check.sh"
    if chk.exists():
        # `bash <path>` 로 부른다 — 직접 실행하면 실행 권한에 기대게 되는데,
        # GitHub Contents API 로 배포된 파일에는 실행 비트가 안 따라온다(설치본에서 확인).
        r = subprocess.run(["bash", str(chk)], capture_output=True, text=True)
        if r.returncode != 0:
            fails.append(f"[{name}] check.sh 실패:\n" + r.stdout + r.stderr)

    cfg_ref = re.compile(r"`([a-z_]+(?:\.[a-z_]+)+)`")
    skill_ref = re.compile(rf"/{name}:([a-z-]+)")
    legacy_ref = re.compile(r"(?<![\w-])figma-([a-z-]+)")

    for sk in names:
        f = skills / sk / "SKILL.md"
        s = f.read_text()

        m = re.search(r"^---\n(.*?)\n---", s, re.S)
        if not m:
            fails.append(f"[{name}:{sk}] frontmatter 없음")
        else:
            fm = m.group(1)
            got = re.search(r"^name:\s*(\S+)", fm, re.M)
            if not got or got.group(1) != sk:
                fails.append(f"[{name}:{sk}] frontmatter name 이 디렉터리와 불일치 ({got.group(1) if got else '없음'})")
            if "description:" not in fm:
                fails.append(f"[{name}:{sk}] description 없음")

        for ref in set(cfg_ref.findall(s)):
            if ref.split(".")[0] not in schema:   # 설정 경로가 아닌 코드 표현은 건너뛴다
                continue
            if ref not in known:
                fails.append(f"[{name}:{sk}] `{ref}` 가 스키마에 없음")

        for ref in set(skill_ref.findall(s)):
            if ref != sk and not (skills / ref / "SKILL.md").exists():
                fails.append(f"[{name}:{sk}] → /{name}:{ref} 가 없음")

        # 스크립트 경로는 플러그인 루트 변수를 써야 한다 — 절대경로는 설치 위치가 바뀌면 깨진다
        if "~/.claude/skills/" in s:
            fails.append(f"[{name}:{sk}] 절대경로가 남아 있음 (${{CLAUDE_PLUGIN_ROOT}} 로 바꿀 것)")

        for w in TEAM_STRINGS:
            if w in s:
                fails.append(f"[{name}:{sk}] 고유값 '{w}'")

    # 스킬 이름 참조는 SKILL.md 밖에서도 샌다. 예시 설정의 주석이 개명 전 이름을
    # 그대로 달고 배포된 적이 있다 — 검사가 SKILL.md 만 보고 있었기 때문이다.
    for f in (example, root / "README.md"):
        if not f.exists():
            continue
        t = f.read_text()
        for w in IDENTITY_STRINGS:
            if w in t:
                fails.append(f"[{name}] {f.name}: 식별자 '{w}' — 배포본이 남의 회사를 가리킨다")
        for ref in sorted(set(skill_ref.findall(t))):
            if not (skills / ref / "SKILL.md").exists():
                fails.append(f"[{name}] {f.name} → /{name}:{ref} 가 없음")
        for ref in sorted(set(legacy_ref.findall(t))):
            if ref == "conventions":              # figma-conventions.yaml 은 설정 파일명
                continue
            fails.append(f"[{name}] {f.name}: 옛이름 'figma-{ref}'")

    counts.append(f"{name} {len(names)}스킬·{len(known)}키")


def main():
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML 필요")

    if not MARKET.exists():
        sys.exit(f"마켓플레이스 없음: {MARKET}")
    market = json.loads(MARKET.read_text())
    entries = market.get("plugins", [])
    if not entries:
        sys.exit("marketplace.json 에 plugins 항목이 없음")

    roots = {}
    for e in entries:
        name, src = e.get("name"), e.get("source")
        if not isinstance(src, str):
            warns.append(f"[{name}] source 가 로컬 경로가 아님 — 건너뜀")
            continue
        root = (REPO / src).resolve()
        if not root.is_dir():
            fails.append(f"[{name}] source 경로 없음: {src}")
            continue
        roots[name] = root
        check_plugin(name, root, yaml)

    # 사본으로 도는 파일이 갈렸는가
    for rel in SHARED:
        seen = {}
        for name, root in roots.items():
            f = root / rel
            if f.exists():
                seen.setdefault(f.read_bytes(), []).append(name)
        if len(seen) > 1:
            groups = " vs ".join("+".join(v) for v in seen.values())
            fails.append(f"[공유] {rel} 사본이 갈렸다: {groups}")

    print("=" * 60)
    for x in warns:
        print("WARN ", x)
    for x in fails:
        print("FAIL ", x)
    print("=" * 60)
    print("플러그인 " + " · ".join(counts) + f" · 위반 {len(fails)}건 · 경고 {len(warns)}건")
    print("PASS" if not fails else "FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
