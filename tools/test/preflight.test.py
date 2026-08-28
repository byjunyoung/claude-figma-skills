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
    check("no config → says nothing is needed yet", "Nothing is needed yet" in out.splitlines()[0], out.splitlines()[0])
    check("no config → needed-because line says so", "no settings yet" in line(out, "needed because"), line(out, "needed because"))

    (proj / "pm-conventions.yaml").write_text("task:\n  record: {type: notion, ref: 'collection://x'}\n")
    out = run(proj, home)
    check("record notion → Notion required", "task.record.type: notion" in line(out, "needed because"), line(out, "needed because"))

    # A type the plugin has never heard of, whose adapter declares its connector
    (proj / "pm-adapters" / "trackers").mkdir(parents=True)
    (proj / "pm-adapters" / "trackers" / "gsheet.md").write_text("# Sheets\n\nconnector: Google Drive\n")
    (proj / "pm-conventions.yaml").write_text("task:\n  record: {type: gsheet, ref: 'abc'}\n")
    out = run(proj, home)
    check("unknown type → connector taken from the adapter's connector: line",
          "task.record.type: gsheet → Google Drive" in line(out, "needed because"), line(out, "needed because"))
    check("unknown type → a row named after that connector (whatever its state)", any(ln.startswith("connector Google Drive") for ln in out.splitlines()), out)

    # Where the claude CLI is absent — a CI runner — a required connector must not read as answered
    # A PATH with node but without claude — /usr/bin alone would also lose node and fail on the host row
    import shutil
    bare_bin = Path(tmp) / "bin"; bare_bin.mkdir()
    for tool in ("node", "gh"):
        found = shutil.which(tool)
        if found:
            (bare_bin / tool).symlink_to(found)
    bare = dict(os.environ, HOME=str(home), PYTHONUSERBASE=site.getuserbase(), PATH=f"{bare_bin}:/usr/bin:/bin")
    r = subprocess.run([sys.executable, str(SCRIPT)], cwd=proj, env=bare, capture_output=True, text=True, timeout=120)
    check("no claude CLI → verdict says it cannot tell", r.stdout.startswith("Cannot tell"), r.stdout.splitlines()[0] if r.stdout else r.stderr)
    check("no claude CLI → exit 2, not PASS", r.returncode == 2 and "UNKNOWN" in r.stdout.splitlines()[-1], f"rc={r.returncode}")

    # The same type with no adapter falls back to the type name, and says so
    (proj / "pm-adapters" / "trackers" / "gsheet.md").unlink()
    out = run(proj, home)
    check("unknown type, no adapter → the type name itself", "task.record.type: gsheet" in line(out, "needed because") and "→" not in line(out, "needed because"), line(out, "needed because"))

print()
if failures:
    print(f"{len(failures)} failed — " + ", ".join(failures)); sys.exit(1)
print("preflight fixtures · PASS")
