#!/usr/bin/env python3
"""figma-conventions 해석기 — 설정을 찾아 깊은 병합하고 JSON 한 줄로 낸다.

Figma 플러그인 샌드박스는 파일시스템이 없다. 그래서 설정 해석은 호스트에서 하고,
결과 JSON 을 `const CFG = {...};` 형태로 감사 스크립트 앞에 붙여 use_figma 에 넣는다.

사용
    python3 resolve-config.py [fileKey]      → JSON (stdout)
    python3 resolve-config.py --js [fileKey] → `const CFG = {...};` 한 줄
    python3 resolve-config.py --where        → 어느 파일을 썼는지만

탐색 순서 (먼저 찾은 것 하나만)
    1. ./figma-conventions.yaml
    2. ~/.claude/figma-conventions.yaml
    3. ../conventions.example.yaml           내장 기본값
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CANDIDATES = [
    os.path.join(os.getcwd(), "figma-conventions.yaml"),
    os.path.expanduser("~/.claude/figma-conventions.yaml"),
    os.path.normpath(os.path.join(HERE, "..", "..", "conventions.example.yaml")),
]


def load(path):
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML 없음 — `pip3 install pyyaml` 또는 같은 이름의 .json 을 두세요")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def merge(base, over):
    """over 가 base 를 덮는다. dict 는 깊게, 나머지는 통째로."""
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def resolve(file_key=None):
    for p in CANDIDATES:
        if os.path.exists(p):
            cfg, src = load(p), p
            break
    else:
        sys.exit("설정 파일을 못 찾았습니다: " + " / ".join(CANDIDATES))

    files = cfg.pop("files", None) or {}
    if file_key and file_key in files:
        cfg = merge(cfg, {k: v for k, v in files[file_key].items() if k != "label"})
        cfg.setdefault("meta", {})["file_label"] = files[file_key].get("label", file_key)
    elif file_key:
        cfg.setdefault("meta", {})["file_label"] = None      # 파일별 관례 미등록
    cfg.setdefault("meta", {})["source"] = src
    return cfg, src


def main():
    args = [a for a in sys.argv[1:]]
    as_js = "--js" in args
    where = "--where" in args
    args = [a for a in args if not a.startswith("--")]
    cfg, src = resolve(args[0] if args else None)
    if where:
        print(src)
    elif as_js:
        print("const CFG = " + json.dumps(cfg, ensure_ascii=False) + ";")
    else:
        print(json.dumps(cfg, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
