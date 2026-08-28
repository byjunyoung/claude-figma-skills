#!/usr/bin/env python3
"""Fixtures for draft-conventions.py — observations in, a draft out, and nothing invented.

    python3 tools/test/draft-conventions.test.py

A synthetic probe has the shape probe-page.js returns. Three tidy pages must yield a convention
with its evidence; a thin sample and a split vote must yield null with the reason; no
observations must refuse. And every key the draft writes must be one verify.py accepts in a
team config — the draft *becomes* the team config, so a key verify rejects is a draft that
breaks the next run.
"""
import importlib.util, json, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LIB = REPO / "plugins" / "fig" / "_common" / "scripts" / "lib"
SCHEMA = REPO / "plugins" / "fig" / "_common" / "conventions.example.yaml"
failures = []


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


def probe(page, frames, gap=120, pitch=1560, sec_gap=240, row_gap=480, fill="#6B7280"):
    n = len(frames)
    return {
        "page": page,
        "frameNames": frames,
        "suffixes": {"Default": n // 2, "Empty": n // 4, "Error": n // 4},
        "sections": [{"name": f"0{i}. Account - Feature {i}", "w": 3000, "fill": {"hex": fill, "opacity": 0.04},
                      "stroke": {"hex": fill}, "dash": [20, 20], "radius": 72, "strokeWeight": 1, "strokeAlign": "INSIDE"} for i in (1, 2, 3)],
        "gaps": {"frameX": [gap] * n, "frameY": [gap] * 3, "sectionX": [sec_gap] * 3, "sectionY": [row_gap] * 2},
        "columnPitch": [pitch] * n,
        "dashedFrames": [{"fill": {"hex": "#FAFAFB"}, "stroke": {"hex": "#B3B3BF"}, "dash": [10, 8], "strokeWeight": 2}] * 3,
        "arrows": {"count": 4, "styles": [{"color": {"hex": "#4A5463"}, "weight": 3, "dash": None}] * 4, "headGaps": [12, 12, 12, 13]},
        "labels": {"styles": [{"font": {"family": "Inter", "style": "Medium", "size": 20}, "padding": [10, 5], "radius": 8,
                               "fill": {"hex": "#FFFFFF"}, "stroke": {"hex": "#D9DBE3"}, "textColor": {"hex": "#59616E"}}] * 3},
        "pageDirectFrames": 0,
    }


def run(probes):
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for i, p in enumerate(probes):
            f = Path(tmp) / f"p{i}.json"; f.write_text(json.dumps(p)); paths.append(str(f))
        r = subprocess.run([sys.executable, str(LIB / "draft-conventions.py"), *paths], capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr


import yaml
tidy = [probe(f"[UI] Page {i}", [f"Screen{j}-Default" for j in range(6)] + [f"Screen{j}-Empty" for j in range(3)]) for i in range(3)]
rc, out, err = run(tidy)
cfg = yaml.safe_load(out) if rc == 0 else None
check("three tidy pages → a draft", rc == 0 and isinstance(cfg, dict), err)
if cfg:
    check("naming inferred with evidence", cfg["naming"]["frame"] == "{screen}-{state}" and "match" in out)
    check("frame_gap 120 as the mode", cfg["layout"]["frame_gap"] == 120, str(cfg["layout"]))
    check("column_grid 1560", cfg["layout"]["column_grid"] == 1560)
    check("section fill read off the file", cfg["section_style"]["fill"] == "#6B7280")
    check("strict pages left empty — a person decides", cfg["pages"]["strict"] == [])
    check("head_gap ±3 becomes gap_range", cfg["arrows"]["audit"]["gap_range"] == [9, 15], str(cfg["arrows"]["audit"]))

    # The draft becomes the team config. Every key must be one verify.py accepts there.
    spec = importlib.util.spec_from_file_location("verify", REPO / "tools" / "verify.py")
    # verify.py runs checks on import, so lift just the two helpers out of its source instead
    src = (REPO / "tools" / "verify.py").read_text()
    ns = {}
    exec(src[src.index("def leaf_kv"):src.index("def check_plugin")], ns)
    known = set(ns["leaf_paths"](yaml.safe_load(SCHEMA.read_text())))
    unknown = sorted(k for k in ns["leaf_paths"](cfg) if k not in known and not k.startswith("files."))
    check("every key the draft writes is one verify accepts in a team config", not unknown, ", ".join(unknown))

rc, out, err = run(tidy[:1])
cfg = yaml.safe_load(out) if rc == 0 else {}
check("one page → gaps still inferred from six frames", cfg.get("layout", {}).get("frame_gap") == 120)
thin = [probe("[UI] Thin", ["A-Default", "B-Default"], gap=120)]
thin[0]["gaps"]["frameX"] = [120]; thin[0]["gaps"]["frameY"] = []; thin[0]["sections"] = thin[0]["sections"][:1]
thin[0]["gaps"]["sectionX"] = []; thin[0]["gaps"]["sectionY"] = []
rc, out, err = run(thin)
cfg = yaml.safe_load(out) if rc == 0 else {}
check("thin sample → frame_gap null with the reason", cfg.get("layout", {}).get("frame_gap") is None and "too few" in out, out[:200])

split = [probe("[UI] Split", [f"S{j}-Default" for j in range(6)], gap=120), probe("[UI] Split 2", [f"T{j}-Default" for j in range(6)], gap=200)]
rc, out, err = run(split)
cfg = yaml.safe_load(out) if rc == 0 else {}
check("split vote → frame_gap null, says split", cfg.get("layout", {}).get("frame_gap") is None and "split" in out, out[:200])

rc, out, err = run([{"error": "page not found"}])
check("no observations → refuses", rc != 0 and "no observations" in (err + out))

print()
if failures:
    print(f"{len(failures)} failed — " + ", ".join(failures)); sys.exit(1)
print("draft-conventions fixtures · PASS")
