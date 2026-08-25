/* =============================================================================
 * audit-component.js — 컴포넌트 기본값 잔재 감사 (읽기 전용, 쓰기 0)
 *
 * 복제한 인스턴스는 컴포넌트 기본값을 그대로 물고 온다. 라이브러리에서 켜져 있는
 * 표시 토글이 그 화면에서 안 쓰여도 켜진 채 남아 빈 자리가 렌더된다.
 * 축소된 스크린샷에선 안 보여 눈검사로는 계속 빠져나간다 — 수치로만 잡힌다.
 *
 * 판정 기준은 규칙 문서가 아니라 **같은 파일의 실사용 분포**다.
 * 운영 화면에서도 값이 갈리는 속성은 위반이 아니라 용도별 선택이라 보고하지 않는다.
 *
 * 2단계. setCurrentPageAsync 가 호출당 1회라 페이지가 다르면 호출도 나눈다.
 *   MODE="collect" : 참조 페이지에서 컴포넌트별 boolean 속성 분포 수집 → STAT 반환
 *   MODE="compare" : 작업 페이지를 STAT 과 대조 → 위반 + 판정불가 반환
 *
 * 앞에 붙일 것
 *   const CFG  = {...};                      resolve-config.py --js
 *   const MODE = "collect";                  또는 "compare"
 *   const PAGE = "<페이지 이름 일부>";
 *   const STAT = {...};                      compare 모드에서만. collect 결과를 그대로
 *
 * 참조 한 페이지로는 표본이 안 차는 컴포넌트가 남는다. 대상이 폼과 목록을 함께 쓰면
 * 참조도 둘을 뽑아 STAT 을 합산한다. 그래도 없는 건 위반이 아니라 판정 불가다.
 * ========================================================================== */

const C = typeof CFG !== "undefined" ? CFG : {};
const CA = C.component_audit || {};
const MIN_N = CA.min_samples != null ? CA.min_samples : 5;
const DOMINANCE = CA.dominance != null ? CA.dominance : 0.9;
const BODY = CA.body_offset || { left: 0, top: 0 };
const LABEL = (C.naming || {}).label_prefix || "[label] ";

const page = figma.root.children.find(p => p.name.indexOf(PAGE) !== -1);
if (!page) return `페이지 못 찾음: ${PAGE}`;
await figma.setCurrentPageAsync(page);

// 인스턴스의 판정 키는 인스턴스 이름이 아니라 마스터 이름이다.
// 인스턴스는 이름이 바뀌어 있는 경우가 많고, 그걸 키로 쓰면 관례 대조에서 통째로 빠진다.
async function masterName(n) {
  const m = await n.getMainComponentAsync();
  if (!m) return n.name;
  return m.parent && m.parent.type === "COMPONENT_SET" ? m.parent.name : m.name;
}
const boolKeys = p => Object.keys(p).filter(k => typeof p[k].value === "boolean");
const propName = k => k.split("#")[0];        // 속성 id 는 파일마다 달라 이름만 쓴다

if (MODE === "collect") {
  const stat = {};
  for (const n of page.findAll(x => x.type === "INSTANCE" && x.componentProperties)) {
    const p = n.componentProperties, keys = boolKeys(p);
    if (!keys.length) continue;
    const cname = await masterName(n);
    for (const k of keys) {
      const key = cname + "|" + propName(k);
      stat[key] = stat[key] || { t: 0, f: 0 };
      p[k].value ? stat[key].t++ : stat[key].f++;
    }
  }
  return stat;
}

// compare — 화면 공통 껍데기(좌측 내비·상단바)는 화면마다 같은 인스턴스라 대상이 아니다.
// 본문 영역만 본다.
const S = typeof STAT !== "undefined" ? STAT : {};
const issues = [], unknown = {};
for (const s of page.children.filter(c => c.type === "SECTION")) {
  for (const f of s.children.filter(c => c.type === "FRAME" && !c.name.startsWith(LABEL))) {
    const fb = f.absoluteBoundingBox;
    if (!fb) continue;
    for (const n of f.findAll(x => x.type === "INSTANCE" && x.componentProperties)) {
      const b = n.absoluteBoundingBox;
      if (!b) continue;
      if (b.x - fb.x < BODY.left || b.y - fb.y < BODY.top) continue;
      const p = n.componentProperties, keys = boolKeys(p);
      if (!keys.length) continue;
      const cname = await masterName(n);
      for (const k of keys) {
        const key = cname + "|" + propName(k);
        const st = S[key];
        if (!st) { unknown[key] = (unknown[key] || 0) + 1; continue; }
        const tot = st.t + st.f;
        if (tot < MIN_N) continue;
        const norm = st.t / tot >= DOMINANCE ? true : (st.f / tot >= DOMINANCE ? false : null);
        if (norm === null || p[k].value === norm) continue;   // 관례가 갈리면 용도별 선택
        issues.push(`[기본값] ${f.name} / ${n.name === cname ? cname : n.name + "(" + cname + ")"}` +
                    ` ${propName(k)}=${p[k].value} (관례 ${norm}, 표본 ${tot})`);
      }
    }
  }
}
// unknown 은 위반이 아니라 판정 불가 — 참조 페이지를 더 넣어야 한다는 신호다
return {
  component: issues.length ? issues : "COMPONENT PASS",
  unknown: Object.keys(unknown).map(k => k + " x" + unknown[k])
};
