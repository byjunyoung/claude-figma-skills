#!/usr/bin/env python3
"""Fixtures for preflight.py — which connector a config makes required, and what it says when
there is no config. Connector rows depend on the machine (`claude mcp list`), so only the
lines that do not are asserted: the `required by` line and the verdict's first words.

    python3 tools/test/preflight.test.py
"""
import os, site, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins" / "pm" / "_common" / "scripts" / "lib" / "preflight.py"
failures = []


def run(cwd, home):
    env = dict(os.environ, HOME=str(home), PYTHONUSERBASE=site.getuserbase())
    r = subprocess.run([sys.executable, str(SCRIPT)], cwd=cwd, env=env, capture_output=True, text=True, timeout=300)
    return r.stdout


def line(out, prefix):
    return next((ln for ln in out.splitlines() if ln.startswith(prefix)), "")


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


with tempfile.TemporaryDirectory() as tmp:
    home, proj = Path(tmp) / "home", Path(tmp) / "proj"
    (home / ".claude").mkdir(parents=True); proj.mkdir()

    out = run(proj, home)
    check("no config → says nothing is required yet", "Nothing is required yet" in out.splitlines()[0], out.splitlines()[0])
    check("no config → required-by line says so", "no config yet" in line(out, "required by"), line(out, "required by"))

    (proj / "pm-conventions.yaml").write_text("task:\n  record: {type: notion, ref: 'collection://x'}\n")
    out = run(proj, home)
    check("record notion → Notion required", "task.record.type: notion" in line(out, "required by"), line(out, "required by"))

    # A type the plugin has never heard of, whose adapter declares its connector
    (proj / "pm-adapters" / "trackers").mkdir(parents=True)
    (proj / "pm-adapters" / "trackers" / "gsheet.md").write_text("# Sheets\n\nconnector: Google Drive\n")
    (proj / "pm-conventions.yaml").write_text("task:\n  record: {type: gsheet, ref: 'abc'}\n")
    out = run(proj, home)
    check("unknown type → connector taken from the adapter's connector: line",
          "task.record.type: gsheet → Google Drive" in line(out, "required by"), line(out, "required by"))
    check("unknown type → a row named after that connector", any(ln.startswith("connector Google Drive") for ln in out.splitlines()), out)

    # The same type with no adapter falls back to the type name, and says so
    (proj / "pm-adapters" / "trackers" / "gsheet.md").unlink()
    out = run(proj, home)
    check("unknown type, no adapter → the type name itself", "task.record.type: gsheet" in line(out, "required by") and "→" not in line(out, "required by"), line(out, "required by"))

print()
if failures:
    print(f"{len(failures)} failed — " + ", ".join(failures)); sys.exit(1)
print("preflight fixtures · PASS")
