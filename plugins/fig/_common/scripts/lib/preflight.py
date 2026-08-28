#!/usr/bin/env python3
"""Preflight — says whether this machine can actually run the skills, before one is run.

This file lives as a copy in each plugin. Change one and not the other and verify catches it.

The README's own troubleshooting says it plainly: a skill cannot call a tool it was never
given, and it does not fail loudly when one is missing — it simply cannot reach it. A first
run then looks like it did nothing. This runs before that happens and names what is absent.

Which plugin it is speaking for comes from its own path, so the two copies stay identical.

What counts as required is not fixed. Before a config exists nothing beyond the host rows can
be, because whether GitHub matters depends on a value nobody has written yet. Once the config
names a tracker, the connector it needs is required — and a setup skill that has just asked
which tools are in play passes them with --require, so the verdict means something on a
machine that has no config yet.

Usage
    python3 preflight.py                          → a report, exit 1 if a hard requirement is missing
    python3 preflight.py --quiet                  → only the lines that need attention, and the summary
    python3 preflight.py --require Notion,GitHub  → treat these connectors as required for this run

What it cannot see: Claude in Chrome is a browser extension, not an MCP server, so it does
not appear in `claude mcp list`. It is reported as unknown rather than guessed at. A Figma
seat is not visible from the shell either — the skills that write check it with `whoami`.
"""
import importlib.util, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = "pm" if f"{os.sep}pm{os.sep}" in HERE else "fig"
QUIET = "--quiet" in sys.argv

RULE = "=" * 60

# Connectors are named by what `claude mcp list` prints, matched case-insensitively as a
# substring. `plugin:figma` is the Figma MCP plugin; the claude.ai connectors carry that prefix.
#
# required — the plugin cannot work without it
# optional — a config key decides whether the skill ever reaches for it, so its absence is
#            a fact worth knowing, not a failure — until the config names it (see below)
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

# A tool the config names is a required connector, whatever the tool. The trigger is a value
# somebody wrote — a ref, a type, a channel id — and the name comes from the resolved type, so a
# default type still counts once a ref was written against it, and a default alone never does.
# A machine that has never run setup has nothing required here, and is told so rather than
# PASSing as if that meant something.
#   (keys the user must have written, the type key, type values that need no connector)
NAMED_TOOLS = {
    "fig": [
        (("task_tracker.ref", "task_tracker.type"), "task_tracker.type", {"none"}),
        (("guide_source.ref", "guide_source.type"), "guide_source.type", {"none", "file", "url"}),
    ],
    "pm": [
        (("task.record.ref", "task.record.type"), "task.record.type", {"none", "markdown"}),
        (("task.mirror.ref", "task.mirror.type"), "task.mirror.type", {"none"}),
        (("prd.target", "prd.notion.template", "prd.notion.task_db",
          "prd.notion.inline_db.users", "prd.notion.inline_db.features"), "prd.target", {"markdown", "git"}),
        (("log.sources.chat_channels", "log.sources.notes_channel"), "sources.chat_type", {"none"}),
        (("log.sources.calendar",), "sources.calendar_type", {"none"}),
    ],
}
# How a type reads in `claude mcp list`. Anything else is matched on the type name itself,
# which is how a connector this file has never heard of still gets a row.
CONNECTOR_NAME = {"notion": "Notion", "github": "GitHub", "slack": "Slack", "google": "Google Calendar"}

# Where the tracker is GitHub, the tracker adapter runs on the gh CLI, not on the connector.
# This is the config key holding the repo the check tries to open.
TRACKER_REF = {"fig": "task_tracker.ref", "pm": "task.mirror.ref"}

CHROME_SKILLS = {"fig": "/fig:proto, /fig:code and /fig:qa drive a real browser", "pm": None}
CONFIG_NAME = {"fig": "figma-conventions.yaml", "pm": "pm-conventions.yaml"}[PLUGIN]

rows, missing, required, because = [], [], {}, []      # required: lower-case name → display name


def arg_after(flag):
    argv = sys.argv[1:]
    if flag in argv and argv.index(flag) + 1 < len(argv):
        return argv[argv.index(flag) + 1]
    return None


def row(kind, name, state, note=""):
    rows.append((kind, name, state, note))
    if state == "missing":
        missing.append(name)


def dig(cfg, path):
    cur = cfg
    for part in path.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
        if cur is None:
            return None
    return cur


def run(cmd, timeout=20):
    """stdout+stderr and the return code, or None where the command is not there or hangs."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or "") + (p.stderr or ""), p.returncode
    except (OSError, subprocess.SubprocessError):
        return None, None


def load_config():
    """(the user's layers merged without the bundled floor, the fully resolved config), or
    (None, None) where no user layer exists.

    The floor is kept apart on purpose. Its record type is notion, and a machine whose only
    config is a profile name must not read as "Notion required": a requirement comes from a
    value somebody wrote, never from a default nobody chose. The resolved config is still
    needed — for the name of the tool once a ref was written against a default type."""
    spec = importlib.util.spec_from_file_location("resolve_config", os.path.join(HERE, "resolve-config.py"))
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        user, found = {}, False
        for p in mod.candidates(CONFIG_NAME)[1:]:
            if os.path.exists(p):
                user, found = mod.merge(user, mod.load(p)), True
        full, _ = mod.resolve(None, CONFIG_NAME)
    except (SystemExit, Exception):        # no PyYAML, no file — the host rows say which
        return None, None
    return (user, full) if found else (None, None)


def written(cfg, key):
    return dig(cfg, key) not in (None, "", [], {})


def require(name, why):
    required[name.lower()] = name
    because.append(why)


def settle_requirements():
    for name in (arg_after("--require") or "").split(","):
        if name.strip():
            require(name.strip(), f"--require {name.strip()}")
    user, full = load_config()
    if user is None:
        because.append("no config yet — nothing beyond the host is required until setup names a tool")
        return None
    named = False
    for triggers, type_key, quiet in NAMED_TOOLS[PLUGIN]:
        if not any(written(user, k) for k in triggers):
            continue
        if triggers[0].startswith("log.") and not dig(full, "log.enabled"):
            continue                       # channels named in a log that is switched off
        typ = str(dig(full, type_key) or "none").lower()
        if typ in quiet:
            continue
        require(CONNECTOR_NAME.get(typ, typ.capitalize()), f"{type_key}: {typ}")
        named = True
    if not named:
        because.append("the config names no connector — nothing beyond the host is required")
    return full


def is_required(name):
    return name.lower() in required


def host_checks():
    row("host", f"python3 {sys.version.split()[0]}", "ok")

    try:
        import yaml
        row("host", f"PyYAML {getattr(yaml, '__version__', '?')}", "ok")
    except ImportError:
        row("host", "PyYAML", "missing", "pip3 install pyyaml — config resolution needs it")

    out, code = run(["node", "--version"], timeout=10)
    if code == 0:
        row("host", f"node {out.strip()}", "ok")
    else:
        row("host", "node", "missing", "nodejs.org — the audit scripts are syntax-checked with it")


def connector_checks():
    """`claude mcp list` runs a health check per server, so it is slow but authoritative."""
    listing, _ = run(["claude", "mcp", "list"], timeout=120)
    if listing is None:
        row("connector", "claude mcp list", "unknown", "the claude CLI did not answer — check connectors by hand")
        return

    lines = listing.splitlines()
    checks = list(CONNECTORS[PLUGIN])
    listed = {n.lower() for n, _, _ in checks}
    checks += [(disp, False, "named by the config") for low, disp in required.items() if low not in listed]
    for name, hard, why in checks:
        need = hard or is_required(name)
        hit = next((ln for ln in lines if name.lower() in ln.lower()), None)
        if hit and "Connected" in hit:
            row("connector", name, "ok", "" if hard else why)
        elif hit and "Failed" in hit:
            # Configured and not answering is a different fix from not configured. The tail of
            # the error is what says which — a 400 on the auth header is an empty token variable,
            # not a revoked login
            tail = re.sub(r".*Failed to connect\s*[—-]*\s*", "", hit).strip()[:70]
            row("connector", name, "missing" if need else "failed",
                f"configured but not answering — {tail}" if tail else "configured but not answering")
        elif need:
            row("connector", name, "missing", why)
        else:
            row("connector", name, "absent", why)


def gh_checks(cfg):
    """The GitHub tracker adapter runs on the gh CLI. Where GitHub is required this row decides,
    and which account it is logged in to decides more than whether it is installed — a personal
    account against a company org gets a 404 that reads like the repo does not exist."""
    need = is_required("GitHub")
    out, code = run(["gh", "--version"], timeout=10)
    if code != 0:
        row("cli", "gh", "missing" if need else "absent", "cli.github.com — the GitHub tracker adapter runs on it")
        return
    ver = (out.split() + ["?"])[2] if out.startswith("gh version") else "?"

    status, _ = run(["gh", "auth", "status"])
    account, active = None, None
    for ln in (status or "").splitlines():
        m = re.search(r"account (\S+)", ln)
        if m:
            account = account or m.group(1)
            current = m.group(1)
        if "Active account: true" in ln:
            active = current
    account = active or account
    if not account:
        row("cli", f"gh {ver}", "missing" if need else "attention", "not logged in — gh auth login")
        return

    hdr, _ = run(["gh", "api", "-i", "user"])
    m = re.search(r"^x-oauth-scopes:\s*(.*)$", hdr or "", re.I | re.M)
    scopes = m.group(1).strip() if m else ""
    note = f"account {account}"
    if scopes:
        note += f" · scopes {scopes}"
        if "project" not in scopes:
            note += " · no read:project — board ids need it: gh auth refresh -s read:project"
    else:
        note += " · scopes not reported by this token"
    row("cli", f"gh {ver}", "ok", note)

    ref = dig(cfg, TRACKER_REF[PLUGIN]) if cfg else None
    if need and isinstance(ref, str) and "/" in ref:
        _, code = run(["gh", "repo", "view", ref, "--json", "name"])
        if code == 0:
            row("tracker", ref, "ok", f"visible to {account}")
        else:
            row("tracker", ref, "missing",
                f"not visible to {account} — the wrong active account (gh auth switch) or not a member of that org")


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
    if because:
        print("required by  " + " · ".join(because))

    absent = sum(1 for r in rows if r[2] == "absent")
    tail = f" · {absent} optional connector{'s' if absent != 1 else ''} not connected" if absent else ""
    if missing:
        print(f"{len(missing)} missing — {', '.join(missing)}{tail} · FAIL")
        return 1
    print(f"ready for /{PLUGIN}:setup{tail} · PASS")
    return 0


cfg = settle_requirements()
host_checks()
connector_checks()
gh_checks(cfg)
other_checks()
sys.exit(report())
