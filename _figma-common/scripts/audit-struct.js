/* =============================================================================
 * audit-struct.js — 구조 감사 (읽기 전용, 쓰기 0)
 *
 * 검사: 프레임 소속 · 경계 이탈 · 프레임 겹침 · 섹션 겹침 · 네이밍
 *
 * 사용
 *   1) python3 scripts/lib/resolve-config.py --js <fileKey>   → `const CFG = {...};`
 *   2) 그 한 줄을 이 파일 앞에 붙여 use_figma 에 넣는다
 *   3) 다른 페이지를 볼 땐 맨 앞에 setCurrentPageAsync 한 줄 (스크립트당 1회)
 *
 * 반환: 위반 문자열 배열, 없으면 "STRUCT PASS"
 *
 * 패턴이 null 이면 그 검사를 건너뛴다 — 규약 없는 파일에서 전건 오탐을 막는다.
 * 좌표·부모 검사는 설정과 무관하게 항상 돈다(기하의 문제라 규약이 없어도 참이다).
 * ========================================================================== */

const C = typeof CFG !== "undefined" ? CFG : {};
const N = C.naming || {}, P = C.pages || {};

const reOrNull = s => (s ? new RegExp(s) : null);
const anyOf = a => (a && a.length ? new RegExp(a.join("|")) : null);

const NAME_RE = reOrNull(N.frame_pattern);
const SEC_RE = reOrNull(N.section_pattern);
const SEC_EXCLUDE = anyOf(P.exclude_sections);
const LABEL = N.label_prefix || "[label] ";

const skipSection = s => !!(SEC_EXCLUDE && SEC_EXCLUDE.test(s.name));
const isScreen = n => n.type === "FRAME" && !n.name.startsWith(LABEL);
const r = v => Math.round(v);

const issues = [];
const secs = figma.currentPage.children.filter(c => c.type === "SECTION");

// 페이지 직속 화면 프레임 = 섹션 흡수 누락.
// clone()·createFrame 의 기본 부모가 currentPage 라 흡수를 빠뜨리면 여기로 샌다.
for (const f of figma.currentPage.children)
  if (isScreen(f))
    issues.push(`[소속] 페이지 직속(섹션 미흡수): ${f.name} @abs ${r(f.x)},${r(f.y)}`);

for (const s of secs) {
  if (skipSection(s)) continue;
  const frames = s.children.filter(isScreen);

  for (const f of frames) {
    // 경계 이탈 — 섹션 자식의 x/y 는 섹션 기준 상대좌표다.
    // 절대좌표를 그 자리에 박으면 프레임이 섹션 밖으로 튄다.
    if (f.x < 0 || f.y < 0 || f.x + f.width > s.width || f.y + f.height > s.height)
      issues.push(`[경계] ${s.name} / ${f.name} 이탈 (rel ${r(f.x)},${r(f.y)} ${r(f.width)}x${r(f.height)} vs 섹션 ${r(s.width)}x${r(s.height)})`);
    if (NAME_RE && !NAME_RE.test(f.name))
      issues.push(`[네이밍] ${s.name} / ${f.name} (패턴 불일치)`);
  }

  for (let i = 0; i < frames.length; i++)
    for (let j = i + 1; j < frames.length; j++) {
      const a = frames[i], b = frames[j];
      if (a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y)
        issues.push(`[프레임겹침] ${s.name}: ${a.name} ∩ ${b.name}`);
    }

  if (SEC_RE && !SEC_RE.test(s.name))
    issues.push(`[네이밍] 섹션 ${s.name} (패턴 불일치)`);
}

// 섹션 겹침 — 제외 섹션은 어느 쪽이든 대상에서 뺀다
for (let i = 0; i < secs.length; i++)
  for (let j = i + 1; j < secs.length; j++) {
    const a = secs[i], b = secs[j];
    if (skipSection(a) || skipSection(b)) continue;
    if (a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y)
      issues.push(`[섹션겹침] ${a.name} ∩ ${b.name}`);
  }

// ── 순번 어긋남 — 캔버스 배열(행 우선)과 NN. 순번이 맞는가 ─────────────────────
// 보호 번호대는 재부여 대상이 아니므로 검사도 하지 않는다.
const BUCKET = (C.layout || {}).row_bucket || 1000;
const PROT = P.protected_numbers || [];
const numbered = secs
  .filter(s => !skipSection(s) && /^\d+\./.test(s.name) && !PROT.some(p => s.name.startsWith(p)))
  .sort((a, b) => (Math.round(a.y / BUCKET) - Math.round(b.y / BUCKET)) || (a.x - b.x));
numbered.forEach((s, i) => {
  const want = String(i + 1).padStart(2, "0");
  const have = s.name.match(/^(\d+)\./)[1];
  if (have !== want) issues.push(`[순번] ${s.name} → ${want}. (캔버스 ${i + 1}번째)`);
});

// ── 상태 변형 분리 — 같은 화면의 상태 변형이 한 열에서 끊겼는가 ─────────────────
// 부모 화면과 상태 변형 사이에 전환 결과(모달·다이얼로그)가 끼면 [state] 점선이
// 직선이라 그걸 관통한다. 배치 단계에서 잡아야 화살표 단계가 깨끗해진다.
const screenOf = n => n.replace(/-[^-]+$/, "");     // 마지막 접미사를 뗀 [화면명]
for (const s of secs) {
  if (skipSection(s)) continue;
  const frames = s.children.filter(isScreen)
    .map(f => ({ name: f.name, screen: screenOf(f.name), x: f.x, y: f.y, b: f.y + f.height }));
  const byScreen = {};
  for (const f of frames) (byScreen[f.screen] = byScreen[f.screen] || []).push(f);
  for (const [screen, group] of Object.entries(byScreen)) {
    if (group.length < 2) continue;
    // 같은 열(x 근접)에 있는 것끼리만 본다 — 열이 다르면 애초에 [state] 대상이 아니다
    const cols = {};
    for (const f of group) { const k = Math.round(f.x / 8); (cols[k] = cols[k] || []).push(f); }
    for (const col of Object.values(cols)) {
      if (col.length < 2) continue;
      col.sort((a, b) => a.y - b.y);
      for (let i = 1; i < col.length; i++) {
        const top = col[i - 1].b, bot = col[i].y;
        const intruder = frames.find(o =>
          o.screen !== screen && Math.abs(o.x - col[i].x) < 8 && o.y >= top && o.y < bot);
        if (intruder)
          issues.push(`[상태분리] ${s.name}: ${col[i - 1].name} 과 ${col[i].name} 사이에 ${intruder.name} 이(가) 끼어 있음`);
      }
    }
  }
}

return issues.length ? issues : "STRUCT PASS";
