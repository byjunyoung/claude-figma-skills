# _figma-common — fig 플러그인 공용 층

`fig` 플러그인의 스킬 10개가 공유하는 **규칙 원천**과 **실행 코드**가 여기 있다.
스킬 문서(SKILL.md)에는 판단만 적고, 값과 코드는 이 폴더 하나로 모은다 —
두 벌이 되면 한쪽만 고쳐져 갈라지기 때문이다.

스킬에서 이 폴더를 가리킬 때는 **절대경로가 아니라 `${CLAUDE_PLUGIN_ROOT}`** 를 쓴다.
플러그인은 설치 위치가 환경마다 달라서, 홈 아래를 하드코딩하면 남의 기계에서 깨진다.

```
conventions.example.yaml   스키마 + 내장 기본값. 주석이 곧 가이드다
verify.py                  정합성 검사 (스킬 고친 뒤 이걸 돌린다)
scripts/
  audit-struct.js          소속·경계·프레임겹침·섹션겹침·네이밍
  audit-flow.js            화살표 수치·진입방향·관통·라벨 z·[state]·커버리지
  audit-component.js       컴포넌트 기본값 잔재 (MODE=collect / compare)
  arrow-build.js           화살표 생성 프리앰블
  prep-ops.js              페이지 정리 프리앰블
  probe-page.js            관례 역추출 관측 (/fig:setup 용)
  lib/
    resolve-config.py      설정 탐색·깊은병합·files 오버레이 → JSON 또는 `const CFG=`
    draft-conventions.py   관측치 집계 → conventions.yaml 초안
    check.sh               스크립트 문법 게이트
```

## 설정

탐색 순서는 `./figma-conventions.yaml` → `~/.claude/figma-conventions.yaml` → 이 폴더의 example.
마지막으로 떨어지면 결과 보고에 **"기본값으로 진행"을 명시**한다.

`null` 은 "모른다"는 뜻이고, 그 검사를 건너뛴다. **추정을 확정처럼 채우지 않는다** —
규약을 모르는 것과 규약을 어긴 것은 다르고, 둘을 섞으면 리포트가 오탐에 묻힌다.

파일마다 갈리는 항목(`pages` 3축 등)은 공통 절이 아니라 `files.<fileKey>` 에 적는다.

## 스크립트 실행

Figma 플러그인 샌드박스에는 파일시스템이 없다. 그래서 설정 해석은 호스트에서 하고,
결과를 스크립트 앞에 붙여 넣는다.

```bash
python3 scripts/lib/resolve-config.py --js <fileKey>   # → const CFG = {...};
```

`<그 한 줄>` + `<스크립트 전문>` + (필요하면 맨 앞에 `setCurrentPageAsync` 한 줄)
을 이어 붙여 `use_figma` 에 넣는다. 페이지 전환은 스크립트당 1회이므로,
멀티 페이지는 호출을 나눠 한 메시지에서 병렬로 띄운다.

## 고치고 나서

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_figma-common/verify.py
```

검사하는 것 — 설정 2벌 파싱 · 팀 설정 키가 스키마 안에 있는가 · 스크립트 문법 ·
frontmatter 의 name 이 디렉터리와 맞는가 · SKILL.md 가 참조하는 설정 키가 실재하는가 ·
가리키는 스킬이 실재하는가 · 팀 고유값이 남았는가.

고유값 검사는 **패턴을 하나씩 따로** 돌린다. 여럿을 `|` 로 이어 붙이면 이스케이프가 꼬여
조용히 0 을 낸다 — 실제로 그렇게 한 건을 놓쳤다.

## 두 가지 함정

**문법 게이트** — `use_figma` 는 스크립트를 async 함수로 감싸 실행해서 top-level 의
`await` 와 `return` 이 둘 다 된다. `node --check` 는 CommonJS 로 보면 `await` 를,
ESM 으로 보면 `return` 을 거부한다. `check.sh` 가 같은 방식으로 감싼 뒤 검사하는 이유다.

**제외 섹션** — 세 갈래로 다르게 취급한다. 감사 대상에서 빼고, 커버리지에서도 빼되,
**관통 대상에는 남긴다.** 선이 실제로 그 위를 지나면 제외 섹션이든 아니든 깨진 선이다.

## 고치고 배포하기

작업본은 `~/.claude/skills/fig/`, 배포본은 저장소다. 편집은 작업본에서 하고 저장소로 밀어 넣는다.

```
1  ~/.claude/skills/fig/ 에서 편집
2  python3 _figma-common/verify.py          위반 0 확인
3  .claude-plugin/plugin.json 의 version 판올림   ← 빠뜨리면 설치본이 안 바뀐다
4  저장소에 반영
5  claude plugin marketplace update byjunyoung
6  claude plugin uninstall fig@byjunyoung && claude plugin install fig@byjunyoung
```

**3번이 핵심이다.** 설치본은 `plugins/cache/<마켓>/<플러그인>/<버전>/` 에 버전으로 고정돼 있어서,
버전이 그대로면 마켓을 갱신해도 설치본은 옛 코드를 계속 쓴다.

**실행 권한에 기대지 않는다.** GitHub Contents API 로 올린 파일에는 실행 비트가 따라오지 않는다.
`check.sh` 를 직접 실행하면 설치본에서 `Permission denied` 가 난다 — `bash <path>` 로 부른다.
