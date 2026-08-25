# claude-figma-skills

Claude Code에서 Figma 파일을 정리·검증·동기화하는 스킬 모음. 화면을 새로 만드는 쪽이 아니라, 여러 사람이 함께 쓰는 파일을 관리하는 쪽입니다.

공식 Figma 플러그인(`figma-use`·`figma-generate-design`)이 **생성**을 맡는다면 이쪽은 **운영**을 맡습니다. 공식 플러그인 위에서 동작합니다.

---

## 스킬

| 스킬 | 기능 |
|---|---|
| `figma-setup` | 파일의 관례를 읽어 설정 초안 생성 — **처음 설치했다면 이것부터** |
| `figma-read` | 파일 URL만으로 페이지·프레임 구조 수집 |
| `figma-prep` | 프레임 네이밍 통일, 기능 단위 섹션화·배치, 누락 케이스를 placeholder로 |
| `figma-arrows` | 화면 흐름 화살표·라벨 생성 및 재동기화 |
| `figma-lint` | 읽기 전용 검증 게이트 — 구조·흐름·컴포넌트 기본값을 한 번에 검사 |
| `figma-tokens` | 색상의 디자인시스템 토큰 바인딩 검수·정비 |
| `figma-sync` | 작업분이 정본에 반영됐는지 전수 감사 → 반영 → 아카이브 이관 |
| `figma-diff` | AS-IS/TO-BE 변경점을 Dev Mode annotation으로 표기, 일감 문서에 정리 |
| `figma-proto` | 시안을 실제 동작하는 단일 HTML 프로토타입으로 |
| `figma-code` | 시안을 프론트엔드 레포 코드에 반영 |

쓰기 스킬(`prep`·`arrows`·`sync`)에는 검증 코드가 없습니다. 판정은 `figma-lint` 하나가 하고 나머지는 고치는 역할만 맡습니다.

## 설치

```bash
git clone https://github.com/byjunyoung/claude-figma-skills /tmp/cfs && /tmp/cfs/install.sh
```

전제를 확인하고 스킬 10개와 공용 층을 `~/.claude/skills/`에 설치한 뒤, 설정 씨앗 배치와 정합성 검사까지 진행합니다. 기존 스킬은 덮어쓰기 전에 확인합니다.

- **필요한 것** — Claude Code, Figma MCP 플러그인(`plugin:figma`), `python3` + PyYAML, `node`
- **설치 위치 변경** — `CLAUDE_SKILLS_DIR=... ./install.sh`

## 설정

규칙은 스킬 문서가 아니라 `figma-conventions.yaml` 하나가 정합니다. 네이밍 패턴·상태 목록·간격 토큰·섹션 스타일·화살표 스타일·제외 섹션·허용오차가 모두 여기 있습니다.

- **탐색 순서** — `./figma-conventions.yaml` → `~/.claude/figma-conventions.yaml` → 내장 기본값
- **첫 실행** — 대상 파일에서 `/figma-setup`을 돌리면 관례를 관측해 초안을 만듭니다
- **`null`의 의미** — 추정하지 않았다는 뜻이고, 해당 검사를 건너뜁니다
- **파일별 설정** — 정본·아카이브 페이지 구분처럼 파일마다 다른 항목은 `files.<fileKey>`에 적습니다

## 구조

```
_figma-common/
  conventions.example.yaml   설정 스키마 + 내장 기본값
  verify.py                  정합성 검사
  scripts/
    audit-struct.js          소속·경계·겹침·네이밍·순번
    audit-flow.js            화살표 수치·진입방향·관통·라벨·커버리지
    audit-component.js       컴포넌트 기본값 잔재
    arrow-build.js           화살표 생성 헬퍼
    prep-ops.js              페이지 정리 헬퍼
    probe-page.js            관례 관측
    lib/                     설정 해석·초안 생성·문법 검사
figma-*/SKILL.md
```

Figma 플러그인은 파일 시스템에 접근할 수 없습니다. 설정 해석은 로컬에서 처리하고, `resolve-config.py --js <fileKey>`가 출력한 한 줄을 스크립트 앞에 붙여 실행합니다.

스킬을 수정한 뒤에는 `python3 _figma-common/verify.py`로 정합성을 확인합니다.

## 기술 스택

Claude Code 스킬(Markdown) + Figma Plugin API(JavaScript) + 설정 해석·집계(Python). 외부 의존성은 PyYAML 하나입니다.

## 만든 사람

김준영 · [LinkedIn](https://www.linkedin.com/in/byjunyoung/)

© 2026 Junyoung Kim. 별도 라이선스를 두지 않았습니다.

## 피드백

버그 제보나 기능 제안은 [Issues](https://github.com/byjunyoung/claude-figma-skills/issues)에 남겨주세요.
