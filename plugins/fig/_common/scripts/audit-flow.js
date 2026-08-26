/* =============================================================================
 * audit-flow.js — 흐름 감사 (읽기 전용, 쓰기 0)
 *
 * 검사: 전환 화살표 수치 · 진입 방향 · 관통 · 라벨 z순서 · [state] 점선 · 커버리지 orphan
 *
 * 사용은 audit-struct.js 와 같다. 반환: 위반 배열, 없으면 "FLOW PASS"
 *
 * 제외 섹션(템플릿·아카이브·폐기 대역) 취급 — 세 갈래로 다르다.
 *   · 감사 대상에서 제외   그 섹션 안의 화살표·라벨은 검사하지 않는다
 *   · 커버리지에서 제외    그 섹션의 프레임은 연결을 요구하지 않는다
 *   · 관통 대상에는 포함   선이 실제로 그 위를 지나면 여전히 깨진 선이다
 * 이 구분이 없으면 아카이브의 옛 화살표가 매번 위반으로 잡힌다.
 * ========================================================================== */

const C = typeof CFG !== "undefined" ? CFG : {};
const N = C.naming || {}, P = C.pages || {};
const A = (C.arrows || {}).audit || {};

const anyOf = a => (a && a.length ? new RegExp(a.join("|")) : null);
const SEC_EXCLUDE = anyOf(P.exclude_sections);

const ARROW = (N.arrow_delimiter || " --> ").trim();      // 이름 안 구분자
const CHAIN = N.state_chain_delimiter || " ~ ";
const LABEL = N.label_prefix || "[label] ";
const STATE = N.state_chain_prefix || "[state] ";

const EDGE_TOL = A.edge_tolerance != null ? A.edge_tolerance : 2;
const GAP = A.gap_range || [9, 15];
const CLEAR = A.label_clear != null ? A.label_clear : 30;

const skipSection = s => !!(SEC_EXCLUDE && SEC_EXCLUDE.test(s.name));
const isScreen = n => n.type === "FRAME" && !n.name.startsWith(LABEL) &&
  !n.name.startsWith(STATE) && !n.name.includes(ARROW);

const allSecs = figma.currentPage.children.filter(c => c.type === "SECTION");
const liveSecs = allSecs.filter(s => !skipSection(s));

// 프레임 사전(절대좌표). 관통 검사와 이름 조회는 제외 섹션까지 포함해야 정확하다.
const frames = [];
for (const s of allSecs)
  for (const f of s.children)
    if (isScreen(f))
      frames.push({ name: f.name, sec: s.name, excluded: skipSection(s),
                    x: s.x + f.x, y: s.y + f.y, r: s.x + f.x + f.width, b: s.y + f.y + f.height });
const byName = Object.fromEntries(frames.map(f => [f.name, f]));

const dup = frames.map(f => f.name).filter((n, i, a) => a.indexOf(n) !== i);
const issues = [];
if (dup.length)
  issues.push(`[중복이름] ${[...new Set(dup)].join(", ")} — 이름 조회가 하나만 잡으니 섹션 한정으로 좁혀 재실행`);

for (const s of liveSecs) {
  for (const n of s.children) {
    if (n.type !== "VECTOR") continue;
    const toAbs = v => ({ x: s.x + n.x + v.x, y: s.y + n.y + v.y });

    // ── 전환 화살표 ────────────────────────────────────────────────
    if (n.name.includes(ARROW) && !n.name.startsWith(STATE)) {
      const [fr, to] = n.name.split(ARROW).map(t => t.trim());
      const F = byName[fr], T = byName[to];
      if (!F || !T) { issues.push(`[화살표] ${n.name}: orphan(${!F ? fr : to} 없음)`); continue; }
      const vs = n.vectorNetwork.vertices.map(toAbs), p0 = vs[0], pe = vs[vs.length - 1];

      const dE = Math.min(Math.abs(p0.x - F.x), Math.abs(p0.x - F.r),
                          Math.abs(p0.y - F.y), Math.abs(p0.y - F.b));
      if (dE > EDGE_TOL) issues.push(`[화살표] ${n.name}: 시작 ${dE.toFixed(0)}px 이탈`);

      const gx = pe.x < T.x ? T.x - pe.x : pe.x > T.r ? pe.x - T.r : 0;
      const gy = pe.y < T.y ? T.y - pe.y : pe.y > T.b ? pe.y - T.b : 0;
      const gap = Math.max(gx, gy);
      if (gap < GAP[0] || gap > GAP[1]) issues.push(`[화살표] ${n.name}: 도착 여백 ${gap.toFixed(0)}px (기준 ${GAP[0]}~${GAP[1]})`);

      // 진입 방향 — 마지막 세그먼트가 도착 변에 수직이어야 한다.
      // 평행이면 화살촉이 옆 허공을 가리키는데 거리 검사만으론 안 잡힌다.
      const prev = vs[vs.length - 2];
      if (prev) {
        const dL = Math.abs(pe.x - T.x), dR = Math.abs(pe.x - T.r);
        const dT = Math.abs(pe.y - T.y), dB = Math.abs(pe.y - T.b);
        const vEdge = Math.min(dL, dR) <= Math.min(dT, dB);
        const finalH = Math.abs(pe.y - prev.y) < 2, finalV = Math.abs(pe.x - prev.x) < 2;
        if (vEdge ? !finalH : !finalV) issues.push(`[화살표] ${n.name}: 화살촉이 도착 변에 평행(방향 틀림)`);
      }

      for (let i = 1; i < vs.length; i++) {
        const sx = Math.min(vs[i-1].x, vs[i].x), sr = Math.max(vs[i-1].x, vs[i].x);
        const sy = Math.min(vs[i-1].y, vs[i].y), sb = Math.max(vs[i-1].y, vs[i].y);
        for (const f of frames) {
          if (f.name === fr || f.name === to) continue;
          if (sx < f.r && sr > f.x && sy < f.b && sb > f.y)
            issues.push(`[화살표] ${n.name}: seg${i} → ${f.name} 관통`);
        }
      }
    }

    // ── [state] 상태 체인 ──────────────────────────────────────────
    if (n.name.startsWith(STATE) && n.name.includes(CHAIN)) {
      const [a, b] = n.name.slice(STATE.length).split(CHAIN).map(t => t.trim());
      const F = byName[a], T = byName[b];
      if (!F || !T) { issues.push(`[state] ${n.name}: orphan(${!F ? a : b} 없음)`); continue; }
      const vs = n.vectorNetwork.vertices.map(toAbs), p0 = vs[0], pe = vs[vs.length - 1];

      // 2-vertex 수직 직선이어야 한다. 엘보면 자기 from·to 위를 휘감아 관통 검사를 빠져나간다.
      if (vs.length !== 2 || Math.abs(p0.x - pe.x) > 2) {
        issues.push(`[state] ${n.name}: 비수직/엘보(vertex ${vs.length}) — 같은 열 수직으로 재생성하거나 배치를 모을 것`);
        continue;
      }
      if (F.y > T.y) issues.push(`[state] ${n.name}: 이름 순서 역전(from 이 아래)`);
      if (Math.abs(p0.y - F.b) > EDGE_TOL) issues.push(`[state] ${n.name}: 시작이 from 하변에서 ${Math.abs(p0.y - F.b).toFixed(0)}px`);
      if (Math.abs(pe.y - T.y) > EDGE_TOL) issues.push(`[state] ${n.name}: 끝이 to 상변에서 ${Math.abs(pe.y - T.y).toFixed(0)}px`);

      const lx = p0.x, top = Math.min(p0.y, pe.y), bot = Math.max(p0.y, pe.y);
      for (const f of frames) {
        if (f.name === a || f.name === b) continue;
        if (f.x < lx && f.r > lx && f.y < bot && f.b > top)
          issues.push(`[state] ${n.name}: ${f.name} 관통 — 배치 문제(부모와 상태 변형 사이에 끼어 있음)`);
      }
    }
  }

  // ── 라벨 ──────────────────────────────────────────────────────
  // 라벨은 세 가지로 깨진다. z순서가 낮으면 선이 글자를 관통하고,
  // 화살촉에 붙으면 어디로 가는지를 가리고, 남의 선 위에 얹히면 소속이 모호해진다.
  const segsOf = n => {
    const vs = n.vectorNetwork.vertices.map(v => ({ x: s.x + n.x + v.x, y: s.y + n.y + v.y }));
    const out = [];
    for (let i = 1; i < vs.length; i++)
      out.push({ x: Math.min(vs[i-1].x, vs[i].x), r: Math.max(vs[i-1].x, vs[i].x),
                 y: Math.min(vs[i-1].y, vs[i].y), b: Math.max(vs[i-1].y, vs[i].y) });
    return { segs: out, head: vs[vs.length - 1] };
  };
  const arrowsHere = s.children.filter(c => c.type === "VECTOR" && c.name.includes(ARROW) && !c.name.startsWith(STATE));

  for (const p of s.children) {
    if (!p.name.startsWith(LABEL)) continue;
    const owner = p.name.slice(LABEL.length);
    const v = s.children.find(c => c.name === owner);
    if (v && s.children.indexOf(p) < s.children.indexOf(v))
      issues.push(`[라벨] ${p.name}: pill 이 화살표보다 z순서 아래`);
    if (p.width == null) continue;
    const box = { x: s.x + p.x, y: s.y + p.y, r: s.x + p.x + p.width, b: s.y + p.y + p.height };

    // 자기 화살촉을 가리는가 — pill 을 label_clear 만큼 넓힌 상자에 도착점이 들어오면 위반
    if (v && v.type === "VECTOR") {
      const { head } = segsOf(v);
      if (head && head.x > box.x - CLEAR && head.x < box.r + CLEAR &&
                  head.y > box.y - CLEAR && head.y < box.b + CLEAR)
        issues.push(`[라벨] ${p.name}: 화살촉 ${CLEAR}px 이내 — 도착점을 가린다`);
    }

    // 다른 화살표의 선을 덮는가 — 공유 트렁크 위에 얹은 라벨이 주범이다
    for (const a of arrowsHere) {
      if (a.name === owner) continue;
      const { segs } = segsOf(a);
      if (segs.some(g => box.x < g.r && box.r > g.x && box.y < g.b && box.b > g.y)) {
        issues.push(`[라벨] ${p.name}: ${a.name} 의 선을 덮음`);
        break;
      }
    }
  }
}

// ── 커버리지 orphan — 모든 화면 프레임이 흐름에 최소 1회 등장해야 한다 ──────────
// 연결 집합은 제외 섹션의 화살표도 포함한다(아카이브가 가리키는 프레임도 연결된 것).
// 다만 연결을 요구하는 대상은 살아 있는 섹션의 프레임뿐이다.
const connected = new Set();
for (const s of allSecs)
  for (const c of s.children) {
    if (c.type !== "VECTOR") continue;
    if (c.name.startsWith(STATE) && c.name.includes(CHAIN))
      c.name.slice(STATE.length).split(CHAIN).map(t => t.trim()).forEach(x => connected.add(x));
    else if (c.name.includes(ARROW))
      c.name.split(ARROW).map(t => t.trim()).forEach(x => connected.add(x));
  }
// 공통 페이지의 canonical 상태 프레임은 화면별 흐름에 안 걸리는 게 정상이다.
// 그 페이지 전체를 커버리지에서 뺀다 — 설정이 null 이면 이 예외를 적용하지 않는다.
const COMMON_RE = N.common_page_pattern ? new RegExp(N.common_page_pattern) : null;
const isCommonPage = !!(COMMON_RE && COMMON_RE.test(figma.currentPage.name));
if (!isCommonPage)
  for (const f of frames)
    if (!f.excluded && !connected.has(f.name))
      issues.push(`[커버리지] orphan 프레임(흐름에서 빠짐): ${f.name} — ${f.sec}`);

return issues.length ? issues : "FLOW PASS";
