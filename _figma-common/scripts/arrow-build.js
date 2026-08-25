/* =============================================================================
 * arrow-build.js — 흐름 화살표 생성 헬퍼 (프리앰블)
 *
 * 이 파일은 감사가 아니라 **빌드용 프리앰블**이다. 앞에 설정을 붙이고, 뒤에
 * 실제 생성 호출을 이어 붙여 use_figma 에 넣는다. deck/figma-deck/preamble.js 와 같은 방식.
 *
 *   const CFG = {...};        ← resolve-config.py --js
 *   <이 파일 전문>
 *   const sec = figma.currentPage.children.find(c => c.name === "01. 회원 - 목록");
 *   await straight(sec, "로그인-Default", "홈-Default");
 *   return { createdNodeIds: [...] };
 *
 * 좌표는 밖에서 계산해 넘기지 않는다. find() 로 스크립트 안에서 실시간 조회한다 —
 * 사용자가 그 사이 캔버스를 재배치했을 수 있다.
 *
 * 규칙은 설정이 정한다(색·굵기·트렁크·여백·라벨). 페이지에 기존 화살표가 있으면
 * 그 stroke 를 읽어 따르는 게 우선이고, 없을 때만 이 기본값을 쓴다.
 * ========================================================================== */

const C = typeof CFG !== "undefined" ? CFG : {};
const AR = C.arrows || {}, LB = AR.label || {}, NM = C.naming || {};

const hx = h => {
  const n = parseInt(String(h).replace("#", ""), 16);
  return { r: ((n >> 16) & 255) / 255, g: ((n >> 8) & 255) / 255, b: (n & 255) / 255 };
};

const COLOR = hx(AR.color || "#4A5463");
const WEIGHT = AR.stroke_weight != null ? AR.stroke_weight : 3;
const DASH = AR.dash_conditional || [12, 8];
const GAP = AR.head_gap != null ? AR.head_gap : 12;
const TRUNK = AR.trunk != null ? AR.trunk : 120;
const OFFSET = AR.parallel_offset != null ? AR.parallel_offset : 24;
const CAP = AR.cap || { start: "ROUND", end: "ARROW_EQUILATERAL" };

const ARROW_D = NM.arrow_delimiter || " --> ";
const CHAIN_D = NM.state_chain_delimiter || " ~ ";
const LABEL_P = NM.label_prefix || "[label] ";
const STATE_P = NM.state_chain_prefix || "[state] ";

const arrowName = (from, to) => from + ARROW_D + to;
const chainName = (from, to) => STATE_P + from + CHAIN_D + to;

/** 섹션 내 프레임 좌표 실시간 조회. 섹션 기준 상대좌표를 준다.
 *  섹션 간 화살표는 section.x/y 를 더해 절대좌표로 바꿔 계산한다. */
function find(section, name) {
  const n = section.children.find(c => c.name === name && c.type === "FRAME");
  if (!n) throw new Error(`프레임 없음: ${name}`);
  return { x: n.x, y: n.y, w: n.width, h: n.height,
           r: n.x + n.width, b: n.y + n.height,
           cx: n.x + n.width / 2, cy: n.y + n.height / 2 };
}

/** 꼭짓점 배열로 화살표 생성. 2점이면 직선, 3점 이상이면 직각 엘보.
 *  opts: { dashed, bidirectional } */
async function arrow(parent, name, pts, opts) {
  const o = opts || {};
  const minX = Math.min(...pts.map(p => p[0])), minY = Math.min(...pts.map(p => p[1]));
  const v = figma.createVector();
  await v.setVectorNetworkAsync({
    vertices: pts.map((p, i) => ({
      x: p[0] - minX, y: p[1] - minY,
      ...(i === 0 ? { strokeCap: o.bidirectional ? CAP.end : CAP.start } : {}),
      ...(i === pts.length - 1 ? { strokeCap: CAP.end } : {})
    })),
    segments: pts.slice(1).map((_, i) => ({ start: i, end: i + 1 }))
  });
  v.strokes = [{ type: "SOLID", color: COLOR }];
  v.strokeWeight = WEIGHT;
  if (o.dashed) v.dashPattern = DASH;
  v.name = name;
  parent.appendChild(v);          // appendChild 가 먼저, 좌표는 그 다음
  v.x = minX; v.y = minY;
  return v.id;
}

/* ── 경로 패턴 3종 (도착이 오른쪽 기준. 다른 방향은 축 대칭) ─────────────────── */

/** 1) 직선 — 교차축 좌표가 같을 때 */
async function straight(section, fromName, toName, opts) {
  const s = find(section, fromName), d = find(section, toName);
  return arrow(section, arrowName(fromName, toName),
    [[s.r, s.cy], [d.x - GAP, s.cy]], opts);
}

/** 2) 분기 트렁크 엘보 — 같은 출발점에서 여러 도착지로.
 *  trunkX 는 출발 프레임당 하나로 공유해야 줄기가 겹쳐 한 줄로 보인다. */
async function trunkElbow(section, fromName, toName, trunkX, opts) {
  const s = find(section, fromName), d = find(section, toName);
  const tx = trunkX != null ? trunkX : s.r + TRUNK;
  return arrow(section, arrowName(fromName, toName),
    [[s.r, s.cy], [tx, s.cy], [tx, d.cy], [d.x - GAP, d.cy]], opts);
}

/** 3) 우회(ㄷ자) — 직행 경로가 다른 프레임과 교차할 때 행 위 복도로.
 *  위/아래로 돌아 닿을 땐 좌·우변이 아니라 상·하변을 타겟해야 한다 —
 *  좌변을 노리고 수직 하강하면 화살촉이 변과 평행해 옆 허공을 가리킨다. */
async function detour(section, fromName, toName, corridorY, opts) {
  const s = find(section, fromName), d = find(section, toName);
  const cy = corridorY != null ? corridorY : Math.min(s.y, d.y) - 80;
  return arrow(section, arrowName(fromName, toName),
    [[s.cx, s.y], [s.cx, cy], [d.cx, cy], [d.cx, d.y - GAP]], opts);
}

/** 라벨 pill. 반드시 화살표를 다 만든 뒤 호출한다 — pill 이 z순서 위여야
 *  선이 라벨 텍스트를 관통하지 않는다. (cx, cy) 는 라벨을 얹을 선 위의 중심점. */
async function pill(section, forArrowName, text, cx, cy) {
  const font = LB.font || { family: "Inter", style: "Medium", size: 20 };
  await figma.loadFontAsync({ family: font.family, style: font.style });
  const pad = LB.padding || [10, 5];
  const p = figma.createAutoLayout("HORIZONTAL", { name: LABEL_P + forArrowName });
  p.paddingLeft = pad[0]; p.paddingRight = pad[0];
  p.paddingTop = pad[1]; p.paddingBottom = pad[1];
  p.cornerRadius = LB.corner_radius != null ? LB.corner_radius : 8;
  p.fills = [{ type: "SOLID", color: hx(LB.fill || "#FFFFFF") }];
  p.strokes = [{ type: "SOLID", color: hx(LB.stroke || "#D9DBE3") }];
  p.strokeWeight = 1;
  const t = figma.createText();
  t.fontName = { family: font.family, style: font.style };
  t.fontSize = font.size;
  t.characters = text;
  t.fills = [{ type: "SOLID", color: hx(LB.text_color || "#59616E") }];
  p.appendChild(t);
  section.appendChild(p);
  p.x = cx - p.width / 2;         // hug 측정이 끝난 뒤 중앙 정렬
  p.y = cy - p.height / 2;
  return p.id;
}

/** [state] 상태 체인 — 같은 화면의 인접 상태 변형을 잇는 화살촉 없는 점선.
 *  전환이 아니라 묶음 표시다. 같은 열에 위아래로 맞닿은 쌍에만 쓴다 —
 *  사이에 다른 프레임이 끼면 직선이 그걸 관통한다. */
async function stateLink(section, fromName, toName) {
  const f = find(section, fromName), t = find(section, toName);
  const v = figma.createVector();
  await v.setVectorNetworkAsync({                 // strokeCap 미지정 = 화살촉 없음
    vertices: [{ x: 0, y: 0 }, { x: 0, y: t.y - f.b }],
    segments: [{ start: 0, end: 1 }]
  });
  v.strokes = [{ type: "SOLID", color: COLOR }];
  v.strokeWeight = WEIGHT;
  v.dashPattern = DASH;
  v.name = chainName(fromName, toName);
  section.appendChild(v);
  v.x = f.cx; v.y = f.b;
  return v.id;
}

/** 경로가 다른 프레임을 지나는지. straight 로 판정 후 걸리면 trunkElbow·detour 로 승격한다. */
function hits(section, pts, exclude) {
  const skip = new Set(exclude || []);
  const rects = section.children
    .filter(c => c.type === "FRAME" && !c.name.startsWith(LABEL_P) && !skip.has(c.name))
    .map(c => ({ name: c.name, x: c.x, y: c.y, r: c.x + c.width, b: c.y + c.height }));
  const out = [];
  for (let i = 1; i < pts.length; i++) {
    const sx = Math.min(pts[i-1][0], pts[i][0]), sr = Math.max(pts[i-1][0], pts[i][0]);
    const sy = Math.min(pts[i-1][1], pts[i][1]), sb = Math.max(pts[i-1][1], pts[i][1]);
    for (const f of rects)
      if (sx < f.r && sr > f.x && sy < f.b && sb > f.y) out.push(f.name);
  }
  return [...new Set(out)];
}
