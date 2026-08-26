# fig

이미 그려진 Figma 파일을 정리·검증·동기화하는 스킬 묶음. 화면을 만드는 쪽이 아니라, 여러 사람이 함께 쓰는 파일을 관리하는 쪽입니다.

```bash
claude plugin marketplace add byjunyoung/claude-figma-skills
claude plugin install fig@byjunyoung
```

| 명령 | 무엇을 |
|---|---|
| `/fig:setup` | 파일 관례를 관측해 설정 초안 생성 |
| `/fig:read` | 페이지·화면 목록 수집 |
| `/fig:prep` | 이름 통일 · 섹션 배치 · 누락 화면 placeholder |
| `/fig:arrows` | 흐름 화살표 생성과 재동기화 |
| `/fig:lint` | 읽기 전용 검증 게이트 (쓰기 0) |
| `/fig:tokens` | 색상의 디자인시스템 토큰 바인딩 검수 |
| `/fig:sync` | 정본 반영 전수 감사 → 반영 → 이관 |
| `/fig:diff` | 변경점 주석 표기 · 일감 문서 정리 |
| `/fig:proto` | 동작하는 단일 HTML 프로토타입 |
| `/fig:code` | 프론트엔드 레포 코드 반영 |
| `/fig:qa` | 올라온 화면을 기획 기준과 대조해 결함 리포트 |
| `/fig:deck-setup` | 팀 발표 템플릿을 실측해 덱 자산 생성 |
| `/fig:deck` | 소스를 발표 덱(Figma Slides)으로 |

설정은 `figma-conventions.yaml` 하나가 정합니다. 내장 기본값 → `~/.claude/figma-conventions.yaml` → `./figma-conventions.yaml` 순으로 겹쳐 읽으니 **필요한 키만 적으면 됩니다.**

처음 여는 파일에서는 `/fig:setup`을 먼저 돌려 관례를 관측하게 하세요. 전체 설명은 [저장소 README](https://github.com/byjunyoung/claude-figma-skills)에 있습니다.
