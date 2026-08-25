---
name: figma-diff
description: AS-IS / TO-BE 시안을 비교해 변경된 요소를 Figma 네이티브 Dev Mode annotation으로 표기하고, 연결된 일감 문서에 Figma 링크 + AS-IS/TO-BE 비교표 + 범위 콜아웃을 정리한다. 일감 트래커는 figma-conventions.yaml 의 task_tracker 절이 정하며 notion·github·none 을 지원하고, none 이면 Figma 표기까지만 하고 비교표는 마크다운으로 낸다. AS-IS는 같은 페이지의 다른 섹션일 수도, 다른 페이지·현행 디자인일 수도 있어 소스 확정을 먼저 한다. 카테고리는 새로 만들지 않고 공용 카테고리 재사용 또는 무카테고리, 분류는 라벨 태그로. 대표 화면만 표기하고 상태 변형은 상속. Triggers - "/figma-diff", "as-is to-be 비교", "변경점 표시해줘", "바뀐 요소 annotation 달아줘", "뭐가 변경됐는지 표시하고 노션 정리", "as is to be 어노테이션".
allowed-tools: AskUserQuestion, Bash, mcp__plugin_figma_figma__use_figma, mcp__plugin_figma_figma__get_metadata, mcp__plugin_figma_figma__get_screenshot, mcp__claude_ai_Notion__notion-fetch, mcp__claude_ai_Notion__notion-update-page, mcp__claude_ai_Notion__notion-search, mcp__plugin_github_github__issue_read, mcp__plugin_github_github__issue_write, mcp__plugin_github_github__add_issue_comment
---

# figma-diff — AS-IS / TO-BE 변경점 표기 + 일감 문서 정리

AS-IS / TO-BE 시안을 비교해 **바뀐 요소를 찾아 Figma 네이티브 Dev Mode annotation 으로 핀을 박고**, 같은 내용을 **연결된 일감 문서**에 비교표로 정리한다. 어디에 정리하느냐는 설정 `task_tracker` 가 정한다.

**핵심 원칙**
- 변경점의 **단일 출처는 라벨 텍스트**. 카테고리 색은 보조일 뿐(유실될 수 있음).
- **카테고리를 새로 만들지 않는다.** 공용 카테고리 재사용 또는 무카테고리.
- **대표 화면만** 표기. 상태 변형(Default/Selected, Detail/Toast 등)은 대표 하나로 묶고 "상속" 문구로 처리.
- 모든 쓰기(Figma·Notion)는 **미리보기 → "go"** 게이트.
- AS-IS 위치를 **추측하지 않는다** — 같은 페이지에 없으면 검색하거나 묻는다.

## When to invoke

- AS-IS/TO-BE 시안이 있고 "바뀐 거 표시해줘 / 비교해서 annotation 달아줘"
- 변경점을 일감 문서에도 정리해야 할 때
- "/figma-diff" 명시적 호출

## When NOT to invoke

- 전체 프레임 구조만 파악 → `/figma-read`
- 구조·네이밍 정리, placeholder 채움 → `/figma-prep`
- 흐름 화살표 → `/figma-arrows`
- 규칙 위반 검증만 → `/figma-lint`
- 변경이 정본에 반영됐는지 감사·반영·이관 → `/figma-sync`

## Inputs

- `figma_url` (필수): TO-BE(또는 비교 대상) URL. 페이지·섹션·프레임 어느 것이든 가능 — 종류를 판별해 분기한다.
- `task_ref` (선택): 정리할 일감. 없으면 화면·기능명 키워드로 트래커에서 검색해 후보를 확인받는다. 그래도 없으면 트래커 단계를 건너뛴다(사용자 확인).
- `shared_category` (선택): 재사용할 공용 annotation 카테고리 이름. 생략하면 설정 `task_tracker.annotation_category`.

규칙 원천은 `figma-conventions.yaml` 이다 — `resolve-config.py --js <fileKey>` 로 `task_tracker`·`sync.pair_patterns` 를 읽는다.

`use_figma` 호출 전 항상 `figma:figma-use` 스킬을 로드한다.

## 카테고리 정책 (새로 만들지 않는다)

- annotation 카테고리를 **절대 새로 생성하지 않는다** (`addAnnotationCategoryAsync` 금지). 매 실행 생성하면 파일 카테고리 목록이 오염되고, 파일 sync 시 프리셋으로 유실·재매핑된다(실측).
- `getAnnotationCategoriesAsync()` 로 설정 `task_tracker.annotation_category` 이름을 찾는다 → 있으면 그 `categoryId` 사용, 없으면 `categoryId` 생략(무카테고리).
- **분류는 카테고리 색이 아니라 라벨 앞 `[태그]` 로 표현한다.** 태그 목록은 설정 `task_tracker.scope_tags`. 색은 유실될 수 있어 분류의 단일 출처는 라벨 텍스트다.

## Procedure

### 1. AS-IS / TO-BE 소스 확정 (추측 금지)
입력 노드 종류를 판별한다(페이지 = 여러 프레임/섹션 담긴 canvas / 섹션 / 단일 프레임).

TO-BE를 먼저 잡고, **AS-IS를 다음 순서로 찾는다**:
1. **같은 페이지의 다른 섹션**: 섹션명을 설정 `sync.pair_patterns`(figma-sync 와 공용)로 매칭한다.
2. 같은 페이지에 없으면 **다른 페이지 검색**: `figma.root.children`에서 이름에 AS/현행/current/live/before가 있거나, **같은 화면명 프레임을 가진 페이지**를 후보로 제시.
3. 그래도 불명확하면 **사용자에게 질문**(AskUserQuestion): "AS-IS가 어디 있나 — ①같은 파일 다른 페이지 ②다른 파일 ③현행 라이브(비교본 없음)". 후보가 있으면 권장안으로 제시.
4. AS-IS가 **아예 없으면**(순수 신규 화면) 비교 불가 → 변경점 대신 "신규 화면"으로 처리할지 확인.

> 여러 페이지를 읽어야 하면 `setCurrentPageAsync`는 스크립트당 1회 — 페이지별로 `use_figma` 호출을 병렬로 나눈다(figma-use 규칙).

### 1-2. 비교 구조 정비 (AS-IS가 다른 곳에 있을 때)

AS-IS가 운영 페이지 등 **다른 페이지·파일에 있으면, 작업 페이지로 복제해 와 한 화면에서 대조되게 만든다.** 리뷰어·개발이 두 페이지를 오가야 하면 비교 자체가 안 된다.

- **섹션은 AS-IS / TO-BE 두 덩어리로 나눈다.** 기능·도메인별로 쪼개지 않는다 — 비교 페이지의 분류 축은 '변경 전/후' 하나다.
- 섹션 이름은 1번의 매칭 패턴에 걸리게 짓는다 (예: `NN. AS-IS` / `NN. TO-BE`).
- **프레임 이름은 양쪽 동일하게 둔다** — 이름이 페어링 키이고 구분자는 섹션이다. 프레임에 `[AS-IS]` 같은 prefix를 붙이면 페어링이 깨진다.
- 두 섹션은 **세로로 쌓고 화면별 x를 맞춘다** — 같은 화면이 위아래로 마주봐야 대조가 쉽다.
- TO-BE에만 있는 신규 화면·상태 변형은 TO-BE 섹션에만 둔다(AS-IS 자리는 비운다).
- AS-IS는 참고본이라 **수정하지 않는다.** 정본에서 복제만 하고 원본은 건드리지 않는다.
- 같은 이름 프레임이 두 섹션에 하나씩 있는 것은 정상 — 이름 중복은 **섹션 내부에서만** 위반으로 본다(`/figma-lint` 호출 시 이 점을 명시).

### 2. 프레임 페어링
- `get_metadata`(대상 스코프)를 부른다. 응답이 커서 파일로 저장되면 Bash python/jq로 `<section>`/`<frame>` 태그만 추출(스니펫 참조).
- AS-IS ↔ TO-BE 프레임을 **이름으로 페어링**(같은 화면명끼리). 하위 섹션이 있으면 한 단계 더 내려간다.
- **크기(width/height) 차이는 변경 후보 신호** — TO-BE가 더 크면 콘텐츠 추가 확률↑.

### 3. 화면별 diff
- 페어별 **프레임 단위** 고해상 `get_screenshot`을 **병렬**로 받아 curl→로컬 저장→육안 비교(큰 캔버스 전체는 해상도가 낮아 못 읽음).
- 바뀐 요소를 목록화: 신규 컬럼/필드/섹션, 값·단위·스타일 변경, 아이콘 추가 등.
- **상태 변형은 대표 1개로 묶는다**(Default/Selected, Detail/Toast → 대표에만 핀 + "변형은 동일 변경 상속" 문구). 형제 변형 중복 표기 금지.
- 더미 데이터 값 차이(합계 숫자만 다름 등)는 **설계 변경 아님 → 제외**.

### 4. 일감 범위 대조 → 분류
- 일감이 있으면 **범위 In/Out·주요 변경 요약**을 읽어 각 변경을 분류한다. 태그는 설정 `task_tracker.scope_tags` 순서대로 — 통상 「이 일감」 / 「범위 밖」 / 「별도 예정」 세 갈래다
- 설정에 태그가 없으면 분류 없이 변경 목록만 내고, 범위 판단이 필요하면 사용자에게 묻는다
- 범위 밖 변경은 임의 판단하지 말고 **"이 일감 포함 의도인지" 확인**을 남긴다.

### 5. 앵커 노드 확보 (읽기)
- `use_figma` **읽기 스크립트**로 각 변경 요소 노드를 텍스트 내용 `findOne`(정확·부분 일치)으로 잡고 `absoluteBoundingBox` 확인.
- 인스턴스 내부 sublayer도 `node.annotations` 부착 가능. 단 `get_metadata`의 `0:xxxx` 내부 id는 `getNodeByIdAsync`로 **직접 주소지정 불가** → 텍스트 매칭으로 확보.

### 6. 미리보기 → go (Figma)
- 변경표(요소 / AS-IS / TO-BE / 분류) + **각 핀 라벨 문구** + 어느 프레임에 박을지 + 쓸 카테고리(공용명 or 무)를 제시하고 "go" 대기.

### 7. Figma 쓰기 (annotation)
- `figma-use` 로드 후 `use_figma`로: currentPage 전환 → 공용 카테고리 조회 → 각 앵커 부착. **카테고리 조회+전 핀 부착을 한 스크립트로**(중간 유실 방지). 스니펫 참조.
- **라벨 앞 `[분류]` 태그 필수** — 색이 풀려도 분류가 텍스트로 남는다.
- **되읽기 검증**: `node.annotations` 재조회로 확인. 핀은 **Dev Mode에서만** 보여 `get_screenshot`으론 확인 안 됨.

### 8. 일감 문서 미리보기 → go → 쓰기

넣을 것은 트래커와 무관하게 셋이다. ①Figma 링크(`node-id` 포함) + "Dev Mode annotation 표기, 대표 화면·상태 변형 상속" 한 줄 ②**AS-IS/TO-BE 비교표** ③**범위 콜아웃**(모두 범위 내면 `✅`, 범위 밖이 있으면 `⚠️` + TBD).

어디에 어떻게 넣느냐만 설정 `task_tracker.type` 으로 갈린다.

| type | 대상 | 방식 |
|---|---|---|
| `notion` | 일감 페이지의 `ui_section_heading` 절 (보통 비어 있는 콜아웃 뒤) | `update_content` 로 헤딩·콜아웃을 `old_str` 로 잡아 **뒤에 삽입**. 전체 교체 금지 |
| `github` | 일감 이슈 | 본문에 해당 절이 있으면 그 아래 삽입, 없으면 코멘트로 추가 |
| `none` | — | 쓰지 않는다. 비교표·콜아웃을 **응답에 마크다운으로 출력**하고 끝낸다 |

- 일감을 못 찾았으면 이 단계를 건너뛴다(사용자 확인).
- 대상 절을 **탐색**한다. `ui_section_heading` 이 없거나 이름이 다르면 어디에 넣을지 확인받는다. 이미 내용이 있으면 덮지 말고 뒤에 이어 넣는다.

### 9. 검증
- `none` 이 아니면 되읽어 표·콜아웃·링크를 확인한다.
- **한글 인코딩 오타 주의**: 직접 입력 한글이 깨질 수 있다. 깨진 글자의 코드포인트를 확인해 `\u` 이스케이프로 치환(직접 재입력하면 또 깨짐). [[reference_notion_korean_input_typos]]

### 10. 범위 확정 후속 (해당 시)
- 범위 밖 변경이 이후 "포함·제외" 로 확정되면: Figma 라벨 `[태그]`·일감 비교표 분류·범위 In 항목·범위 콜아웃(⚠️↔✅)을 **함께 갱신**한다(각각 미리보기→go).

## 라벨 문구 규칙

- 형식: `**[분류] 무엇이 바뀌었나** — 어떻게/왜(값·형식·위치).`
- 개발이 산출물만 보고 알 수 있게 구체값 포함: 위치(어디 뒤/옆), 값 형식(예: 분:초), 예외(미완료 시 표기) 등.
- 분류 태그는 설정 `task_tracker.scope_tags` 에서 고른다 — 임의로 새 태그를 만들지 않는다.

## 구현 스니펫

**섹션·프레임 추출** (저장된 metadata 파일에서):

    # f = 저장된 get_metadata 결과 파일 경로
    python3 -c "
    import json,re
    t=json.load(open('$f'))[0]['text']
    for m in re.finditer(r'<(section|frame)\s+id=\"([^\"]+)\"\s+name=\"([^\"]+)\"\s+x=\"(-?[0-9.]+)\"\s+y=\"(-?[0-9.]+)\"\s+width=\"([0-9.]+)\"\s+height=\"([0-9.]+)\"', t):
        tag,i,n,x,y,w,h=m.groups()
        if tag=='section' or float(w)>=1400: print(f'{tag} {i} w={float(w):.0f} h={float(h):.0f}  {n}')
    "

**카테고리 조회 + 전 핀 부착 + 되읽기** (한 스크립트, 정책 반영):

    // targets = [{ id, md }] — md는 "[분류]"로 시작. SHARED='Changed'
    const page = await figma.getNodeByIdAsync(PAGE_ID);
    await figma.setCurrentPageAsync(page);
    const cats = await figma.annotations.getAnnotationCategoriesAsync();
    const shared = cats.find(c => c.label === SHARED);   // 없으면 undefined → 무카테고리
    const res = [];
    for (const t of targets) {
      const n = await figma.getNodeByIdAsync(t.id);
      if (!n) { res.push({ id: t.id, ok: false }); continue; }
      const ann = { labelMarkdown: t.md };
      if (shared) ann.categoryId = shared.id;            // 있을 때만 부여, 생성 금지
      n.annotations = [ann];
      res.push({ name: n.name, cat: shared ? shared.id : null, ok: true });
    }
    return res;   // 되읽기 검증은 별도 호출로 node.annotations 재조회

## 함정

- **카테고리 생성 금지**: 새 커스텀 카테고리는 파일 sync 시 사라지고 핀이 프리셋으로 재매핑, 일부 핀은 통째로 유실됨. → 공용 재사용/무 + 라벨 태그.
- **핀은 Dev Mode 전용**: 일반 스크린샷·편집 모드엔 안 보임. 검증은 `node.annotations` 되읽기.
- **AS-IS 위치 추측 금지**: 같은 페이지에 없으면 다른 페이지 검색 or 질문.
- **비교 페이지를 기능별 섹션으로 짜지 않기**: 축이 둘(기능×전후)이 되면 대조가 불가능해진다. AS-IS/TO-BE 두 섹션이 유일한 축(1-2절).
- **대표만 표기**: 형제 상태 변형에 중복 핀 금지. 대표 + "상속" 문구.
- **metadata 대용량**: 파일로 저장되면 python/jq 파싱. `0:xxxx` 내부 id는 주소지정 불가 → 텍스트 매칭.
- **한글 인코딩 오타**: 외부 문서에 직접 입력할 때 음절이 깨질 수 있다. 삽입 후 되읽어 검증하고, 깨진 글자는 `\u` 이스케이프로 치환한다.

## Constraints

- Figma·일감 문서 각 쓰기 전 **미리보기 → "go"**(Figma 는 단계 많으면 분할). annotation 카테고리 **생성 금지**. 대상 노드 외 부모/형제 미변경. 검증 전 "완료" 단정 금지.

## 완료 조건

- TO-BE 변경 요소마다(대표 프레임 기준) `[분류]` 태그 라벨 annotation이 부착·되읽기 확인됨.
- 일감 문서의 지정 절에 Figma 링크 + 비교표 + 범위 콜아웃 삽입·되읽기 확인(한글 오타 없음). `type: none` 이거나 일감이 없으면 마크다운 출력으로 대신하고 그 사실을 명시.
- 범위 밖 변경은 플래그로 남고, 확정 시 Figma·Notion 함께 갱신.
