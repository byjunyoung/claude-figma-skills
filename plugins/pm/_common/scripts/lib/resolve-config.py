#!/usr/bin/env python3
"""설정 해석기 — 설정 파일을 찾아 깊은 병합하고 JSON 한 줄로 낸다.

플러그인 사이에서 사본으로 도는 파일이다. 한쪽만 고치면 verify 가 잡는다.

Figma 플러그인 샌드박스는 파일시스템이 없다. 그래서 설정 해석은 호스트에서 하고,
결과 JSON 을 `const CFG = {...};` 형태로 감사 스크립트 앞에 붙여 use_figma 에 넣는다.

사용
    python3 resolve-config.py [fileKey]      → JSON (stdout)
    python3 resolve-config.py --js [fileKey] → `const CFG = {...};` 한 줄
    python3 resolve-config.py --where        → 어느 파일을 썼는지만
    python3 resolve-config.py --name pm-conventions.yaml   → 찾을 파일명을 바꾼다

겹쳐 읽는다 (아래가 위를 덮는다). 부분만 적은 설정도 그대로 동작한다 —
빠뜨린 키는 기본값이 채우고, 적은 키만 덮인다.
    1. ../conventions.example.yaml           내장 기본값 (바닥)
    2. ~/.claude/<name>                      사용자 공통
    3. ./<name>                              프로젝트별 (가장 셈)

키를 지워서 검사를 끄지 않는다 — 끄려면 null 을 적는다. 지우면 기본값이 살아난다.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_NAME = "figma-conventions.yaml"


def candidates(name):
    """바닥부터 순서대로. 뒤가 앞을 덮는다."""
    return [
        os.path.normpath(os.path.join(HERE, "..", "..", "conventions.example.yaml")),
        os.path.expanduser(os.path.join("~/.claude", name)),
        os.path.join(os.getcwd(), name),
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


def resolve(file_key=None, name=DEFAULT_NAME):
    cands = candidates(name)
    cfg, used = {}, []
    for p in cands:
        if os.path.exists(p):
            cfg = merge(cfg, load(p))
            used.append(p)
    if not used:
        sys.exit("설정 파일을 못 찾았습니다: " + " / ".join(cands))
    src = used[-1]              # 가장 센 층. 어느 설정으로 돌았는지 보고에 쓴다

    files = cfg.pop("files", None) or {}
    if file_key and file_key in files:
        cfg = merge(cfg, {k: v for k, v in files[file_key].items() if k != "label"})
        cfg.setdefault("meta", {})["file_label"] = files[file_key].get("label", file_key)
    elif file_key:
        cfg.setdefault("meta", {})["file_label"] = None      # 파일별 관례 미등록
    cfg.setdefault("meta", {})["source"] = src
    cfg["meta"]["layers"] = used
    return cfg, src


def main():
    argv = sys.argv[1:]
    as_js = "--js" in argv
    where = "--where" in argv
    name = DEFAULT_NAME
    if "--name" in argv:
        i = argv.index("--name")
        if i + 1 >= len(argv):
            sys.exit("--name 뒤에 파일명이 필요합니다")
        name = argv[i + 1]
        del argv[i:i + 2]
    args = [a for a in argv if not a.startswith("--")]
    cfg, src = resolve(args[0] if args else None, name)
    if where:
        print(src)
    elif as_js:
        print("const CFG = " + json.dumps(cfg, ensure_ascii=False) + ";")
    else:
        print(json.dumps(cfg, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
