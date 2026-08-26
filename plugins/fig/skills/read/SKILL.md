---
name: read
description: Takes a Figma file URL, lists its pages, and collects every top-level frame on the page you pick. Metadata and screenshots are read in parallel and laid out as a markdown tree. Gives you the whole structure from a URL alone, without selecting frames one by one in the desktop app. Triggers - "/fig:read", "read this Figma file", "list every frame", "피그마 파일 읽어줘", "프레임 전부 뽑아줘", "전체 구조 보여줘".
allowed-tools: AskUserQuestion, Bash, mcp__plugin_figma_figma__get_metadata, mcp__plugin_figma_figma__get_screenshot
---

# fig:read — Figma 파일 전체 프레임 자동 수집

Figma 파일 URL 하나만 받아서 페이지 → 프레임 구조를 자동 탐색하고, 사용자가 고른 페이지의 모든 최상위 프레임을 메타데이터+스크린샷으로 수집한다. 데스크톱 앱에서 프레임을 선택하지 않아도 동작한다.

## When to invoke

- 사용자가 Figma **파일** URL(노드 지정 없음)을 주며 "전부 읽어줘", "구조 보여줘", "프레임 다 뽑아줘"
- PRD·정본 작업 전 화면 인벤토리 파악 단계
- "/fig:read" 명시적 호출

## When NOT to invoke

- 프레임 네이밍·섹션 정리 → `/fig:prep`
- 규칙 위반 검증 → `/fig:lint`
- 작업분이 정본에 반영됐는지 감사 → `/fig:sync`
- 코드 구현용 디자인 컨텍스트 → `figma:figma-design-to-code` skill · 프론트 레포 반영 → `/fig:code`

## Inputs

- `figma_url` (필수): figma.com/design/:fileKey/... 형태의 URL
  - node-id 파라미터가 있어도 무시하고 전체 파일로 다룬다 (사용자가 페이지 선택)

## Procedure

### 1. URL 파싱

Figma URL에서 fileKey 추출:
- 패턴: `figma.com/design/([A-Za-z0-9]+)/...`
- fileKey가 추출되지 않으면 사용자에게 정확한 URL 재요청

### 1.5 토큰 사전 검증

REST API 경로를 쓰기 전에 가벼운 ping 으로 토큰 상태를 확인한다. 환경변수 이름은 설정 `tools.figma_token_env` 가 정한다(기본 `FIGMA_TOKEN`).

```bash
source ~/.zshrc 2>/dev/null
VAR=$(python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/resolve-config.py \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["tools"]["figma_token_env"])')
TOKEN="${!VAR}"
if [ -z "$TOKEN" ]; then
  echo "STATE=NO_TOKEN ($VAR 미설정)"
else
  CODE=$(curl -sS -o /dev/null -w '%{http_code}' \
    -H "X-Figma-Token: $TOKEN" "https://api.figma.com/v1/me")
  echo "STATE=HTTP_$CODE"
fi
```

상태별 분기:

| STATE | 의미 | 처리 |
|---|---|---|
| `NO_TOKEN` | 토큰 환경변수 미설정 | "토큰 미설정" 안내 + Notes의 PAT 발급 가이드 링크 + plugin:figma fallback |
| `HTTP_200` | 정상 | Step 2의 REST 경로 진행 |
| `HTTP_401` | 토큰 만료/무효 | **"FIGMA_TOKEN이 만료되었거나 유효하지 않습니다. 재발급이 필요합니다."** + 발급 가이드 + fallback |
| `HTTP_403` | 권한 부족 | "토큰 권한이 부족합니다. file_content:read scope로 재발급하세요" + fallback |
| `HTTP_429` | rate limit | "잠시 후 다시 시도하세요" + fallback |
| 그 외 | 알 수 없는 오류 | HTTP 코드 그대로 노출 + fallback |

**중요**: 401 은 "토큰 없음"·"만료"·"무효" 가 같이 나오는 상태 코드다. 위에서 환경변수 존재 여부를 먼저 보기 때문에, 401 이 나왔다는 건 값은 있는데 거부됐다는 뜻 — 만료·무효로 안내한다.

### 2. 페이지 목록 조회

**우선순위 1: Figma REST API (1.5에서 HTTP_200 통과 시)**

```bash
curl -sS -w "\nHTTP_CODE=%{http_code}" \
  -H "X-Figma-Token: $FIGMA_TOKEN" \
  "https://api.figma.com/v1/files/{fileKey}?depth=1"
```

- depth=1로 페이지 노드만 받음 (전체 트리 다운로드 회피)
- 응답 본문에서 `.document.children[]` → `{nodeId}|{pageName}` 추출
- HTTP_CODE도 같이 받아 파일별 권한 이슈 가드:
  - `200` → 진행
  - `403` → "이 파일에 접근 권한이 없습니다 (다른 팀/비공개 파일일 수 있음)" + fallback
  - `404` → "파일을 찾을 수 없습니다. URL을 확인하세요"
  - 그 외 → 에러 노출 + fallback
- 토큰을 응답이나 로그에 출력 금지 — 헤더에만 사용

**우선순위 2: plugin:figma MCP fallback (토큰 없음/오류 시)**

`mcp__plugin_figma_figma__get_metadata`를 fileKey만 전달해 호출.
- 한계: 데스크톱 앱의 현재 열린 파일/뷰포트에 의존해 일부 페이지만 반환할 수 있음
- 사용자 URL의 node-id가 페이지(canvas 타입)면 그 페이지도 직접 진입 후보로 포함

**페이지 0개**: 토큰 미설정 + plugin도 빈 응답이면, 출력 마지막의 "PAT 발급 가이드" 안내하고 종료.

페이지가 1개뿐이면 선택 단계 생략하고 바로 3-2로 진행.

### 3. 페이지 선택 (페이지 ≥ 2개일 때)

`AskUserQuestion`으로 페이지 목록 제시:
- `multiSelect: true`
- 각 페이지 이름을 option label로 (최대 4개까지만 표시 가능 — 페이지가 5개 이상이면 처음 3개 + "전체" + "직접 선택" 식으로 구성)
- 페이지가 너무 많으면(8개 초과) 마크다운으로 번호 매겨 출력 후 사용자가 직접 번호 입력하게 안내

### 3-2. 프레임 트리 조회

선택된 페이지마다 `get_metadata` 호출:
- `fileKey` + 페이지 `nodeId`
- depth 2 정도로 충분 (페이지 직속 자식 = 최상위 프레임)

각 페이지의 최상위 프레임 ID 목록 수집.

### 4. 프레임 수 가드

전체 프레임 수가 설정 `tools.frame_count_guard` 를 넘으면 진행 전 경고한다:
- 마크다운으로 "{N}개 프레임 발견. 스크린샷까지 받으면 시간/컨텍스트 부담이 큼. 계속할까요?" 출력
- `AskUserQuestion`으로 "전부 진행 / 메타데이터만(스크린샷 생략) / 페이지 다시 선택" 분기

### 5. 프레임별 수집 (병렬)

각 프레임에 대해 다음 두 호출을 한 메시지 안에 병렬로:
- `mcp__plugin_figma_figma__get_metadata` (fileKey + nodeId)
- `mcp__plugin_figma_figma__get_screenshot` (fileKey + nodeId)

한 번에 너무 많이 띄우면 무거우므로 **5개씩 배치**로 나눠 호출.

스크린샷 호출이 실패해도 메타데이터는 살리고, 실패 사실은 출력에서 명시(`스크린샷: 실패`).

### 6. 마크다운 트리 출력

다음 형식으로 대화창에 출력:

```
# {파일명}

## {페이지명 1}

### {프레임명} (`{nodeId}`)
- 링크: https://figma.com/design/{fileKey}/?node-id={nodeId(:→-)}
- 크기: {width}×{height}
- 자식 수: {childCount}
- 스크린샷: {경로 또는 "실패"}

### {프레임명 2} ...

## {페이지명 2} ...
```

스크린샷은 `get_screenshot`이 반환한 이미지를 그대로 표시(어시스턴트 응답에 포함).

### 7. 다음 액션 안내

출력 마지막에 한 줄로:
> 다음 단계 후보: `/fig:prep`(구조 정리) · `/fig:lint`(검증) · `/fig:sync`(정본 반영 감사)

## Output Contract

- 모든 출력은 마크다운, 대화창에만 (파일/Notion 생성 없음)
- 노드 링크는 클릭 가능한 figma.com URL 형식 — nodeId의 `:`를 `-`로 변환
- 실패한 항목은 누락이 아니라 명시적으로 "실패" 표기

## Constraints

- 파일/Notion/Slack 등 외부 쓰기 금지 — 순수 읽기 스킬
- 페이지 선택 외에는 인터뷰 최소화 (사용자 부담 최소화)
- 한 번 수집한 결과는 컨텍스트에 남으므로 후속 스킬이 이어받기 좋게 구조화

## Notes

- plugin:figma MCP의 `get_metadata`/`get_screenshot`은 fileKey+nodeId만 있으면 호출 가능 — 데스크톱 앱 선택 상태 무관
- 단, plugin MCP `get_metadata(fileKey only)`는 데스크톱 앱 컨텍스트에 묶여 일부 페이지만 노출됨 → 전체 페이지 enumerate는 Figma REST API가 필수
- 컴포넌트/인스턴스/벡터까지 펴는 건 의도적으로 안 함. 최상위 프레임에서 멈춤
- 디자인이 자주 바뀌면 결과 캐싱 의미 없음 — 매번 다시 호출

### Figma Personal Access Token (PAT) 설정

REST API 경로를 쓰려면 PAT가 필요. 1회 설정:

1. Figma 웹 → 우상단 프로필 → Settings → **Security** 탭 → **Personal access tokens** → **Generate new token**
2. Scope 최소화: `File content` → **Read-only**만 체크 (다른 권한 불필요)
3. 토큰 복사 (한 번만 표시됨, `figd_` 로 시작)
4. `~/.zshrc` 끝에 추가 (이름은 설정 `tools.figma_token_env` 와 맞춘다):

   ```bash
   export FIGMA_TOKEN="figd_여기에_붙여넣기"
   ```

5. 새 터미널 열기 또는 `source ~/.zshrc` 실행

토큰 보안:
- 절대 응답·로그·커밋에 노출 금지
- jq로 파싱할 때도 헤더로만 전달, 응답 본문에만 의존
- 만료 의심되면 Figma Security 탭에서 토큰 revoke 후 재발급

토큰 만료 감지 한계:
- Figma PAT 는 토큰 자체에 만료일이 인코딩되지 않아 사전 조회가 안 된다
- API 호출의 HTTP 응답 코드로만 사후 감지 가능
- `401` 응답은 "토큰 없음·만료·무효"가 모두 같이 나오는 상태이므로, 스킬은 환경변수 존재 여부를 먼저 체크해 케이스를 분리함
