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
    python3 resolve-config.py --need task.record.ref,task.link_property
                                             → exit 2 naming any of these that is null, no JSON

A skill that cannot run without a value asks for it with --need. A null there is a config
gap — setup writes it — and the skill stops on the key's name instead of running on nothing,
which is how a run on an unfinished config used to come back thin and look like a result.

The layers merge (later covers earlier). A config holding only some keys works as it is —
missing keys are filled by the defaults, and only what is written gets covered.
    1. ../conventions.example.yaml           bundled defaults (the floor)
    2. ~/.claude/<name>                      the user's shared config
    3. ./<name>                              per project (strongest)

Deleting a key does not switch a check off — write null for that. Deleting restores the default.
A map keeps the order the schema declares; write every one of its keys to reorder it.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = "pm" if f"{os.sep}pm{os.sep}" in HERE else "fig"
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
    """over covers base. Dicts merge deeply, everything else wholesale.

    Key order is the base's, so a partial override cannot shuffle a map whose order is read
    out — ticket.sections is written into a ticket in the order it is written down here, and
    a team naming one section should not move it to the front. Writing the map ENTIRE is how
    that order is changed: name every key the schema declares, in the order your tracker's
    own template puts them, and that order is what comes out.
    """
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    if over and set(over) >= set(base):
        out = {k: out[k] for k in list(over) + [x for x in out if x not in over]}
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


def unmet(cfg, keys):
    """The dotted keys whose value is missing, null, or an empty string. An empty list or map
    is a value — `label_map: {}` says nothing is mapped, which is a legitimate state."""
    out = []
    for k in keys:
        cur = cfg
        for part in k.split("."):
            cur = cur.get(part) if isinstance(cur, dict) else None
            if cur is None:
                break
        if cur is None or cur == "":
            out.append(k)
    return out


def take(argv, flag):
    """The value after a flag, removed from argv. None where the flag is absent."""
    if flag not in argv:
        return None
    i = argv.index(flag)
    if i + 1 >= len(argv):
        sys.exit(f"{flag} needs a value after it")
    val = argv[i + 1]
    del argv[i:i + 2]
    return val


def main():
    argv = sys.argv[1:]
    as_js = "--js" in argv
    where = "--where" in argv
    name = take(argv, "--name") or DEFAULT_NAME
    need = [k.strip() for k in (take(argv, "--need") or "").split(",") if k.strip()]
    args = [a for a in argv if not a.startswith("--")]
    cfg, src = resolve(args[0] if args else None, name)
    gaps = unmet(cfg, need)
    if gaps:
        for k in gaps:
            print(f"{k} is not set in {name} — this cannot run without it. /{PLUGIN}:setup fills it in, or write it by hand", file=sys.stderr)
        sys.exit(2)
    if where:
        print(src)
    elif as_js:
        print("const CFG = " + json.dumps(cfg, ensure_ascii=False) + ";")
    else:
        print(json.dumps(cfg, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
