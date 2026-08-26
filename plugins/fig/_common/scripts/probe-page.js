/* =============================================================================
 * probe-page.js — 한 페이지에서 관례를 역추출한다 (읽기 전용, 쓰기 0)
 *
 * /figma-setup 이 낯선 파일의 conventions.yaml 초안을 만들 때 쓴다.
 * 규칙을 판정하지 않고 **관측치만** 낸다 — 무엇을 관례로 볼지는 호스트에서 집계한다.
 *
 * 앞에 붙일 것: `const PAGE_ID = "<page id>";`
 * 반환: 아래 shape 의 관측 객체
 *
 * 판정하지 않는 이유 — 표본이 한 페이지뿐이면 우연을 관례로 굳힌다.
 * 여러 페이지를 병렬로 돌려 합산한 뒤에야 최빈값을 관례로 본다.
 * ========================================================================== */

const page = await figma.getNodeByIdAsync(PAGE_ID);
if (!page) return { error: `페이지 없음: ${PAGE_ID}` };
await figma.setCurrentPageAsync(page);

const hex = c => "#" + [c.r, c.g, c.b].map(v =>
  Math.round(v * 255).toString(16).padStart(2, "0").toUpperCase()).join("");
const paint = arr => (Array.isArray(arr) && arr[0] && arr[0].type === "SOLID")
  ? { hex: hex(arr[0].color), opacity: arr[0].opacity != null ? +arr[0].opacity.toFixed(3) : 1 }
  : null;
const g = (n, k) => { try { return n[k]; } catch (e) { return undefined; } };

const secs = page.children.filter(c => c.type === "SECTION");
const out = {
  page: page.name,
  sectionCount: secs.length,
  sections: [],
  frameNames: [],
  suffixes: {},
  gaps: { frameX: [], frameY: [], sectionX: [], sectionY: [] },
  columnPitch: [],
  arrows: { count: 0, styles: [], headGaps: [] },
  labels: { count: 0, styles: [] },
  stateLinks: 0,
  dashedFrames: [],          // placeholder 후보
  pageDirectFrames: 0        // 섹션 밖 화면 프레임 = 이 페이지가 느슨하다는 신호
};

for (const f of page.children) if (f.type === "FRAME") out.pageDirectFrames++;

for (const s of secs) {
  out.sections.push({
    name: s.name, x: Math.round(s.x), y: Math.round(s.y),
    w: Math.round(s.width), h: Math.round(s.height),
    fill: paint(g(s, "fills")), stroke: paint(g(s, "strokes")),
    strokeWeight: g(s, "strokeWeight"), strokeAlign: g(s, "strokeAlign"),
    dash: g(s, "dashPattern"), radius: g(s, "cornerRadius"),
    children: s.children.length
  });

  const frames = s.children.filter(c => c.type === "FRAME");
  for (const f of frames) {
    out.frameNames.push(f.name);
    const m = f.name.match(/-([A-Za-z][\w]*)$/);        // [화면명]-[상태] 의 상태부
    if (m) out.suffixes[m[1]] = (out.suffixes[m[1]] || 0) + 1;
    if (Array.isArray(g(f, "dashPattern")) && f.dashPattern.length)
      out.dashedFrames.push({ name: f.name, dash: f.dashPattern,
        stroke: paint(g(f, "strokes")), fill: paint(g(f, "fills")),
        strokeWeight: g(f, "strokeWeight") });
  }

  // 간격은 **인접 쌍만** 센다. 모든 쌍을 세면 배수(2칸·3칸 건너뛴 거리)가 목록을 덮어
  // 최빈값이 무너진다 — 실측에서 frame_gap 이 24/69(35%)로 떨어져 추정 불가가 됐다.
  const bucket = (arr, key) => {
    const m = {};
    for (const f of arr) { const k = Math.round(f[key] / 8); (m[k] = m[k] || []).push(f); }
    return Object.values(m);
  };
  for (const row of bucket(frames, "y")) {
    row.sort((a, b) => a.x - b.x);
    for (let i = 1; i < row.length; i++) {
      out.gaps.frameX.push(Math.round(row[i].x - (row[i - 1].x + row[i - 1].width)));
      out.columnPitch.push(Math.round(row[i].x - row[i - 1].x));   // 열 그리드 = 인접 열 시작점 차이
    }
  }
  for (const col of bucket(frames, "x")) {
    col.sort((a, b) => a.y - b.y);
    for (let i = 1; i < col.length; i++)
      out.gaps.frameY.push(Math.round(col[i].y - (col[i - 1].y + col[i - 1].height)));
  }

  for (const n of s.children) {
    if (n.type !== "VECTOR") continue;
    const st = { color: paint(g(n, "strokes")), weight: g(n, "strokeWeight"), dash: g(n, "dashPattern") };
    if (n.name.startsWith("[state]") || (n.name.includes("~") && !n.name.includes("-->"))) {
      out.stateLinks++;
    } else if (n.name.includes("-->")) {
      out.arrows.count++;
      if (out.arrows.styles.length < 8) out.arrows.styles.push(st);
      // 화살촉과 도착 프레임 사이 여백 — 기본값 역추출용
      const to = n.name.split("-->")[1];
      const T = to && frames.find(f => f.name === to.trim());
      if (T) {
        const vs = n.vectorNetwork.vertices;
        const pe = vs[vs.length - 1];
        const ax = n.x + pe.x, ay = n.y + pe.y;
        const gx = ax < T.x ? T.x - ax : ax > T.x + T.width ? ax - (T.x + T.width) : 0;
        const gy = ay < T.y ? T.y - ay : ay > T.y + T.height ? ay - (T.y + T.height) : 0;
        const gap = Math.round(Math.max(gx, gy));
        if (gap > 0 && gap < 100) out.arrows.headGaps.push(gap);
      }
    }
  }

  for (const n of s.children) {
    if (!n.name.startsWith("[label]")) continue;
    out.labels.count++;
    if (out.labels.styles.length >= 5) continue;
    const t = n.findOne ? n.findOne(x => x.type === "TEXT") : null;
    out.labels.styles.push({
      fill: paint(g(n, "fills")), stroke: paint(g(n, "strokes")),
      radius: g(n, "cornerRadius"),
      padding: [g(n, "paddingLeft"), g(n, "paddingTop")],
      font: t ? { family: t.fontName.family, style: t.fontName.style, size: t.fontSize } : null,
      textColor: t ? paint(g(t, "fills")) : null
    });
  }
}

// 섹션 간 간격 — 프레임과 같은 이유로 인접 쌍만
const sbucket = (key) => {
  const m = {};
  for (const s of secs) { const k = Math.round(s[key] / 40); (m[k] = m[k] || []).push(s); }
  return Object.values(m);
};
for (const row of sbucket("y")) {
  row.sort((a, b) => a.x - b.x);
  for (let i = 1; i < row.length; i++)
    out.gaps.sectionX.push(Math.round(row[i].x - (row[i - 1].x + row[i - 1].width)));
}
for (const col of sbucket("x")) {
  col.sort((a, b) => a.y - b.y);
  for (let i = 1; i < col.length; i++)
    out.gaps.sectionY.push(Math.round(col[i].y - (col[i - 1].y + col[i - 1].height)));
}

return out;
