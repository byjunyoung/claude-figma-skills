#!/usr/bin/env python3
"""probe-page.js 관측치 → figma-conventions.yaml 초안.

    python3 draft-conventions.py probe1.json probe2.json ... [--pages pages.txt]

각 값에 근거(표본 수·비율)를 주석으로 달고, 표본이 얇으면 값을 넣지 않고 null 로 둔다.
**추정을 확정처럼 쓰지 않는 것이 이 도구의 전부다** — 애매한 건 사람이 채워야 한다.
"""
import json, re, sys
from collections import Counter

MIN_SUPPORT = 3          # 이 수 미만 표본은 관례로 보지 않는다
DOMINANCE = 0.6          # 최빈값이 이 비율 미만이면 갈린 것으로 본다


def mode(vals, min_support=MIN_SUPPORT, dominance=DOMINANCE):
    """(값, 근거문자열) 또는 (None, 사유)."""
    vals = [v for v in vals if v is not None]
    if not vals:
        return None, "관측 0"
    c = Counter(json.dumps(v, sort_keys=True, ensure_ascii=False) for v in vals)
    top, n = c.most_common(1)[0]
    ratio = n / len(vals)
    if len(vals) < min_support:
        return None, f"표본 {len(vals)}개 — 부족"
    if ratio < dominance:
        return None, f"갈림 (최빈 {n}/{len(vals)}, {ratio:.0%})"
    return json.loads(top), f"{n}/{len(vals)} ({ratio:.0%})"


def snap(vals, grid=4):
    """좌표 오차를 흡수하려고 격자에 맞춰 반올림한 뒤 최빈값을 본다."""
    return [round(v / grid) * grid for v in vals if isinstance(v, (int, float)) and v > 0]


def y(v):
    return json.dumps(v, ensure_ascii=False) if v is not None else "null"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    probes = []
    for f in args:
        d = json.load(open(f, encoding="utf-8"))
        probes.extend(d if isinstance(d, list) else [d])
    probes = [p for p in probes if not p.get("error")]
    if not probes:
        sys.exit("관측치 없음")

    L, notes = [], []

    def line(k, v, why, indent=2):
        L.append(f"{' ' * indent}{k}: {y(v)}" + (f"   # {why}" if why else ""))

    # ── 네이밍 ────────────────────────────────────────────────
    frames = [n for p in probes for n in p.get("frameNames", [])]
    secnames = [s["name"] for p in probes for s in p.get("sections", [])]
    fr_re = r'^.+-[^-\s]+$'        # 접미사를 라틴 문자로 제한하면 비라틴 상태명이 전건 오탐된다
    fr_hit = sum(1 for n in frames if re.match(fr_re, n))
    fr_ok = frames and fr_hit / len(frames) >= DOMINANCE

    sec_num = sum(1 for n in secnames if re.match(r'^\d{2}\. ', n))
    sec_ok = secnames and sec_num / len(secnames) >= DOMINANCE

    suf = Counter()
    for p in probes:
        suf.update(p.get("suffixes", {}))
    states = [k for k, v in suf.most_common() if v >= 2]

    L.append("naming:")
    line("frame", "{screen}-{state}" if fr_ok else None, f"{fr_hit}/{len(frames)} 일치" if frames else "관측 0")
    line("frame_pattern", fr_re if fr_ok else None, "" if fr_ok else "패턴이 안 잡힘 — 검사 안 함")
    line("section", "NN. {domain} - {feature}" if sec_ok else None, f"{sec_num}/{len(secnames)} 번호 접두")
    line("section_pattern", r'^\d{2}\. .+$' if sec_ok else None, "")
    line("states", states or None, f"접미사 빈도 상위: {dict(suf.most_common(8))}" if suf else "관측 0")
    L.append("  required_states: null   # 화면 유형 판정이 필요해 자동 추정 불가 — 직접 채운다")
    for k, v in [("arrow_delimiter", " --> "), ("state_chain_delimiter", " ~ "),
                 ("label_prefix", "[label] "), ("state_chain_prefix", "[state] ")]:
        L.append(f"  {k}: {y(v)}")
    ncommon = [s for s in secnames if re.match(r'^공통|^common', s, re.I)]
    line("common_page_pattern", None, "공통 페이지는 파일 밖에 있을 수 있어 추정하지 않는다" if not ncommon else f"섹션 {len(ncommon)}건 관측 — 확인 필요")
    line("common_frame_prefix", None, "")
    L.append("")

    # ── 페이지 ────────────────────────────────────────────────
    excl = sorted({s for s in secnames if re.match(r'^템플릿$|^[Tt]emplate$|^\[?[Aa]rchive|^9\d\.', s)})
    L.append("pages:")
    L.append("  strict: []     # 자동 추정 불가 — 어느 페이지가 정본인지는 사람이 안다")
    L.append("  free: []")
    L.append("  readonly: []")
    line("exclude_sections", [f"^{re.escape(s)}$" for s in excl] or [], f"관측된 제외 후보: {excl}" if excl else "후보 없음")
    L.append("  protected_numbers: []")
    for k in ("canonical", "archive", "queue"):
        L.append(f"  {k}: null   # figma-sync 첫 실행에서 확인받아 채운다")
    L.append("")

    # ── 배치 ─────────────────────────────────────────────────
    fx = snap([v for p in probes for v in p["gaps"]["frameX"]])
    fy = snap([v for p in probes for v in p["gaps"]["frameY"]])
    sx = snap([v for p in probes for v in p["gaps"]["sectionX"]])
    sy = snap([v for p in probes for v in p["gaps"]["sectionY"]])
    coldiffs = snap([v for p in probes for v in p.get("columnPitch", [])])

    fg, fgw = mode(fx + fy)
    cg, cgw = mode(coldiffs)
    sgx, sgxw = mode(sx)
    sgy, sgyw = mode(sy)
    L.append("layout:")
    line("column_grid", cg, cgw)
    line("section_padding", None, "섹션 내부 여백은 프레임 위치만으론 안 갈라진다 — 직접 채운다")
    line("frame_gap", fg, fgw)
    line("section_gap_same_row", sgx, sgxw)
    line("domain_row_gap", sgy, sgyw)
    L.append("  section_resize_margin: [80, 160]")
    L.append("  row_bucket: 1000")
    ws = [s["w"] for p in probes for s in p.get("sections", [])]
    L.append(f"  reference_frame_width: null   # 화면 폭 관측 필요 (섹션 폭 중앙값 {sorted(ws)[len(ws)//2] if ws else '-'})")
    L.append("")

    # ── 섹션 스타일 ────────────────────────────────────────────
    S = [s for p in probes for s in p.get("sections", [])]
    fill, fw = mode([s["fill"] for s in S])
    strk, sw = mode([s["stroke"] for s in S])
    dash, dw = mode([s["dash"] for s in S])
    rad, rw = mode([s["radius"] for s in S])
    L.append("section_style:")
    line("fill", fill["hex"] if fill else None, fw)
    line("fill_opacity", fill["opacity"] if fill else None, "")
    line("stroke", strk["hex"] if strk else None, sw)
    line("stroke_weight", mode([s["strokeWeight"] for s in S])[0], "")
    line("stroke_align", mode([s["strokeAlign"] for s in S])[0], "")
    line("dash", dash, dw)
    line("corner_radius", rad, rw)
    L.append("")

    # ── placeholder ──────────────────────────────────────────
    D = [d for p in probes for d in p.get("dashedFrames", [])]
    pf, pfw = mode([d["fill"] for d in D])
    ps, psw = mode([d["stroke"] for d in D])
    pd, pdw = mode([d["dash"] for d in D])
    L.append("placeholder_style:")
    line("fill", pf["hex"] if pf else None, pfw)
    line("stroke", ps["hex"] if ps else None, psw)
    line("stroke_weight", mode([d["strokeWeight"] for d in D])[0], "")
    line("dash", pd, pdw)
    L.append("  font: null   # 점선 프레임 안 텍스트를 직접 확인해 채운다")
    L.append("  text_color: null")
    L.append('  text_prefix: "Placeholder — "')
    L.append("")

    # ── 화살표 ────────────────────────────────────────────────
    A = [a for p in probes for a in p["arrows"]["styles"]]
    HG = snap([v for p in probes for v in p["arrows"]["headGaps"]], grid=1)
    LB = [l for p in probes for l in p["labels"]["styles"]]
    ac, acw = mode([a["color"] for a in A])
    aw_, aww = mode([a["weight"] for a in A])
    hg, hgw = mode(HG)
    L.append("arrows:")
    line("color", ac["hex"] if ac else None, acw)
    line("stroke_weight", aw_, aww)
    dashes = [a["dash"] for a in A if a["dash"]]
    line("dash_conditional", mode(dashes)[0] if dashes else None, f"점선 화살표 {len(dashes)}건")
    line("head_gap", hg, hgw)
    L.append("  trunk: null            # 엘보 경로에서만 드러나 자동 추정이 부정확하다")
    L.append("  trunk_to_target_min: null")
    L.append("  parallel_offset: null")
    L.append('  cap: { start: ROUND, end: ARROW_EQUILATERAL }')
    L.append("  label:")
    lf, lfw = mode([l["font"] for l in LB])
    L.append(f"    font: {y(lf)}   # {lfw}")
    lp, lpw = mode([l["padding"] for l in LB])
    L.append(f"    padding: {y(lp)}   # {lpw}")
    L.append(f"    corner_radius: {y(mode([l['radius'] for l in LB])[0])}")
    lfl, _ = mode([l["fill"] for l in LB])
    lst, _ = mode([l["stroke"] for l in LB])
    ltc, _ = mode([l["textColor"] for l in LB])
    L.append(f"    fill: {y(lfl['hex'] if lfl else None)}")
    L.append(f"    stroke: {y(lst['hex'] if lst else None)}")
    L.append(f"    text_color: {y(ltc['hex'] if ltc else None)}")
    L.append("    offset_from_target: null")
    L.append("  audit:")
    L.append("    edge_tolerance: 2")
    L.append(f"    gap_range: {y([hg - 3, hg + 3] if hg else None)}   # head_gap ±3")
    L.append("    label_clear: 30")
    L.append("")

    L.append("component_audit:")
    L.append("  min_samples: 5")
    L.append("  dominance: 0.9")
    L.append("  body_offset: null   # 화면 공통 껍데기 폭·높이 — 화면 하나를 열어 재야 한다")
    L.append("")
    L.append("design_system:\n  library: auto\n  token_prefixes: []\n  match_threshold_channel: 8\n")
    L.append("sync:")
    L.append("  pair_patterns:\n    to_be: 'to.?be|개선|after'\n    as_is: 'as.?is|현행|before'")
    L.append("  text_diff_max_len: 40\n  version_page_pattern: null\n")
    L.append("task_tracker:\n  type: none\n  ref: null\n  ui_section_heading: null")
    L.append('  annotation_category: "Changed"\n  scope_tags: []\n')
    L.append("tools:\n  figma_token_env: FIGMA_TOKEN\n  frame_count_guard: 20")
    L.append('  proto_output_dir: "."\n  proto_publish: null\n')
    L.append("guide_source:\n  type: none\n  ref: null\n")
    L.append("files: {}")

    head = [
        "# figma-conventions.yaml — /figma-setup 자동 초안",
        "#",
        f"# 관측 페이지 {len(probes)}개 · 섹션 {len(S)}개 · 프레임 {len(frames)}개"
        f" · 화살표 {sum(p['arrows']['count'] for p in probes)}개",
        "#",
        "# null 은 '추정하지 않았다'는 뜻이다. 추정을 확정처럼 쓰지 않으려고 비워 둔 것이므로,",
        "# 그대로 두면 해당 검사를 건너뛴다. 아는 값은 직접 채운다.",
        "# 각 줄 주석의 n/m 은 그 값이 몇 건 중 몇 건에서 관측됐는지다.",
        "",
    ]
    print("\n".join(head + L))
    pd_ = sum(p.get("pageDirectFrames", 0) for p in probes)
    if pd_:
        print(f"\n# 참고: 섹션 밖 페이지 직속 프레임 {pd_}개 관측 — 이 파일은 섹션 규약이 느슨할 수 있다.",
              file=sys.stderr)


if __name__ == "__main__":
    main()
