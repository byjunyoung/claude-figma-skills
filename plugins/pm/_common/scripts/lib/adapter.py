#!/usr/bin/env python3
"""Adapter lookup — which file carries the calls for a tool, or that none does.

The calls for one tool live in one file, named by the type the config uses: trackers/<type>.md
for a task tracker, sources/<type>.md for chat or a calendar. The bundled ones sit under
_common/ beside this script. The ones you draft live outside the plugin — `adapters.dirs` in
the config — so an update does not overwrite them. Later dirs cover earlier, like the config
layers, so a file of yours with the same name replaces a bundled one.

Usage
    python3 adapter.py --kind trackers --type notion     → the path to read
    python3 adapter.py --kind sources  --type slack
    python3 adapter.py --kind trackers --type none       → prints "none", exit 0 — no adapter needed
    python3 adapter.py --kind trackers --type linear     → exit 3, stderr says where the template is
    --name pm-conventions.yaml                             the config filename, as resolve-config takes it

Exit 3 is the one a skill stops on. It means the type names a tool nobody has written the calls
for. The fix is /pm:setup drafting them from the tools connected on this machine — never a
skill improvising them from what it remembers of the tool's API.
"""
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
COMMON = os.path.normpath(os.path.join(HERE, "..", ".."))
KINDS = ("trackers", "sources")


def take(argv, flag):
    if flag not in argv:
        return None
    i = argv.index(flag)
    if i + 1 >= len(argv):
        sys.exit(f"{flag} needs a value after it")
    val = argv[i + 1]
    del argv[i:i + 2]
    return val


def config_dirs(name):
    """adapters.dirs from the resolved config, ~ expanded. Empty where the config cannot be read —
    the bundled files are still looked at, and resolve-config's own error says why."""
    spec = importlib.util.spec_from_file_location("resolve_config", os.path.join(HERE, "resolve-config.py"))
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cfg, _ = mod.resolve(None, name)
    except (SystemExit, Exception):
        return []
    dirs = (cfg.get("adapters") or {}).get("dirs") or []
    return [os.path.expanduser(d) for d in dirs if isinstance(d, str) and d]


def main():
    argv = sys.argv[1:]
    kind = take(argv, "--kind")
    typ = (take(argv, "--type") or "").strip().lower()
    name = take(argv, "--name") or "pm-conventions.yaml"
    if kind not in KINDS:
        sys.exit("--kind is one of: " + ", ".join(KINDS))
    if typ in ("", "none"):
        print("none")
        return

    # Absolute, so the path a skill is handed does not depend on where it happens to be run from
    candidates = [os.path.join(COMMON, kind, f"{typ}.md")]
    candidates += [os.path.join(d, kind, f"{typ}.md") for d in config_dirs(name)]
    candidates = [os.path.abspath(c) for c in candidates]
    found = [p for p in candidates if os.path.exists(p)]
    if found:
        print(found[-1])
        return
    template = os.path.join(COMMON, kind, "_template.md")
    print(f"no adapter for {kind}/{typ} — looked in: " + ", ".join(candidates), file=sys.stderr)
    print(f"/pm:setup drafts one from the tools connected on this machine. The template is {template}", file=sys.stderr)
    sys.exit(3)


if __name__ == "__main__":
    main()
