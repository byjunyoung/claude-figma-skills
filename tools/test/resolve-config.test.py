#!/usr/bin/env python3
"""Fixtures for resolve-config.py — the layering, and the --need gate a skill stops on.

    python3 tools/test/resolve-config.test.py

Runs the pm copy; verify.py already holds the two copies identical. HOME is pointed at a
temp dir for every case, so the machine's own ~/.claude config cannot leak into a fixture.
Moving HOME also moves python's user site-packages, which is where a `pip install --user
pyyaml` lives — so the real user base is pinned back with PYTHONUSERBASE, or every case
fails on a missing module that is in fact installed.
"""
import json, os, site, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins" / "pm" / "_common" / "scripts" / "lib" / "resolve-config.py"
NAME = "pm-conventions.yaml"

failures = []


def run(cwd, home, *args):
    env = dict(os.environ, HOME=str(home), PYTHONUSERBASE=site.getuserbase())
    return subprocess.run([sys.executable, str(SCRIPT), "--name", NAME, *args],
                          cwd=cwd, env=env, capture_output=True, text=True)


def parse(r):
    """The JSON on stdout, or None with the reason printed — a traceback here hides the stderr
    the script wrote, which is the one line that says why."""
    try:
        return json.loads(r.stdout)
    except ValueError:
        print("      no JSON on stdout — stderr: " + r.stderr.strip())
        return None


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


with tempfile.TemporaryDirectory() as tmp:
    home, proj = Path(tmp) / "home", Path(tmp) / "proj"
    (home / ".claude").mkdir(parents=True)
    proj.mkdir()

    # 1. No config anywhere: the bundled defaults alone, and record.ref is null
    r = run(proj, home)
    cfg = parse(r) or {}
    check("no config → bundled defaults only", r.returncode == 0 and len(cfg.get("meta", {}).get("layers", [])) == 1, r.stderr)
    check("no config → task.record.ref is null", cfg.get("task", {}).get("record", {}).get("ref") is None)

    # 2. --need on that null: exit 2, the key named on stderr, nothing on stdout
    r = run(proj, home, "--need", "task.record.ref")
    check("--need on a null → exit 2", r.returncode == 2, f"rc={r.returncode}")
    check("--need on a null → key named on stderr", "task.record.ref is null" in r.stderr, r.stderr)
    check("--need on a null → no JSON on stdout", r.stdout.strip() == "")

    # 3. A project layer writes the key: --need passes and the value comes through
    (proj / NAME).write_text("task:\n  record:\n    type: markdown\n    ref: ./tasks\n")
    r = run(proj, home, "--need", "task.record.ref")
    cfg = parse(r) or {}
    check("project layer → --need passes", r.returncode == 0, r.stderr)
    check("project layer → value read", cfg.get("task", {}).get("record", {}).get("ref") == "./tasks")
    check("project layer → two layers", len(cfg.get("meta", {}).get("layers", [])) == 2)

    # 4. Home + project: project wins, and a deep merge keeps the sibling the project did not write
    (home / ".claude" / NAME).write_text("meta:\n  profile: home\ntask:\n  link_property: Ticket\n  record:\n    ref: ./from-home\n")
    r = run(proj, home)
    cfg = parse(r) or {}
    check("two layers → project covers home", cfg.get("task", {}).get("record", {}).get("ref") == "./tasks")
    check("two layers → sibling from home survives", cfg.get("task", {}).get("link_property") == "Ticket")
    check("two layers → three layers reported", len(cfg.get("meta", {}).get("layers", [])) == 3)

    # 5. An explicit null in the stronger layer is a value, not an absence — it does not fall back
    (proj / NAME).write_text("task:\n  link_property: null\n")
    r = run(proj, home, "--need", "task.link_property")
    check("null in project → covers the home value, --need stops", r.returncode == 2, f"rc={r.returncode}")

    # 6. An empty map is a value, so --need does not stop on it
    (proj / NAME).write_text("task:\n  label_map:\n    project: {}\n")
    r = run(proj, home, "--need", "task.label_map.project")
    check("empty map → --need passes", r.returncode == 0, r.stderr)

print()
if failures:
    print(f"{len(failures)} failed — " + ", ".join(failures))
    sys.exit(1)
print("resolve-config fixtures · PASS")
