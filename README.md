# claude-figma-skills

Claude Code 에서 **이미 그려진 Figma 파일을 운영하는** 스킬 묶음.
화면을 만드는 쪽이 아니라, 여러 사람이 쓰는 파일이 망가지지 않게 정리·검증·동기화하는 쪽이다.

공식 Figma 플러그인(`figma-use`·`figma-generate-design` 등)이 **생성**을 맡는다면 이쪽은 **운영**을 맡는다.
둘은 경쟁이 아니라 보완이고, 이 스킬들은 공식 플러그인 위에서 돈다.

## 스킬

| 스킬 | 하는 일 |
|---|---|
| `figma-setup` | 낯선 파일을 훑어 관례를 역추출하고 설정 초안을 만든다. **처음 켤 때 이것부터** |
| `figma-read` | 파일 URL 하나로 페이지→프레임 구조를 수집 |
| `figma-prep` | 네이밍 통일·기능 단위 섹션화·배치, 누락 케이스를 placeholder 로 |
| `figma-arrows` | 화면 흐름 화살표·라벨 생성과 재동기화. 이름에 흐름을 저장해 재배치 후에도 sync |
| `figma-lint` | **읽기 전용 검증 게이트.** 구조·흐름·컴포넌트 기본값 잔재를 한 번에 |
| `figma-tokens` | 색이 디자인시스템 토큰에 바인딩됐는지 검수·정비 |
| `figma-sync` | 작업분이 정본에 반영됐는지 전수 감사 → 반영 → 아카이브 이관 |
| `figma-diff` | AS-IS/TO-BE 변경점을 Dev Mode annotation 으로 표기하고 일감 문서에 정리 |
| `figma-proto` | 시안을 코드로 재현해 실제 동작하는 단일 HTML 프로토타입 |
| `figma-code` | 시안을 프론트 레포 코드에 반영 |

쓰는 스킬(`prep`·`arrows`·`sync`)은 **감사 코드를 갖고 있지 않다.** 판정은 전부 `figma-lint` 하나가 하고,
나머지는 검출된 위반을 고치는 쪽만 맡는다. 검증이 스킬마다 흩어지면
"지금은 그 스킬이 아니라서 감사를 안 돌렸다"는 사각이 생긴다.

## 설치

```bash
git clone https://github.com/byjunyoung/claude-figma-skills /tmp/cfs && /tmp/cfs/install.sh
```

전제를 확인하고, 스킬 10개와 공용 층을 `~/.claude/skills/` 에 깔고, 설정 씨앗을 놓은 뒤
정합성 검사까지 돌립니다. 이미 있는 스킬은 덮어쓰기 전에 묻습니다.

전제 — Claude Code, Figma MCP 플러그인(`plugin:figma`) 연결, `python3` + PyYAML, `node`.

설치 위치를 바꾸려면 `CLAUDE_SKILLS_DIR=... ./install.sh`.

## 설정

규칙은 스킬 문서가 아니라 **`figma-conventions.yaml`** 하나가 정한다.
네이밍 패턴·상태 목록·간격 토큰·섹션 스타일·화살표 스타일·제외 섹션·허용오차가 전부 여기 있다.

탐색 순서는 `./figma-conventions.yaml` → `~/.claude/figma-conventions.yaml` → 내장 기본값
(`_figma-common/conventions.example.yaml`). 마지막으로 떨어지면 결과에 "기본값으로 진행"이 찍힌다.

낯선 파일에서는 `/figma-setup` 을 먼저 돌린다. 캔버스에서 관례를 관측해 초안을 만들고,
표본이 얇거나 갈리는 항목은 **추정하지 않고 `null` 로 남긴다.** `null` 은 그 검사를 건너뛴다는 뜻이다 —
규약을 모르는 것과 규약을 어긴 것은 다르고, 둘을 섞으면 리포트가 오탐에 묻힌다.

파일마다 갈리는 항목(정본/아카이브/대기열 3축 등)은 공통 절이 아니라 `files.<fileKey>` 에 적는다.

## 구조

```
_figma-common/
  conventions.example.yaml   스키마 + 내장 기본값. 주석이 곧 가이드
  verify.py                  정합성 검사 (스킬 고친 뒤 실행)
  scripts/
    audit-struct.js          소속·경계·겹침·네이밍
    audit-flow.js            화살표 수치·진입방향·관통·라벨·[state]·커버리지
    audit-component.js       컴포넌트 기본값 잔재
    arrow-build.js           화살표 생성 프리앰블
    prep-ops.js              페이지 정리 프리앰블
    probe-page.js            관례 역추출 관측
    lib/
      resolve-config.py      설정 탐색·병합 → `const CFG = {...};`
      draft-conventions.py   관측치 집계 → 설정 초안
      check.sh               스크립트 문법 게이트
figma-*/SKILL.md
```

Figma 플러그인 샌드박스에는 파일시스템이 없다. 그래서 설정 해석은 호스트에서 하고,
`resolve-config.py --js <fileKey>` 가 낸 한 줄을 스크립트 앞에 붙여 `use_figma` 에 넣는다.

## 고치고 나서

```bash
python3 _figma-common/verify.py
```

설정 파싱 · 팀 설정 키가 스키마 안에 있는가 · 스크립트 문법 · frontmatter 의 name 이 디렉터리와 맞는가 ·
SKILL.md 가 참조하는 설정 키가 실재하는가 · 가리키는 스킬이 실재하는가 · 고유값이 남았는가를 본다.

## 알아둘 함정 셋

**문법 검사** — `use_figma` 는 스크립트를 async 함수로 감싸 실행해서 top-level `await` 와 `return` 이 둘 다 된다.
`node --check` 는 CommonJS 로 보면 `await` 를, ESM 으로 보면 `return` 을 거부한다.
`check.sh` 가 같은 방식으로 감싼 뒤 검사하는 이유다.

**제외 섹션** — 세 갈래로 다르게 취급한다. 감사 대상에서 빼고, 커버리지에서도 빼되, **관통 대상에는 남긴다.**
선이 실제로 그 위를 지나면 제외 섹션이든 아니든 깨진 선이다.

**네이밍 패턴** — 상태 접미사를 `[A-Za-z]` 로 제한하지 말 것. 상태 이름이 라틴 문자가 아닌 팀에서 전건이 오탐된다.
실측에서 그 패턴이 61건 중 38건(62%)을 위반으로 올렸고, 제한을 풀자 2건(3%)만 남았으며 그 둘은 진짜 위반이었다.

## 상태

한 회사의 Figma 전반에서 **UX 파트 세 명이 실사용** 중입니다. 여러 제품 파일에 걸쳐 돌아가고,
여기 담긴 규칙과 함정은 대부분 실제로 사고가 난 뒤에 추가된 것들입니다.

검증되지 않은 쪽은 **다른 조직의 관례**입니다. 네이밍 규약도, 페이지 역할 구분도, 상태 이름의
문자 체계도 팀마다 다릅니다. 실제로 상태 접미사를 라틴 문자로 제한한 정규식이 한글 접미사를
쓰는 파일에서 61건 중 38건을 오탐한 적이 있습니다 — 그런 종류의 가정이 아직 더 숨어 있을 겁니다.

`/figma-setup` 이 관례를 물어보지 않고 **관측해서** 채우도록 만든 이유가 그것이고, 표본이 얇으면
`null` 로 남기는 설계도 같은 이유입니다. 모르는 것을 아는 척하면 리포트가 오탐에 묻힙니다.

낯선 파일에서 오탐이 나오면 이슈로 알려주세요.

## 저작권

© 2026 Junyoung Kim. 별도 라이선스를 두지 않았습니다 — 읽고 참고하는 건 자유지만
복제·수정·재배포에는 허락이 필요합니다. 쓰고 싶으시면 이슈로 물어봐 주세요.
