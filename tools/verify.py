#!/usr/bin/env python3
"""Repository consistency check — every plugin registered in the marketplace.

    python3 tools/verify.py

Run this after editing a skill. It is the regression gate for as long as `plugin eval` stays
behind early access. It checks one thing: has the documentation drifted from the reality —
a config key a skill references that is not in the schema, a skill it points at that does not
exist, a team-specific value left in.

This is a repository development tool, so it does not live inside a plugin. It never ships to an install.

Exit code 0 pass / 1 violations.
"""
import json, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MARKET = REPO / ".claude-plugin" / "marketplace.json"

# The team config filename differs per plugin. Only fig keeps the older name (it is a file already in use)
TEAM_FILE = {"fig": "figma-conventions.yaml"}

# Files that live as copies across plugins. Let them diverge and one gets fixed while the other ships —
# during the fig rework the audit code had already split into three copies. Keep the copies, but check they match.
SHARED = ["_common/scripts/lib/resolve-config.py"]

# Team-value check. **One pattern at a time** — joining several with | tangles the escaping
# and silently returns zero (one case was actually missed that way).
#
# Two layers. A value that differs per team and a value that **identifies** a team are different things.
#   · SKILL.md carries judgement only, so no value belongs in it → check all of them
#   · conventions defaults and READMEs exist to carry values. But anything pointing at someone
#     else's company — a brand colour, a product name, a document id — must not ship → check identifiers only
TEAM_STRINGS = ["REDACTED", "REDACTED", "1560", "REDACTED", "[UI]", "[Update]",
                "REDACTED", "REDACTED", "REDACTED", "매 실행 시 fetch",
                "REDACTED", "Pretendard", "townhall"]
IDENTITY_STRINGS = ["REDACTED", "REDACTED", "REDACTED", "REDACTED", "REDACTED", "REDACTED",
                    "REDACTED"]

fails, warns, counts = [], [], []


# Only **spatial numbers measured in a specific file**. One test decides it — would shipping this
# value as a default make every frame in someone else's file report as a violation?
# Style, tolerance, and statistical thresholds are defaults somebody has to pick, so overlapping with
# a team's value is normal; widening to them produces 42 warnings. A warning that is always on never gets read.
MEASURED_KEYS = {
    "layout.column_grid", "layout.section_padding", "layout.frame_gap",
    "layout.section_gap_same_row", "layout.domain_row_gap",
    "layout.section_resize_margin",
}


def leaf_kv(o, prefix=""):
    """Leaf nodes only, as (path, value)."""
    if isinstance(o, dict) and o:
        for k, v in o.items():
            p = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict) and v:
                yield from leaf_kv(v, p)
            else:
                yield p, v


def leaf_paths(o, prefix=""):
    if isinstance(o, dict) and o:
        for k, v in o.items():
            p = f"{prefix}.{k}" if prefix else k
            yield p
            yield from leaf_paths(v, p)


def check_plugin(name, root, yaml):
    """Checks one plugin. root is <repo>/plugins/<name>."""
    common = root / "_common"
    skills = root / "skills"
    example = common / "conventions.example.yaml"

    if not skills.is_dir():
        fails.append(f"[{name}] no skills/")
        return
    # The skill list comes from the directory — a hand-written list does not grow when a skill is added
    names = sorted(d.name for d in skills.iterdir() if (d / "SKILL.md").exists())
    if not names:
        fails.append(f"[{name}] no SKILL.md at all")
        return

    schema, known = {}, set()
    if example.exists():
        schema = yaml.safe_load(example.read_text()) or {}
        known = set(leaf_paths(schema))
    else:
        warns.append(f"[{name}] no conventions.example.yaml — config checks skipped")

    # Manifest
    pj = root / ".claude-plugin" / "plugin.json"
    if not pj.exists():
        fails.append(f"[{name}] no .claude-plugin/plugin.json")
    else:
        try:
            d = json.loads(pj.read_text())
            if d.get("name") != name:
                fails.append(f"[{name}] plugin.json name mismatch: {d.get('name')}")
            if not d.get("version"):
                fails.append(f"[{name}] plugin.json has no version")
        except Exception as e:
            fails.append(f"[{name}] plugin.json failed to parse: {e}")

    # Does every team config key exist in the schema
    team = Path.home() / ".claude" / TEAM_FILE.get(name, f"{name}-conventions.yaml")
    if team.exists() and known:
        tcfg = yaml.safe_load(team.read_text()) or {}
        for p in leaf_paths(tcfg):
            if p.startswith("files."):        # per-file overlays take free-form keys
                continue
            if p not in known:
                fails.append(f"[{name}] key present only in the team config: {p}")

        # A bundled default identical to the team's value means a measured number shipped.
        # The whole layout section once went out byte-identical to the team config.
        # It can also coincide, so this stays a warning — a person makes the call
        tv, sv = dict(leaf_kv(tcfg)), dict(leaf_kv(schema))
        leaked = sorted(k for k in tv
                        if k in MEASURED_KEYS and k in sv
                        and tv[k] == sv[k] and tv[k] is not None)
        if leaked:
            warns.append(f"[{name}] default identical to team value: {', '.join(leaked[:6])}"
                         + (f" and {len(leaked)-6} more" if len(leaked) > 6 else "")
                         + " — check whether a measured value shipped")
    elif not team.exists():
        warns.append(f"[{name}] no team config ({team.name}) — running on bundled defaults")

    # Team values leak into the scripts too. Watching SKILL.md alone once shipped a team font
    # name left in a comment — because the check only covered the documents.
    if (common / "scripts").is_dir():
        for f in sorted((common / "scripts").rglob("*")):
            if not f.is_file() or f.suffix not in (".js", ".py", ".sh"):
                continue
            t = f.read_text(errors="ignore")
            for w in TEAM_STRINGS:
                if w in t:
                    fails.append(f"[{name}] {f.name}: team value '{w}'")

    # Script syntax
    chk = common / "scripts" / "lib" / "check.sh"
    if chk.exists():
        # Call it as `bash <path>` — running it directly relies on the executable bit,
        # which a file shipped through the GitHub Contents API does not carry (confirmed on an install).
        r = subprocess.run(["bash", str(chk)], capture_output=True, text=True)
        if r.returncode != 0:
            fails.append(f"[{name}] check.sh failed:\n" + r.stdout + r.stderr)

    cfg_ref = re.compile(r"`([a-z_]+(?:\.[a-z_]+)+)`")
    skill_ref = re.compile(rf"/{name}:([a-z-]+)")
    legacy_ref = re.compile(r"(?<![\w-])figma-([a-z-]+)")

    for sk in names:
        f = skills / sk / "SKILL.md"
        s = f.read_text()

        m = re.search(r"^---\n(.*?)\n---", s, re.S)
        if not m:
            fails.append(f"[{name}:{sk}] no frontmatter")
        else:
            fm = m.group(1)
            got = re.search(r"^name:\s*(\S+)", fm, re.M)
            if not got or got.group(1) != sk:
                fails.append(f"[{name}:{sk}] frontmatter name does not match the directory ({got.group(1) if got else 'missing'})")
            if "description:" not in fm:
                fails.append(f"[{name}:{sk}] no description")

        for ref in set(cfg_ref.findall(s)):
            if ref.split(".")[0] not in schema:   # skip code expressions that are not config paths
                continue
            if ref not in known:
                fails.append(f"[{name}:{sk}] `{ref}` is not in the schema")

        for ref in set(skill_ref.findall(s)):
            if ref != sk and not (skills / ref / "SKILL.md").exists():
                fails.append(f"[{name}:{sk}] → /{name}:{ref} does not exist")

        # Script paths must use the plugin root variable — an absolute path breaks when the install location changes
        if "~/.claude/skills/" in s:
            fails.append(f"[{name}:{sk}] an absolute path is left in (replace with ${{CLAUDE_PLUGIN_ROOT}})")

        for w in TEAM_STRINGS:
            if w in s:
                fails.append(f"[{name}:{sk}] team value '{w}'")

    # Skill-name references leak outside SKILL.md too. A comment in the example config once shipped
    # still carrying a pre-rename name — because the check was only looking at SKILL.md.
    for f in (example, root / "README.md"):
        if not f.exists():
            continue
        t = f.read_text()
        for w in IDENTITY_STRINGS:
            if w in t:
                fails.append(f"[{name}] {f.name}: identifier '{w}' — the shipped copy points at someone else's company")
        for ref in sorted(set(skill_ref.findall(t))):
            if not (skills / ref / "SKILL.md").exists():
                fails.append(f"[{name}] {f.name} → /{name}:{ref} does not exist")
        for ref in sorted(set(legacy_ref.findall(t))):
            if ref == "conventions":              # figma-conventions.yaml is a config filename
                continue
            fails.append(f"[{name}] {f.name}: old name 'figma-{ref}'")

    counts.append(f"{name} {len(names)} skills / {len(known)} keys")


def main():
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML required")

    if not MARKET.exists():
        sys.exit(f"marketplace not found: {MARKET}")
    market = json.loads(MARKET.read_text())
    entries = market.get("plugins", [])
    if not entries:
        sys.exit("marketplace.json has no plugins entry")

    roots = {}
    for e in entries:
        name, src = e.get("name"), e.get("source")
        if not isinstance(src, str):
            warns.append(f"[{name}] source is not a local path — skipped")
            continue
        root = (REPO / src).resolve()
        if not root.is_dir():
            fails.append(f"[{name}] source path does not exist: {src}")
            continue
        roots[name] = root
        check_plugin(name, root, yaml)

    # Have the shared copies diverged
    for rel in SHARED:
        seen = {}
        for name, root in roots.items():
            f = root / rel
            if f.exists():
                seen.setdefault(f.read_bytes(), []).append(name)
        if len(seen) > 1:
            groups = " vs ".join("+".join(v) for v in seen.values())
            fails.append(f"[shared] copies of {rel} have diverged: {groups}")

    print("=" * 60)
    for x in warns:
        print("WARN ", x)
    for x in fails:
        print("FAIL ", x)
    print("=" * 60)
    print("plugins " + " · ".join(counts) + f" · {len(fails)} violations · {len(warns)} warnings")
    print("PASS" if not fails else "FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
