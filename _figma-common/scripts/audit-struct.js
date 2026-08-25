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

return issues.length ? issues : "STRUCT PASS";
