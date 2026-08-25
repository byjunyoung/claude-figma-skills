---
name: sync
description: 작업 페이지·업데이트 페이지에서 끝난 변경이 운영(정본) 페이지에 실제로 반영됐는지 전수 감사하고, 미반영분을 정본에 반영한 뒤 작업분을 아카이브로 이관한다. 팀 Figma 관리 가이드의 "릴리즈 후 운영 반영" 장을 집행하는 스킬 — 감사(쓰기 0) → 반영 → 이관 순으로 각 단계마다 미리보기·go 게이트. 프레임 이름이 양쪽 같아 이름 대조로는 안 잡히므로 텍스트 diff·높이·컴포넌트 마스터 3신호로 판정한다. Triggers - "/fig:sync", "정본 반영 안 된 것 찾아줘", "운영 페이지 최신화", "미반영 전수 검사", "릴리즈 정본 반영해줘", "정본에 흡수해줘", "교체 안 된 화면 찾아줘".
allowed-tools: AskUserQuestion, Bash, Read, Write, mcp__plugin_figma_figma__use_figma, mcp__plugin_figma_figma__get_metadata, mcp__plugin_figma_figma__get_screenshot, mcp__claude_ai_Notion__notion-fetch
---

# fig:sync — 정본 최신화 (감사 → 반영 → 이관)

개발이 끝난 화면이 운영 페이지(정본)에 실제로 들어갔는지 전수로 대조하고, 빠진 것을 반영한 뒤 작업분을 아카이브로 옮긴다. 가이드가 정의한 릴리즈 후 절차를 사람 대신 집행하는 자리다.

정본은 "현재 운영 중인 모습"이어야 하는데, 개발 반영과 정본 갱신은 서로 다른 시점에 일어난다. 그 사이가 벌어진 채로 방치되면 개발·QA가 옛 화면을 보고 판단한다. **이 스킬이 막는 사고는 그 시차다.**

**전제**: `use_figma` 호출 전 반드시 `figma:figma-use` 로드. 1단계(감사)는 **쓰기 0** — `use_figma`를 `return`으로 리포트만 하는 읽기 스크립트로 쓴다.

## When to invoke

- "정본에 반영 안 된 화면 찾아줘", "운영 페이지 최신화해줘", "교체 안 된 것 전수 검사"
- 릴리즈·개발 반영이 끝난 직후 정본을 맞출 때
- 작업 페이지가 오래 쌓여 무엇이 반영됐는지 아무도 모를 때
- 주기 점검 — 월 1회 정도 돌려 시차를 없애는 용도

## When NOT to invoke

- 시안 두 벌(AS-IS/TO-BE)의 변경점 표기·일감 문서 정리 → `/fig:diff`
- 네이밍·섹션 정리, placeholder 채움 → `/fig:prep`
- 규칙 위반 검증만 → `/fig:lint`
- 흐름 화살표 → `/fig:arrows`
- 프론트 레포 코드에 반영 → `/fig:code`
- 파일 구조 파악만 → `/fig:read`

## 규칙 원천 — 설정 파일 (fig:prep·fig:lint와 동일 출처)

규칙은 **`figma-conventions.yaml`** 이 정한다. `resolve-config.py --js <fileKey>` 로 읽는다.

읽어 쓰는 절 — `pages`(3축 판별·제외 섹션) · `sync`(대조쌍 패턴·diff 상한·버전 페이지) · `naming`.

**반영 방식은 두 갈래고, 구조 대조가 그걸 가른다.** 기본은 프레임 이동이되, 레이어 구성이 같고 값만 다르면 이동 대신 값만 고친다 — 노드 id 가 유지돼야 기획서·티켓 딥링크가 안 끊기기 때문이다. 3단계가 그 판정을 집행하고, 어느 쪽을 썼는지 근거와 함께 결과 보고에 적는다.

팀 가이드 문서가 따로 있으면 설정 `guide_source` 에 적는다. 매 실행 fetch 하지 않는다.

## Inputs

- `figma_url` (필수): 대상 파일 URL. 특정 페이지를 지정해도 되지만, 감사는 파일 단위가 기본이다
- `scope` (선택): 감사 범위를 특정 도메인·기간으로 좁힐 때

## Procedure

### 1단계 — 축 확정 (추측 금지, 파일별로 설정에 남긴다)

파일마다 관례가 갈린다. 버전 단위로 묶는 파일도, 기간 단위로 묶는 파일도, 구분선(`## 제목 ##` 형태의 빈 페이지)으로 진행 단계를 나누는 파일도 있다.

1. **설정 `files.<fileKey>.pages` 에 3축이 있으면 그대로 쓴다.** 있으면 2~5번을 건너뛴다
2. 없으면 `figma.root.children` 으로 **페이지 목록과 순서**를 읽는다. `get_metadata` 의 파일 단위 응답은 페이지 목록이 불완전해 쓰지 않는다
3. 세 축을 추정한다. 판별 방식이 두 가지라는 걸 잊지 않는다 — **이름으로 걸리는 축**(`match: name`)과 **구분선 아래 대역으로 걸리는 축**(`match: divider`)

   | 축 | 무엇 | 신호 |
   |---|---|---|
   | 정본 | 대조 기준이 되는 운영 페이지 | 운영 prefix, 구조가 엄격하게 정리돼 있음 |
   | 아카이브 | 반영이 끝나 정리된 작업분 | 버전·기간 prefix, 날짜·버전 섹션 계층 |
   | 대기열 | 개발은 끝났고 정본 반영이 안 된 것 | 구분선 그룹 라벨(완료·배포 등), 개별 작업 페이지 |

4. **구분선으로 나뉜 그룹을 반드시 훑는다.** 그룹 라벨이 "완료"에 해당하는 대역의 페이지가 곧 미반영 후보다. 이름 prefix 만 보고 아카이브 페이지만 대조하면 실제 미반영을 놓친다(실측). 대기열이 이름으로 안 잡히는 게 흔한 이유다
5. 추정 결과를 **한 번 확인받는다** — 정본 N개 / 아카이브 M개 / 대기열 K개를 나열하고 맞는지
6. 확인된 관례를 **설정 `files.<fileKey>` 에 적어 둔다**(label 과 3축). 다음 실행은 1번에서 바로 시작한다. 페이지 목록이 관례와 안 맞으면 다시 확인한다

### 2단계 — 감사 (쓰기 0, 3신호 판정)

아카이브·대기열의 각 작업 건이 정본에 들어갔는지 대조한다.

**프레임 이름으로는 안 잡힌다.** 작업분과 정본의 프레임 이름은 같게 유지되는 게 정상이라(같은 화면이므로), 이름 대조는 항상 "일치"로 나온다. 내용을 봐야 한다.

**신호 1 — 텍스트 diff (주력)**

작업 건 안에 대조쌍 섹션이 있으면(이름 패턴은 설정 `sync.pair_patterns`) 양쪽 텍스트 집합을 뽑아 차집합을 구한다. 그것이 그 건의 변경 키워드다. 대조쌍이 없으면(신규 화면·단일안) 그 섹션 텍스트 전체를 후보로 본다.

- 개선안에만 있는 문자열 → 정본에 **있어야** 반영
- 현행안에만 있는 문자열 → 정본에 **없어야** 반영 (워딩 변경·항목 삭제가 여기 걸린다)

**신호 2 — 프레임 높이**

요소가 추가·삭제된 변경은 높이가 바뀐다. 개선안 높이와 정본 높이가 같고 현행안과 다르면 반영 정황, 반대면 미반영 정황. 단독으로는 판정하지 않고 신호 1의 보조로 쓴다.

**신호 3 — 컴포넌트 마스터**

컴포넌트 단위 변경(상태 추가·위계 정돈)은 프레임 텍스트에 안 드러난다. 정본 프레임 인스턴스의 `getMainComponentAsync()`로 마스터 id를 얻고, 작업분 쪽 인스턴스의 마스터 id와 비교한다. **같은 마스터를 참조하면 이미 통합된 것** — 마스터가 정본 페이지에 있으면 작업분 수정이 곧 정본 반영이다.

**결과는 3분류로만 낸다**

| 분류 | 기준 |
|---|---|
| 반영 | 신호 중 하나 이상이 명확히 반영을 지지하고 반대 신호 없음 |
| 미반영 | 개선안 키워드가 정본에 없거나, 현행안 키워드가 정본에 남아 있음 |
| 확인 필요 | 세 신호가 모두 무증상 — 대조쌍 텍스트가 동일하고 높이도 같은 순수 시각 변경 |

**확인 필요 건은 판정하지 않는다.** 모아서 보고하고 스크린샷 대조를 돌릴지 묻는다 — 건수만큼 비용이 드니 자동으로 하지 않는다. 대조쌍의 현행안이 작업 후에 덧씌워져 개선안과 같아진 경우도 여기 들어오는데, 그 건은 대조 자료로 못 쓴다는 사실을 함께 적는다.

### 3단계 — 반영 (구조 대조로 방식 분기)

미반영 건만 대상. 건별로 **먼저 구조를 대조**한다.

정본 프레임과 개선안 프레임의 텍스트 노드를 문서 순서대로 `부모이름|문자` 형태로 나열해 비교한다.

- **순서·개수·부모 이름이 모두 일치** → 다른 것은 값뿐이다. **값만 수정한다.** 노드 id가 유지돼 외부 딥링크가 안 끊긴다. 수정 대상 개수를 미리 세어 기대값과 다르면 중단하는 방어를 스크립트에 넣는다
- **하나라도 어긋남** → 구조가 바뀐 변경이다. **가이드대로 프레임을 이동**하고, 정본의 옛 프레임 id를 가리키던 외부 링크가 끊긴다는 사실을 리포트에 적는다(→ 딥링크 감사)

값 수정은 텍스트 편집이므로 대상 노드의 **현재 폰트를 `getStyledTextSegments(['fontName'])`로 읽어 로드**한 뒤 바꾼다. 기본 폰트를 가정하지 않는다.

**미리보기 → go.** 대상 프레임, 바꿀 항목과 개수, 방식(값 수정/이동)과 그 근거를 적는다. 건이 여러 개면 쪼개서 건별로 게이트를 통과한다.

반영 직후 같은 대조를 다시 돌려 결과가 개선안과 일치하는지 확인한다.

### 4단계 — 이관

정본 반영이 끝난 작업 페이지를 아카이브로 옮긴다.

1. **어느 아카이브 페이지·어느 기간(버전) 섹션에 넣을지 확인받는다.** 페이지 id 대역으로 작업 시점을 추정할 수 있지만 실제 개발 완료 시점은 파일에 없다 — 추측하지 말고 묻는다
2. 아카이브의 **기존 작업 섹션에서 여백·간격·배경 스타일을 읽어** 새 작업 섹션에 그대로 적용한다. 스타일을 새로 정하지 않는다
3. 프레임을 새 섹션으로 이동하고 기존 관례 위치에 배치
4. 비워진 작업 페이지는 **자식이 0개임을 확인한 뒤** 삭제한다. 페이지 삭제는 되돌릴 수 없으므로 **다른 확인과 합치지 않고 독립 게이트**로 묻는다
5. 아카이브 페이지가 오래 쌓였으면 보관 대역으로 옮길 후보만 알린다 — 이 스킬은 아카이브 개명·이동을 직접 하지 않는다

**섹션을 늘릴 때는 4변 교차를 실제 좌표로 계산한다.** 페이지 안 섹션이 세로로 정렬돼 있지 않아 "아래 섹션"을 눈대중으로 고르면 틀린다. 세로 구간만 겹치고 가로는 안 겹치는 경우도 있어 네 변을 모두 봐야 한다.

### 5단계 — 검증

- `/fig:lint` 를 호출해 프레임 소속·경계·섹션 겹침을 통과 확인한다. clone·move 가 끼면 필수
- 이동한 프레임의 텍스트 노드 수가 이동 전과 같은지 확인한다
- 정본에 두지만 검사 대상은 아닌 참고 자료(사이즈 변형 등)는 설정 `pages.exclude_sections` 에 걸리는 섹션에 넣는다. 일반 섹션에 두면 상태 변형 누락·흐름 orphan 으로 오탐된다

## 결과 보고

```
감사 N건  →  반영 X · 미반영 Y · 확인 필요 Z

[미반영 — 처리]
· 건명 (담당)
  이전: 정본이 어떤 상태였는지
  반영: 무엇을 어떻게 바꿨는지 / 방식(값 수정·이동)과 근거

[확인 필요]
· 건명 — 어느 신호가 무증상인지, 스크린샷 대조 필요 여부

[이관]
· 작업 페이지 → 아카이브 위치, 삭제 여부
```

미반영이 0건이면 그것만 짧게 보고한다.

## 구현 스니펫

**대조쌍 텍스트 diff (아카이브 한 페이지 통째)**

```js
const page = await figma.getNodeByIdAsync(PAGE_ID);
await figma.setCurrentPageAsync(page);
const texts = n => [...new Set(n.findAll(x => x.type === 'TEXT').map(t => t.characters.trim()).filter(s => s && s.length < CFG.sync.text_diff_max_len))];
const sub = (sec, re) => sec.children.filter(c => c.type === 'SECTION' && re.test(c.name));
const out = [];
for (const grp of page.children.filter(c => c.type === 'SECTION')) {
  for (const task of grp.children.filter(c => c.type === 'SECTION')) {
    const tb = sub(task, new RegExp(CFG.sync.pair_patterns.to_be, 'i')), ai = sub(task, new RegExp(CFG.sync.pair_patterns.as_is, 'i'));
    if (tb.length && ai.length) {
      const T = new Set(tb.flatMap(texts)), A = new Set(ai.flatMap(texts));
      out.push({ grp: grp.name, task: task.name, mode: 'diff',
        onlyToBe: [...T].filter(x => !A.has(x)), onlyAsIs: [...A].filter(x => !T.has(x)) });
    } else {
      out.push({ grp: grp.name, task: task.name, mode: 'flat', all: texts(task).slice(0, 70) });
    }
  }
}
return out;
```

**키워드를 정본 프레임에서 찾기**

```js
const KW = [/* 위 diff에서 뽑은 문자열 */];
function tf(n, acc) {   // 섹션 계층을 뚫고 화면 프레임만 모은다
  for (const c of n.children || []) {
    if (c.type === 'SECTION') tf(c, acc);
    else if (['FRAME','COMPONENT','INSTANCE'].includes(c.type) && !c.name.startsWith('[label]')) acc.push(c);
  }
  return acc;
}
const res = {};
for (const kw of KW) res[kw] = [];
for (const f of tf(figma.currentPage, [])) {
  const txt = f.findAll(x => x.type === 'TEXT').map(t => t.characters).join('');
  for (const kw of KW) if (txt.includes(kw)) res[kw].push(f.name);
}
return res;   // 빈 배열 = 그 키워드가 정본에 없음
```

**구조 대조 (값 수정이 가능한지 판정)**

```js
// 양쪽 페이지에서 각각 실행해 결과를 비교한다 (setCurrentPageAsync는 스크립트당 1회)
const f = await figma.getNodeByIdAsync(FRAME_ID);
return f.findAll(x => x.type === 'TEXT').map(t => `${t.parent.name}|${t.characters.replace(/\n/g,' ')}`);
// 두 배열의 길이·순서·부모 이름이 전부 같으면 값만 다르다 → 값 수정 가능
```

**값 수정 (방어 + 폰트 로드)**

```js
const edits = [/* [textNode, newValue] 쌍 */];
if (edits.length !== EXPECTED) throw new Error(`aborted: expected ${EXPECTED}, got ${edits.length}`);
const fonts = new Set();
for (const [t] of edits) for (const s of t.getStyledTextSegments(['fontName'])) fonts.add(JSON.stringify(s.fontName));
for (const fs of fonts) await figma.loadFontAsync(JSON.parse(fs));
for (const [t, v] of edits) t.characters = v;
return { mutatedNodeIds: edits.map(([t]) => t.id) };
```

**섹션 확장 전 4변 교차 검사**

```js
const t = target.absoluteBoundingBox;
const T = { x: t.x, y: t.y, r: t.x + t.width, b: t.y + t.height };   // 확장 후 값으로 계산
return figma.currentPage.children.filter(c => c.type === 'SECTION' && c.id !== target.id)
  .map(s => { const b = s.absoluteBoundingBox;
    return { name: s.name, hit: b.x < T.r && b.x + b.width > T.x && b.y < T.b && b.y + b.height > T.y }; })
  .filter(s => s.hit);   // 비어야 안전
```

## 함정

| 함정 | 대응 |
|---|---|
| 프레임 이름이 양쪽 같아 이름 대조가 항상 "일치" | 내용 3신호로 판정. 이름은 페어링에만 쓴다 |
| 아카이브 페이지만 대조하고 끝냄 | 구분선 그룹의 완료 대역이 실제 미반영 소굴 — `match: divider` 축을 반드시 포함 |
| 대조쌍의 현행안이 작업 후 덧씌워져 개선안과 동일 | 그 건은 대조 불가로 분류하고 정본 구조를 직접 확인 |
| 프레임 통째 교체로 외부 딥링크 끊김 | 구조가 같으면 값만 수정. 이동이 불가피하면 끊길 링크를 리포트 |
| 섹션 확장이 이웃 섹션 침범 | 확장 후 좌표로 4변 교차 계산. 세로만 보지 않는다 |
| 섹션 자식 좌표를 절대 좌표로 착각 | 섹션 자식의 x/y는 부모 섹션 기준 상대 좌표 |
| 폰트 로드 없이 텍스트 수정 | 노드의 현재 폰트를 읽어 로드. 기본 폰트를 가정하지 않는다 |
| 참고 자료를 정본 섹션에 배치 | lint 제외 섹션에 넣어 오탐 방지 |
| 빈 작업 페이지를 다른 확인과 묶어 삭제 | 페이지 삭제는 독립 게이트. 자식 0개 확인 후 실행 |

## Constraints

- 1·2단계는 **쓰기 0** — 감사 중에는 어떤 노드도 바꾸지 않는다
- 3·4단계의 모든 쓰기는 **미리보기 → go**. 건이 여러 개면 건별로 게이트를 통과한다
- **페이지 삭제는 독립 게이트** — 다른 확인과 합치지 않는다
- 설정에 없는 판단(값 수정이냐 이동이냐)은 쓸 때마다 근거를 결과 보고에 적는다
- 아카이브 페이지의 개명·이동은 하지 않는다 — 후보만 알린다
- 정본을 신규안에 없는 방향으로 "개선"하지 않는다. 반영은 신규안과 일치시키는 것까지다
