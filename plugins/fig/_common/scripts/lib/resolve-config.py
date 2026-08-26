#!/usr/bin/env python3
"""Config resolver — finds the config files, deep-merges them, emits one line of JSON.

This file lives as a copy in each plugin. Change one and not the other and verify catches it.

The Figma plugin sandbox has no filesystem. So the config is resolved on the host and the
resulting JSON is prepended to the audit script as `const CFG = {...};` before it goes to use_figma.

Usage
    python3 resolve-config.py [fileKey]      → JSON (stdout)
    python3 resolve-config.py --js [fileKey] → one `const CFG = {...};` line
    python3 resolve-config.py --where        → which files were used, nothing else
    python3 resolve-config.py --name pm-conventions.yaml   → change the filename to look for

The layers merge (later covers earlier). A config holding only some keys works as it is —
missing keys are filled by the defaults, and only what is written gets covered.
    1. ../conventions.example.yaml           bundled defaults (the floor)
    2. ~/.claude/<name>                      the user's shared config
    3. ./<name>                              per project (strongest)

Deleting a key does not switch a check off — write null for that. Deleting restores the default.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_NAME = "figma-conventions.yaml"


def candidates(name):
    """From the floor upward. Later covers earlier."""
    return [
        os.path.normpath(os.path.join(HERE, "..", "..", "conventions.example.yaml")),
        os.path.expanduser(os.path.join("~/.claude", name)),
        os.path.join(os.getcwd(), name),
    ]


def load(path):
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML missing — run `pip3 install pyyaml`, or put a .json of the same name in place")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def merge(base, over):
    """over covers base. Dicts merge deeply, everything else wholesale."""
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
        sys.exit("No config file found: " + " / ".join(cands))
    src = used[-1]              # the strongest layer. Reported so it is clear which config it ran on

    files = cfg.pop("files", None) or {}
    if file_key and file_key in files:
        cfg = merge(cfg, {k: v for k, v in files[file_key].items() if k != "label"})
        cfg.setdefault("meta", {})["file_label"] = files[file_key].get("label", file_key)
    elif file_key:
        cfg.setdefault("meta", {})["file_label"] = None      # no per-file convention registered
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
            sys.exit("--name needs a filename after it")
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
