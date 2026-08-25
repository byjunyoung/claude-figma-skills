/* =============================================================================
 * prep-ops.js — 페이지 정리 헬퍼 (프리앰블)
 *
 * 섹션 생성 · 흡수 · 순번 재부여 · placeholder · 공통 참조 주석.
 * arrow-build.js 와 같은 방식으로 쓴다 — 설정 + 이 파일 + 실제 호출.
 *
 * 쓰기 스크립트이므로 호출당 작업을 작게 나누고, 단계마다 감사로 확인한다.
 * ========================================================================== */

const C = typeof CFG !== "undefined" ? CFG : {};
const SS = C.section_style || {}, PS = C.placeholder_style || {};
const LO = C.layout || {}, PG = C.pages || {};

const hx = h => {
  const n = parseInt(String(h).replace("#", ""), 16);
  return { r: ((n >> 16) & 255) / 255, g: ((n >> 8) & 255) / 255, b: (n & 255) / 255 };
};

/** 섹션 생성. z순서를 맨 아래로 내리는 게 필수다 —
 *  안 내리면 새 섹션이 기존 프레임을 흰 배경으로 덮는다. */
function createSection(name, x, y, w, h) {
  const s = figma.createSection();
  s.name = name;
  s.x = x; s.y = y;
  s.resizeWithoutConstraints(w, h);
  // d.ts 엔 fills 만 있지만 런타임 SectionNode 는 strokes·cornerRadius 를 지원한다
  if (SS.fill) s.fills = [{ type: "SOLID", color: hx(SS.fill), opacity: SS.fill_opacity != null ? SS.fill_opacity : 1 }];
  if (SS.stroke) {
    s.strokes = [{ type: "SOLID", color: hx(SS.stroke) }];
    s.strokeWeight = SS.stroke_weight != null ? SS.stroke_weight : 1;
    s.strokeAlign = SS.stroke_align || "INSIDE";
  }
  if (SS.dash) s.dashPattern = SS.dash;
  if (SS.corner_radius != null) s.cornerRadius = SS.corner_radius;
  figma.currentPage.insertChild(0, s);
  return s;
}

/** 흡수 — 프레임을 섹션의 직속 자식으로 만든다.
 *  appendChild 는 로컬 폰트(클라우드 미동기화) 텍스트가 있으면 폰트 로드 실패로 거부되는데,
 *  group→ungroup 은 폰트 검증을 타지 않는다. 수동 드래그가 필요 없다.
 *  jobs: [[frameId, sectionId], ...] */
async function absorb(jobs) {
  const mutatedNodeIds = [];
  for (const [frameId, sectionId] of jobs) {
    const f = await figma.getNodeByIdAsync(frameId);
    const s = await figma.getNodeByIdAsync(sectionId);
    // 좌표 보정은 group 호출 **전의** 부모로 판단한다.
    // 이미 그 섹션의 자식이면 좌표가 이미 상대좌표라, 무조건 빼면 이중 차감으로 섹션 밖으로 튄다.
    const already = f.parent.id === s.id;
    const preX = f.x, preY = f.y;
    const g = figma.group([f], s);
    figma.ungroup(g);
    if (!already) { f.x = preX - s.x; f.y = preY - s.y; }
    mutatedNodeIds.push(frameId);
  }
  return { mutatedNodeIds };
}

/** 섹션 리사이즈 + 이웃 침범 검사.
 *  섹션은 자동 리사이즈되지 않는다. placeholder 를 넣어 섹션을 키울 때 가장 흔한 사고가
 *  아래·옆 행 침범이다. 네 변을 다 봐야 한다 — 세로만 보면 놓친다. */
function resizeSection(section, contentW, contentH) {
  const m = LO.section_resize_margin || [80, 160];
  section.resizeWithoutConstraints(contentW + m[0] * 2, contentH + m[0] * 2);
  const T = { x: section.x, y: section.y, r: section.x + section.width, b: section.y + section.height };
  return figma.currentPage.children
    .filter(c => c.type === "SECTION" && c.id !== section.id)
    .filter(s => s.x < T.r && s.x + s.width > T.x && s.y < T.b && s.y + s.height > T.y)
    .map(s => s.name);          // 비어야 안전
}

/** 순번 재부여 — 캔버스 배열(행 우선) 순으로 NN. 을 다시 매긴다.
 *  보호 대역(폐기 예정 번호대 등)은 건드리지 않는다. */
function renumber() {
  const BUCKET = LO.row_bucket || 1000;
  const PROT = PG.protected_numbers || [];
  const sections = figma.currentPage.children
    .filter(c => c.type === "SECTION" && /^\d+\./.test(c.name) && !PROT.some(p => c.name.startsWith(p)))
    .sort((a, b) => (Math.round(a.y / BUCKET) - Math.round(b.y / BUCKET)) || (a.x - b.x));
  const mutatedNodeIds = [];
  sections.forEach((s, i) => {
    const next = s.name.replace(/^\d+\./, String(i + 1).padStart(2, "0") + ".");
    if (next !== s.name) { s.name = next; mutatedNodeIds.push(s.id); }
  });
  return { mutatedNodeIds, renamed: mutatedNodeIds.length };
}

/** placeholder 프레임. 생성 시점에 올바른 섹션의 자식으로 만든다 —
 *  나중에 흡수하는 것보다 이게 원칙이다. 정책이 미정이면 desc 에 TBD 를 병기한다. */
async function placeholder(section, name, desc, w, h, relX, relY) {
  const font = PS.font || { family: "Inter", style: "Regular", size: 28 };
  await figma.loadFontAsync({ family: font.family, style: font.style });
  const f = figma.createFrame();
  f.name = name;                                   // 네이밍 규칙 그대로 — 이후 화살표 대상이 된다
  f.resize(w, h);
  f.fills = [{ type: "SOLID", color: hx(PS.fill || "#FAFAFB") }];
  f.strokes = [{ type: "SOLID", color: hx(PS.stroke || "#B3B3BF") }];
  f.strokeWeight = PS.stroke_weight != null ? PS.stroke_weight : 2;
  f.dashPattern = PS.dash || [10, 8];               // 점선 테두리 = placeholder 식별자
  const t = figma.createText();
  t.fontName = { family: font.family, style: font.style };
  t.fontSize = font.size;
  t.characters = (PS.text_prefix || "Placeholder — ") + desc;
  t.fills = [{ type: "SOLID", color: hx(PS.text_color || "#73787F") }];
  f.appendChild(t); t.x = 40; t.y = 40;
  section.appendChild(f);
  f.x = relX; f.y = relY;
  return f.id;
}

/** 공통 반복 상태(범용 Empty·Error·Loading)는 화면마다 복제하지 않는다.
 *  공통 페이지에 한 벌만 두고, 각 화면 Default 에 참조 주석을 단다.
 *  페이지 간 노드 하이퍼링크(setRangeHyperlink NODE)는 막혀 있어 URL 딥링크를 쓴다. */
function commonRef(defaultFrame, fileKey, commonPageId, label) {
  const url = `https://www.figma.com/design/${fileKey}/?node-id=${String(commonPageId).replace(":", "-")}`;
  defaultFrame.annotations = [{ labelMarkdown: `${label || "빈·오류·로딩 상태"} → [공통 페이지](${url})` }];
  return { mutatedNodeIds: [defaultFrame.id] };
}
