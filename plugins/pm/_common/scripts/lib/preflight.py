#!/usr/bin/env python3
"""Preflight — says whether this machine can actually run the skills, before one is run.

This file lives as a copy in each plugin. Change one and not the other and verify catches it.

The README's own troubleshooting says it plainly: a skill cannot call a tool it was never
given, and it does not fail loudly when one is missing — it simply cannot reach it. A first
run then looks like it did nothing. This runs before that happens and names what is absent.

Which plugin it is speaking for comes from its own path, so the two copies stay identical.

Usage
    python3 preflight.py            → a report, exit 1 if a hard requirement is missing
    python3 preflight.py --quiet    → only the lines that need attention, and the summary

What it cannot see: Claude in Chrome is a browser extension, not an MCP server, so it does
not appear in `claude mcp list`. It is reported as unknown rather than guessed at.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = "pm" if f"{os.sep}pm{os.sep}" in HERE else "fig"
QUIET = "--quiet" in sys.argv

RULE = "=" * 60

# Connectors are named by what `claude mcp list` prints, matched case-insensitively as a
# substring. `plugin:figma` is the Figma MCP plugin; the claude.ai connectors carry that prefix.
#
# required — the plugin cannot work without it
# optional — a config key decides whether the skill ever reaches for it, so its absence is
#            a fact worth knowing, not a failure
CONNECTORS = {
    "fig": [
        ("plugin:figma", True, "every fig skill reads and writes Figma through it"),
        ("Notion", False, "where a config key points at a Notion page"),
        ("GitHub", False, "where task_tracker.type is github"),
        ("Slack", False, "where /fig:qa takes its request source from a thread"),
    ],
    "pm": [
        ("Notion", False, "where prd.target or the tracker is notion"),
        ("GitHub", False, "where task.mirror.type is github"),
        ("Slack", False, "where /pm:task-draft drafts from a thread"),
    ],
}

CHROME_SKILLS = {"fig": "/fig:proto, /fig:code and /fig:qa drive a real browser", "pm": None}
CONFIG_NAME = {"fig": "figma-conventions.yaml", "pm": "pm-conventions.yaml"}[PLUGIN]

rows, missing = [], []


def row(kind, name, state, note=""):
    rows.append((kind, name, state, note))
    if state == "missing":
        missing.append(name)


def host_checks():
    row("host", f"python3 {sys.version.split()[0]}", "ok")

    try:
        import yaml
        row("host", f"PyYAML {getattr(yaml, '__version__', '?')}", "ok")
    except ImportError:
        row("host", "PyYAML", "missing", "pip3 install pyyaml — config resolution needs it")

    try:
        v = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
        if v.returncode == 0:
            row("host", f"node {v.stdout.strip()}", "ok")
        else:
            row("host", "node", "missing", "nodejs.org — the audit scripts are syntax-checked with it")
    except (OSError, subprocess.SubprocessError):
        row("host", "node", "missing", "nodejs.org — the audit scripts are syntax-checked with it")


def connector_checks():
    """`claude mcp list` runs a health check per server, so it is slow but authoritative."""
    try:
        p = subprocess.run(["claude", "mcp", "list"], capture_output=True, text=True, timeout=120)
        listing = (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.SubprocessError):
        listing = None

    if listing is None:
        row("connector", "claude mcp list", "unknown", "the claude CLI did not answer — check connectors by hand")
        return

    connected = [ln for ln in listing.splitlines() if "Connected" in ln]
    for name, required, why in CONNECTORS[PLUGIN]:
        hit = any(name.lower() in ln.lower() for ln in connected)
        if hit:
            row("connector", name, "ok", "" if required else why)
        elif required:
            row("connector", name, "missing", why)
        else:
            row("connector", name, "absent", why)


def other_checks():
    why = CHROME_SKILLS[PLUGIN]
    if why:
        row("browser", "Claude in Chrome", "unknown", f"not visible from the shell — {why}")

    for path in (os.path.join(os.path.expanduser("~/.claude"), CONFIG_NAME),
                 os.path.join(os.getcwd(), CONFIG_NAME)):
        if os.path.exists(path):
            row("config", path.replace(os.path.expanduser("~"), "~"), "ok")
            return
    row("config", f"~/.claude/{CONFIG_NAME}", "none yet",
        f"expected before setup — /{PLUGIN}:setup writes it")


def report():
    print(RULE)
    for kind, name, state, note in rows:
        if QUIET and state in ("ok", "absent"):
            continue
        line = f"{kind:<10}{name:<38}{state:<9}"
        print(f"{line} {note}".rstrip())
    print(RULE)

    absent = sum(1 for r in rows if r[2] == "absent")
    tail = f" · {absent} optional connector{'s' if absent != 1 else ''} not connected" if absent else ""
    if missing:
        print(f"{len(missing)} missing — {', '.join(missing)}{tail} · FAIL")
        return 1
    print(f"ready for /{PLUGIN}:setup{tail} · PASS")
    return 0


host_checks()
connector_checks()
other_checks()
sys.exit(report())
