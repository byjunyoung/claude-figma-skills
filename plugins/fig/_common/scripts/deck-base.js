/* =====================================================================
 * DECK BASE — Figma Slides 빌드 공통 헬퍼
 *
 * 빌드 스크립트 맨 위에 이 파일을 붙이고, 그 아래에 /fig:deck-setup 이 만든
 * template.js (팔레트 C · 타이포 T · 레이아웃 상수 · 아키타입 빌더) 를 붙인다.
 * 순서가 이 방향이어야 한다 — 여기 함수들은 선언이라 끌어올려지고, C·T 는
 * 호출 시점에만 읽히므로 아래에서 정의돼도 된다.
 *
 * 이 파일에는 **값이 없다.** 색·크기·좌표는 전부 template.js 몫이다.
 * 여기 값을 박으면 다른 팀 템플릿에서 그 값이 그대로 새어 나간다.
 *
 * template.js 가 정의해야 하는 것
 *   C     { bg, text, textMuted, cardSurface, ... }   0~1 범위 색
 *   T     { title, h1, h2, body1, ... }               {size, style, ls, lh}
 *   FAMS  ['Pretendard', 'Inter']                     선호 순 폰트 후보
 *
 * use_figma 규칙이 박혀 있다 — appendChild 를 x/y 보다 먼저, characters 전에
 * 폰트 로드, 색은 0~1, fills 는 새 배열로 재대입.
 * ===================================================================== */

function hx(h) {
  const n = parseInt(h.slice(1), 16);
  return { r: ((n >> 16) & 255) / 255, g: ((n >> 8) & 255) / 255, b: (n & 255) / 255 };
}

/* ---- 폰트 -------------------------------------------------------------
 * 클라우드 환경에는 팀 폰트가 없을 수 있다. 후보를 순서대로 찔러 있는 것을 쓴다.
 * 굵기 이름이 패밀리마다 달라서(Inter 는 'Semi Bold', 대개는 'SemiBold')
 * f() 로 한 겹 감싼다. */
let FAM = null;
async function loadFonts() {
  const avail = await figma.listAvailableFontsAsync();
  const fams = new Set(avail.map(a => a.fontName.family));
  const want = (typeof FAMS !== 'undefined' && FAMS.length) ? FAMS : ['Inter'];
  FAM = want.find(x => fams.has(x)) || (fams.has('Inter') ? 'Inter' : want[0]);
  const styles = FAM === 'Inter'
    ? ['Bold', 'Semi Bold', 'Medium', 'Regular']
    : ['Bold', 'SemiBold', 'Medium', 'Regular'];
  await Promise.all(styles.map(s => figma.loadFontAsync({ family: FAM, style: s }).catch(() => {})));
  return FAM;
}
function f(style) {
  if (FAM === 'Inter' && style === 'SemiBold') return { family: FAM, style: 'Semi Bold' };
  return { family: FAM, style: style };
}

/* ---- named 텍스트 스타일 바인딩 ----------------------------------------
 * 빌드가 끝난 뒤 각 TEXT 를 family|style|size 로 파일의 named 스타일에 묶는다.
 * 못 찾으면 raw 값으로 남긴다 — 사다리 밖 크기나 폰트 대체 상황에서는 정상이다.
 * 색은 건드리지 않는다(텍스트 스타일은 타입만 담는다). */
let _styleIdx = null;
async function applyTextStyles(root) {
  if (!_styleIdx) {
    _styleIdx = {};
    for (const s of await figma.getLocalTextStylesAsync()) {
      _styleIdx[`${s.fontName.family}|${s.fontName.style}|${s.fontSize}`] = s.id;
    }
  }
  const texts = root.type === 'TEXT' ? [root] : root.findAllWithCriteria({ types: ['TEXT'] });
  let bound = 0;
  for (const t of texts) {
    if (typeof t.fontName === 'symbol') continue;          // 여러 서식이 섞인 런
    const id = _styleIdx[`${t.fontName.family}|${t.fontName.style}|${t.fontSize}`];
    if (id && t.textStyleId !== id) { try { await t.setTextStyleIdAsync(id); bound++; } catch (e) {} }
  }
  return bound;
}

/* ---- 요소 헬퍼 (appendChild → 속성 → x/y) -------------------------------
 * 순서를 바꾸면 노드가 밀린다. 헬퍼를 쓰면 순서가 강제된다. */

// 테마가 입혀진 예시 슬라이드 id 를 넣어두면 그걸 복제해 테마를 물려받는다.
// 비어 있으면 createSlide 로 맨 슬라이드를 만든다 — 폰트·색이 'Pick a style' 로 깨진다.
let REF_SLIDE = null;
function newSlide(bg) {
  let s;
  if (REF_SLIDE) {
    const ref = figma.getNodeById(REF_SLIDE);
    s = ref.clone();
    for (const c of [...s.children]) c.remove();
  } else {
    s = figma.createSlide();
  }
  s.fills = [{ type: 'SOLID', color: bg || C.bg }];
  return s;
}

function addText(parent, o) {
  const t = figma.createText(); parent.appendChild(t);
  const p = o.preset ? T[o.preset] : {};
  t.fontName = f(o.style || p.style || 'Regular');
  t.characters = o.chars || '';
  t.fontSize = o.size || p.size || 24;
  t.textAlignHorizontal = o.align || 'LEFT';
  t.fills = [{ type: 'SOLID', color: o.color || C.text, opacity: (o.fillOpacity != null ? o.fillOpacity : 1) }];
  const ls = (o.ls != null ? o.ls : p.ls); if (ls != null) t.letterSpacing = { unit: 'PERCENT', value: ls };
  const lh = (o.lh != null ? o.lh : p.lh); if (lh != null) t.lineHeight = { unit: 'PERCENT', value: lh };
  if (o.w) { t.textAutoResize = 'HEIGHT'; t.resize(o.w, t.height); }
  if (o.x != null) t.x = o.x; if (o.y != null) t.y = o.y;
  return t;
}

function addRect(parent, o) {
  const r = figma.createRectangle(); parent.appendChild(r);
  r.resize(o.w, o.h);
  r.fills = [{ type: 'SOLID', color: o.fill || C.cardSurface }];
  if (o.radius) r.cornerRadius = o.radius;
  if (o.x != null) r.x = o.x; if (o.y != null) r.y = o.y;
  return r;
}

// scaleMode 'FIT' 는 안 자른다(기본). 'FILL' 은 잘린다 — 사진·배경에만.
function addImageRect(parent, o) {
  const r = figma.createRectangle(); parent.appendChild(r);
  r.resize(o.w, o.h);
  if (o.radius) r.cornerRadius = o.radius;
  r.fills = o.imageHash
    ? [{ type: 'IMAGE', imageHash: o.imageHash, scaleMode: o.scaleMode || 'FIT' }]
    : [{ type: 'SOLID', color: C.cardSurface }];       // 이미지 준비 전 자리
  if (o.x != null) r.x = o.x; if (o.y != null) r.y = o.y;
  return r;
}

function addLine(parent, o) {                            // 가는 선·대각 모티프. rot 은 도(°)
  const l = figma.createLine(); parent.appendChild(l);
  l.resize(o.len, 0);
  if (o.rot) l.rotation = o.rot;
  l.strokes = [{ type: 'SOLID', color: o.color || C.text }];
  l.strokeWeight = o.weight || 1;
  if (o.x != null) l.x = o.x; if (o.y != null) l.y = o.y;
  return l;
}

// 오토레이아웃 프레임 안의 텍스트. 슬라이드 직속에 layoutSizing 을 쓰면 던진다
function alText(parent, o) {
  const t = addText(parent, o);
  if (o.fill) t.layoutSizingHorizontal = 'FILL';
  return t;
}

/* ---- 측정 -------------------------------------------------------------
 * 자동 꺾임 검사의 기준. 렌더 줄 수가 수동 개행 수보다 크면 조판기가
 * 낱말 한가운데를 자르고 있다는 뜻이다. */
function renderedLines(t) {
  const lh = (t.lineHeight && t.lineHeight.unit === 'PERCENT') ? t.lineHeight.value / 100 : 1.2;
  return Math.round(t.height / (t.fontSize * lh));
}
function manualLines(t) {
  return typeof t.characters === 'string' ? t.characters.split('\n').length : 1;
}
function isWrapped(t) { return renderedLines(t) > manualLines(t); }

/* ---- 좌표 -------------------------------------------------------------
 * 슬라이드 자식의 x/y 는 슬라이드 기준이 아니라 부모 기준이다.
 * absoluteBoundingBox 로 읽은 값을 그대로 쓰면 슬라이드 폭만큼 밀려난다. */
function relTo(slide, node) {
  const a = node.absoluteBoundingBox, s = slide.absoluteBoundingBox;
  return { x: a.x - s.x, y: a.y - s.y, w: a.width, h: a.height };
}
