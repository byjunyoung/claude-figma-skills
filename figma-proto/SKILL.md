---
name: figma-proto
description: Figma 디자인을 코드로 재현해, 실제 입력·유효성·상태·동적 분기가 동작하는 단일 HTML 프로토타입을 만든다. 스크린샷 클릭 데모가 아니라 진짜 눌러보며 UX를 검증하고 개발 스펙 감을 잡는 용도. 인터뷰로 범위를 맞추고 → 피그마를 정합하게 읽어(구조+정확한 라벨+시각 토큰) → 바닐라 단일 HTML로 빌드 → 브라우저로 실제 동작을 검증하는 파이프라인. Triggers - "/figma-proto", "동작 프로토타입 만들어", "프로토타이핑 해줘", "피그마에 그린 대로 동작하게", "실제로 눌러보고 입력되게", "유효성·상태 되는 프로토타입".
allowed-tools: AskUserQuestion, Bash, Read, Write, Edit, mcp__plugin_figma_figma__get_design_context, mcp__plugin_figma_figma__get_screenshot, mcp__plugin_figma_figma__get_metadata, mcp__plugin_figma_figma__use_figma, mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__computer, mcp__claude-in-chrome__browser_batch, mcp__claude-in-chrome__read_console_messages
---

# figma-proto — Figma 디자인 → 동작 프로토타입 (코드 재현)

Figma에 그려진 화면을 **코드로 재현**해, 폼 입력·유효성·상태 변화·동적 분기가 실제로 동작하는 단일 HTML 프로토타입을 만든다. 스크린샷을 눌러 넘기는 클릭 데모가 아니라, 진짜 값을 넣고 저장이 목록에 반영되는 걸 눌러보는 **동작 검증·개발 스펙 감**용.

**핵심 전제:** 코드 재현이라 **시각은 근사**(디자인 100% 픽셀은 아님) — 대신 실제로 동작한다. 무빌드·무의존성 단일 HTML이라 더블클릭으로 열린다. 픽셀 정합이 최우선인 발표용 데모라면 이 방식이 아니라 스크린샷 기반이 맞다(현재 전용 스킬 없음, 수동 캡처).

**"근사"의 범위 — 레이아웃·색·간격까지다. 에셋은 아니다.** 그림·일러스트·아이콘·사진처럼 **디자인에 이미 이미지로 존재하는 것은 코드로 다시 그리지 말고 원본을 그대로 인라인**한다(3단계). 코드로 흉내 낸 그림은 원본보다 항상 못하고, 무엇보다 **디자인에 없는 동작을 발명하게 된다** — 정지 이미지를 벡터로 다시 그리면서 "값에 따라 움직이게" 만드는 순간, 프로토타입이 존재하지 않는 스펙을 개발자에게 전달한다.

## When to invoke

- "동작 프로토타입", "실제로 눌러보게", "입력·유효성 되게", "피그마에 그린 대로 동작하게 만들어"
- "프로토타이핑 해줘"(입력·상태가 동작하길 원하는 맥락)
- "/figma-proto" 명시 호출

## When NOT to invoke

- 픽셀 그대로 화면만 클릭해 넘기는 데모(입력 불필요) → 스크린샷 기반(전용 스킬 없음, 수동)
- 프로덕션 코드로 이식(프론트 레포 반영) → `/figma-code`
- 프레임 목록·구조만 보기 → `/figma-read`
- 그려진 화면의 구조·흐름 검증(lint) → `/figma-lint`

## Inputs

- `figma_url` (필수): figma.com/design/:fileKey/...?node-id=... — 대상 페이지/화면. 없으면 요청.
- 대상 흐름 (선택): 어느 화면·플로우 중심인지. 없으면 1단계 인터뷰에서 정한다.

## 산출물 위치 / 배포

경로·퍼블리시 대상은 `figma-conventions.yaml` 의 `tools` 절이 정한다 — `python3 ~/.claude/skills/_figma-common/scripts/lib/resolve-config.py` 로 읽는다.

- 기본 = 로컬 단일 HTML. 위치는 설정 `tools.proto_output_dir`, 파일명은 `<이름>-prototype.html`. 파일 하나라 더블클릭으로 열린다.
- 퍼블리시(선택)는 설정 `tools.proto_publish`(레포·계정·공개범위)를 따른다. `null` 이면 로컬까지만 하고 퍼블리시를 제안하지 않는다. 본문에 레포·계정을 하드코딩하지 않는다.

---

## Procedure

### 1. 인터뷰 — 무엇이 되면 끝인지 (CLAUDE.md 1)

충실도는 이 스킬 = **동작**으로 고정. 나머지만 순차로 확인(AskUserQuestion, 각 질문에 권장안 부착, 한 번에 하나씩). 먼저 정할 항목 전체를 공유해 규모를 알린 뒤:

- **범위**: 전체 화면 vs 핵심 플로우 한 줄기(예: 생성→목록→상세). 동작 프로토타입은 전체보다 **핵심 흐름 집중**이 토큰·가치 균형이 좋다 — 보통 폼(입력 로직의 핵심)에 무게.
- **데이터**: 고정 목업 vs 세션 내 상태 유지(만든 게 목록에 반영). 생성 흐름이면 상태 유지가 사실상 필수.
- **기준 폭**: 데스크톱/모바일(피그마 그대로).
- **기술·배포**: 단일 HTML 바닐라(권장) vs React 등, 로컬만 vs 퍼블리시.

완료 조건을 검증 가능한 형태로 못박고(어느 카드·분기·상태가 동작해야 끝인지), 여러 단계면 시작 전 단계 계획을 공유한다.

### 2. 피그마 정합 읽기 (읽기 전용 — 컨펌 불필요, 적극 탐색)

"그린 대로" 옮기려면 라벨·구조·시각을 다 확보해야 한다. 대상 프레임 id는 URL의 `node-id`(그 프레임/페이지), 또는 `get_metadata`(페이지 nodeId)로 섹션→화면 프레임을 열거해 얻는다. 이후 네 소스를 조합한다:

- **구조** — 대상 화면에 `get_design_context`. 프레임 트리·필드 배치·컴포넌트 골격을 준다. 단 **큰 프레임은 sparse로 오고 텍스트가 `text`로 마스킹**돼 실제 라벨이 안 나온다(레이아웃만 파악).
- **정확한 라벨** — 그래서 `use_figma` 읽기 전용 스크립트로 프레임 내 모든 TEXT의 `characters`+절대좌표+hidden 여부를 한 번에 수집한다(get_design_context를 서브레이어마다 반복하는 것보다 토큰이 훨씬 싸다). 좌표로 필드↔라벨을 매핑하고, **hidden 텍스트에서 필수(*)·기본값·분기 힌트·헬퍼 문구**까지 읽어낸다. 목록·상세의 **예시 행·값도 여기서 수확**해 프로토타입 시드로 쓴다.

```js
// 프레임 내 모든 TEXT characters + 절대좌표 수집 (읽기 전용, return만)
const page = figma.root.children.find(p => p.id === "<PAGE_ID>");
await figma.setCurrentPageAsync(page);
const g = (n,k)=>{try{return n[k]}catch(e){return undefined}};   // phantom-safe
const collect = async (id) => {
  const root = await figma.getNodeByIdAsync(id), out = [];
  const walk = (n) => { if(!n) return;
    if (n.type==="TEXT") { const ch=g(n,"characters");
      if (ch && ch.trim()) { const b=n.absoluteBoundingBox;
        out.push({ y:b?Math.round(b.y):0, x:b?Math.round(b.x):0, t:ch, h:!n.visible?1:0 }); } }
    const kids=g(n,"children"); if(kids) for(const k of kids) walk(k); };
  walk(root); out.sort((a,b)=> a.y-b.y || a.x-b.x); return out;
};
return { form: await collect("<FRAME_ID>") };   // 여러 프레임이면 한 스크립트에서 묶어 반환
```

- **시각 토큰** — 화면당 전부 찍지 말고 **대표 1~2장만** `get_screenshot`(maxDimension로 가독 확보) → `curl`로 저장 → `Read`. 색·간격·라운드·컴포넌트 룩·버튼 스타일만 뽑는다(라벨은 이미 TEXT 워크로 확보). 목록형 1장 + 폼형 1장이면 대개 충분.

- **이미지 에셋 목록** — TEXT 워크와 같은 요령으로 **IMAGE fill을 가진 노드를 스캔**해 목록을 만든다. 이게 "코드로 그리지 말고 가져올 것"의 확정 목록이 된다. 함께 확인할 것: 그 노드의 **자식으로 얹힌 오버레이**(표식·번호·배지 등)가 있는지 — 있으면 노드째 export하면 오버레이까지 원본 그대로 따라온다.

```js
// IMAGE fill 노드 스캔 (읽기 전용) — 결과가 곧 3단계에서 인라인할 에셋 목록
const g=(n,k)=>{try{return n[k]}catch(e){return undefined}};
const scan = async (frameId) => {
  const root = await figma.getNodeByIdAsync(frameId), hits = [];
  const walk = n => { if(!n) return;
    const fills = g(n,"fills");
    if (Array.isArray(fills) && fills.some(f => f.type === "IMAGE"))
      hits.push({ id:n.id, name:n.name, type:n.type,
                  w:Math.round(n.width), h:Math.round(n.height),
                  kids:(g(n,"children")||[]).length });   // kids>0 = 오버레이 있음
    for (const k of (g(n,"children")||[])) walk(k); };
  walk(root); return hits;
};
return await scan("<FRAME_ID>");
```

### 3. 단일 HTML 동작 빌드 (바닐라, 무빌드·무의존성)

**자기완결 단일 파일**로 만든다 — CSS·JS·**이미지까지 전부 인라인**, 외부 폰트·CDN·이미지 **링크**만 없음(폰트는 시스템 스택). 이래야 `file://` 더블클릭만으로 열리고, 검증용 서버 없이도 사용자 손에서 그대로 돈다. **"링크 금지"는 "에셋 금지"가 아니다** — 이미지는 링크가 아니라 `data:` URI로 넣는 것이 이 원칙을 지키는 방법이다.

- **이미지 에셋 인라인 (기본값 — 빼려면 물어본다)**: 2단계에서 스캔한 IMAGE 노드를 `get_screenshot`으로 PNG export → `curl` 저장 → **base64 `data:` URI로 치환**. 실무상 장당 수십 KB, 여러 장 합쳐도 수백 KB라 단일 HTML에 부담이 없다(용량 때문에 뺄 일이 거의 없다는 뜻 — 정말 클 때만 사용자에게 알리고 판단을 받는다).
  - HTML에는 `__IMG_<NAME>__` 같은 **placeholder만 적고**, base64는 Bash+Python으로 치환한다. 긴 base64를 에디터 도구로 직접 쓰면 토큰을 통째로 낭비한다.
  - export 배율은 원본 크기가 상한이다(작은 노드를 maxDimension으로 키워도 확대되지 않음). 선명도가 필요하면 Figma에서 더 큰 노드를 고르거나 원본 배율을 확인한다.
  - `contentsOnly: true`로 찍으면 무관한 겹침 요소가 빠지고, 그 노드의 **자식 오버레이는 그대로 포함**된다.

```bash
# placeholder → base64 data URI 치환 (HTML에 __IMG_A__ 형태로 미리 적어둔 뒤 실행)
python3 - <<'PY'
import base64, pathlib
html = pathlib.Path('<산출물.html>')
s = html.read_text()
for token, f in (('__IMG_A__','a.png'), ('__IMG_B__','b.png')):
    if token not in s: raise SystemExit(f'placeholder 없음: {token}')
    s = s.replace(token, 'data:image/png;base64,' + base64.b64encode(pathlib.Path(f).read_bytes()).decode())
html.write_text(s)
print('치환 완료', round(html.stat().st_size/1024), 'KB')
PY
```

- **코드로 그릴 것 vs 가져올 것**: 값·상태에 따라 **실제로 변해야 하는 것만** 코드로 그린다(채워지는 게이지, 상태에 따라 켜지는 셀, 입력에 반응해 회전하는 요소 등 — **디자인에 그 변형이 그려져 있는 경우에 한해**). 디자인에서 한 장으로 고정된 그림은 그대로 가져온다. 판단이 서지 않으면 "이 화면의 상태 변형 프레임에 이 요소가 다르게 그려져 있나?"로 가른다 — 아니면 정적이다.

- **디자인 토큰**: 스크린샷에서 뽑은 색·간격·라운드를 `:root` CSS 변수로. 하드코딩 흩뿌리지 말고 토큰 경유. 라이트/어드민 톤 등 원본 무드를 맞춘다.
- **레이아웃·라우팅**: SPA — `state.view` 기반 `render()`, **이벤트 위임**(`#app`에 click/input/change 하나씩, `data-action`/`data-field`로 분기). 전체 재렌더는 **구조 변화**(라디오·탭·행 추가/삭제)에만. **텍스트 입력은 모델만 갱신하고 재렌더하지 않는다**(포커스 유지).
- **폼 모델·동적 분기**: `form` 객체 하나가 진실. 분기(유형별 값 필드·범위별 대상·발급 방식 등)는 모델→조건부 렌더. 반복 블록(규칙 N개)은 배열.
- **유효성**: 저장 시 `validate()`→필드 빨강+헬퍼 에러+토스트, 첫 에러로 스크롤. 규칙(예: 상호 배타 옵션 차단)은 렌더 단계에서 비활성 + 저장 단계에서 재확인.
- **상태 유지**: 저장→배열 추가→목록 반영, 자동 ID·성공 토스트. 그려진 다이얼로그(이탈·삭제·비활성화 등) 구현.
- **커스텀 위젯**(멀티셀렉트 등): 상태 하나(열림/선택)로, 바깥 클릭 시 닫기. `data-stop` 같은 표식으로 위임 핸들러에서 내부/외부 클릭 구분.
- **충실도 원칙**: 라벨·용어·순서·시드는 피그마 그대로. **명백한 클론 잔재 오라벨**(예: 쿠폰 목록인데 컬럼이 '상품 ID')은 맥락 맞게 고치되 **보고에 명시** — 임의 개선 금지, 알린다(CLAUDE.md 4).

### 4. 브라우저 검증 (필수 — CLAUDE.md 7)

- **`file://` 은 claude-in-chrome가 못 연다** → `python3 -m http.server <port>`(산출물 폴더에서)로 서빙한 뒤 `navigate` http://localhost:<port>/<파일>.
- claude-in-chrome로 핵심 흐름을 **실제 클릭**: 목록 렌더 / 폼 동적 분기(대표 1~2) / 유효성(에러 표시) / 저장→목록 반영 / 상세 / 다이얼로그. `browser_batch`로 클릭+스크린샷을 묶어 왕복을 줄인다(좌표는 직전 스크린샷 기준).
- 발견한 버그는 그 자리서 고치고 **재확인**한다(스크린샷만 보고 넘기지 말 것). 검증 끝나면 서버 종료. 사용자는 파일 더블클릭(file://)으로 열면 됨 — 외부 자원 0이라 동작한다.
- 새로고침 직후 클릭은 렌더 전에 먹힐 수 있음(타이밍) — 한 배치에 navigate+클릭을 몰지 말고 로드 확인 후 진행.

### 5. 핸드오프 보고 (CLAUDE.md 6·7)

- 산출물 위치, **검증한 흐름**(무엇을 실제 눌러 확인했는지).
- 범위(In/Out): 담긴 플로우 vs 뺀 것(미시연 케이스·배포 여부).
- 고친 오라벨, 목업 한계(새로고침 시 초기화 등), 미동작 요소(검색창 표시만 등)를 솔직히.

## 퍼블리시 (선택)

외부 쓰기이므로 **미리보기 → "go"** 게이트(CLAUDE.md 5). 설정 `tools.proto_publish` 에서 레포·계정·공개범위를 확인한다(회사 화면이면 공개범위를 반드시 확인). 설정이 `null` 이면 어디에 올릴지 먼저 묻는다. 단일 HTML이라 화면 폴더 없이 **파일 하나만** 올리면 된다. 코드 재현이라 픽셀 diff 자동갱신은 불필요 — 소스 수정→재검증→재푸시.

## Constraints

- 코드 재현 — 시각은 근사(픽셀 100% 아님). 픽셀 정합이 최우선이면 이 방식 아님. **단 이미지 에셋은 근사 대상이 아니다 — 원본을 인라인한다**(3단계).
- **디자인에 없는 동작을 만들지 않는다.** 정적인 요소를 "값에 반응하게" 바꾸는 건 개선이 아니라 없는 스펙의 발명이다. 동적 처리는 디자인에 상태 변형이 그려져 있는 요소로 한정하고, 해석을 넣었다면 보고에 명시한다(CLAUDE.md 4·6).
- 본문에 프로젝트 고유명사(레포·계정·파일키·특정 화면명) 하드코딩 금지 — 메모리에서(`feedback_skill_writing_generic`).
- 라벨·용어·시드는 피그마 정합 — 임의 개선 말고 오라벨은 보고(CLAUDE.md 4).
- 검증 없이 "동작한다" 단정 금지 — 브라우저 실제 클릭(CLAUDE.md 7).
- `file://` 불가 → http.server 경유해 검증.

## Notes

- 네 소스는 상호보완이다: `get_design_context`=구조·좌표, TEXT 워크=문자열(라벨·시드·hidden), 스크린샷=시각 토큰, IMAGE fill 스캔=그대로 가져올 에셋. 어느 하나로 다 되지 않는다.
- REST `get_screenshot`은 쓰기 직후 옛 상태를 반환할 수 있음(스테일) → `node.screenshot()` 인라인 렌더로 우회(이 스킬은 주로 읽기라 드묾).
- 프로젝트 고유 값은 설정 `tools` 절에서 읽는다. 본문에 레포·계정·파일키·화면명을 적지 않는다.
- 관련 스킬: `/figma-read`(구조만), `/figma-code`(프론트 레포 반영), `/figma-lint`(그린 화면 검증).
