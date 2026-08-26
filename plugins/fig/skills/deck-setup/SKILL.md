---
name: deck-setup
description: Measures a team slide template into local deck assets — template-spec.md, template.js, and reference images. Canvas, type scale, colors, and the archetype catalog are read from actual nodes; anything the sample is too thin to settle is left empty rather than guessed. Run once before using /fig:deck in a new environment, or again after the template is revised. Triggers - "/fig:deck-setup", "extract the slide template", "set up the deck assets", "덱 템플릿 뽑아줘", "발표 템플릿 추출", "템플릿 다시 추출".
allowed-tools: Read, Write, Bash, AskUserQuestion
---

# deck-setup — 발표 템플릿 추출

`/fig:deck`은 팀 템플릿의 좌표·색·타이포를 그대로 쓴다. 그 값이 어디서 오느냐가 이 스킬이다. **매 실행 원격 템플릿을 읽지 않고**, 여기서 한 번 뽑아둔 로컬 자산을 읽는다.

**핵심 전제**: 값을 지어내지 않는다. 관측이 애매하면 채우지 말고 비워 둔다. 빈 칸은 `/fig:deck`이 "그 아키타입은 없다"로 읽고 다른 것을 고른다. 없는 것과 못 잰 것을 섞으면 덱이 템플릿에서 조용히 벗어난다.

## When to invoke

- 새 환경·새 회사에서 `/fig:deck`을 처음 쓸 때
- 팀 템플릿이 개정돼 값이 달라졌을 때
- 자산 폴더가 없거나 `/fig:deck`이 "자산 없음"으로 멈출 때

## When NOT to invoke

- 덱을 만드는 것 자체 → `/fig:deck`
- 디자인 파일 관례 추출 → `/fig:setup` (별개다. 이건 Slides 템플릿 전용)

## 설정

`deck.assets_dir`가 자산을 둘 곳이다. 기본값은 `./deck-assets`이고, 여러 프로젝트에서 같은 템플릿을 쓰면 `~/.claude/deck-assets`으로 옮겨도 된다.

**자산은 플러그인 안에 두지 않는다.** 팀 템플릿 스크린샷과 배경 이미지에는 워드마크·주소 같은 회사 자산이 들어 있어 배포본에 실리면 안 된다.

## 1. 템플릿에 닿는다

원천 템플릿 파일은 대개 MCP 권한 밖이다. 그럴 때는 미러를 만든다.

1. 빈 Slides 파일을 만든다 — `create_new_file`, editorType `slides`
2. **사용자에게 Templates 패널에서 팀 템플릿을 적용해 달라고 요청하고 기다린다.** MCP로는 적용되지 않는다
3. 적용하면 샘플 슬라이드가 통째로 딸려 들어온다. 이게 카탈로그의 원본이다

적용 여부를 먼저 확인한다. 텍스트가 `Inter`·'Pick a style'로 남아 있으면 아직 안 된 것이다.

## 2. 실측 (읽기 전용)

딸려 들어온 샘플을 전수로 잰다. 눈으로 보지 말고 값을 읽는다.

| 무엇 | 어떻게 |
|---|---|
| 캔버스 | 슬라이드 `absoluteBoundingBox`의 폭·높이 |
| 여백 | 각 슬라이드 자식의 최소·최대 x — 최빈값이 좌우 여백이다 |
| 타이포 | 모든 TEXT의 `fontSize`·`fontName`·`letterSpacing`·`lineHeight` 분포 |
| 컬러 | 모든 `fills`·`strokes`의 색 분포. `getLocalPaintStyles`도 함께 |
| 텍스트 스타일 | `getLocalTextStylesAsync` — named 스타일이 곧 타입 사다리다 |
| 아키타입 | 슬라이드마다 이름·자식 구성·제목 위치·콘텐츠 상단 y |

`/fig:setup`과 같은 판정 기준을 쓴다. **표본이 얇거나 값이 갈리면 채우지 않는다.** 한 값이 표본 5개 이상에서 9할 넘게 쏠릴 때만 관례로 굳힌다.

**타입 사다리는 named 텍스트 스타일에서 가져온다.** 실측 `fontSize` 분포에는 손으로 고친 예외가 섞여 있어, 그걸 사다리로 삼으면 사다리가 무의미해진다.

## 3. 아키타입 카탈로그

슬라이드 하나가 아키타입 하나다. 각각에 대해 적는다.

    번호 · 이름 · 쓰임 한 줄
    제목 위치 계열 (상단형 / 좌제목 세로중앙형 / 캡션형 / 제목 없음)
    콘텐츠 상단 y · 열 수 · 열 폭 · 열 간격
    슬롯 (제목·부제·본문·이미지·수치 각각의 좌표와 크기)

**계열을 세어 보고한다.** 제목 위치가 넷, 콘텐츠 상단 y가 여섯 가지로 나오는 것이 정상이다. 템플릿은 덱이 아니라 메뉴라 골라 쓰라고 만든 대안 목록이다. 이 숫자를 `/fig:deck` 3단계에서 사용자가 충실도를 고를 때 근거로 쓴다.

참조 이미지가 필요하면 아키타입마다 스크린샷을 떠 `template-assets/`에 번호 이름으로 둔다. 없어도 동작하지만, 있으면 고를 때 정확해진다.

## 4. 자산 쓰기

`deck.assets_dir`에 셋을 만든다. 로컬 파일이라 미리보기 없이 바로 쓰되, 이미 있으면 덮기 전에 알린다.

**`template-spec.md`** — 사람이 읽는 스펙.

```
캔버스·그리드      폭·높이·여백·열 폭·열 간격
타이포            패밀리 후보 · 사다리(크기·굵기·자간·행간)
컬러              이름 → hex. 의미가 붙은 것만
아키타입 카탈로그   위 3장 형식으로 전수
선택 규칙          내용 형태 → 아키타입 매핑
```

**`template.js`** — 빌드 스크립트에 붙일 상수와 빌더. `_common/scripts/deck-base.js` **다음에** 붙는 것을 전제로 쓴다.

```js
const FAMS = ['<팀 폰트>', 'Inter'];        // 선호 순
const C = { bg: hx('#…'), text: hx('#…'), … };
const T = { title:{size:…,style:'Bold',ls:…,lh:…}, … };
const SW = …, SH = …, MARGIN = …, CELL_W = …, CELL_GAP = …;
// 아키타입 빌더 — 관측한 슬롯 좌표를 그대로 넣는다. 새 좌표를 만들지 않는다
function titleSlide({title, subtitle, bgImageHash}) { … }
```

빌더는 `deck-base.js`의 `newSlide`·`addText`·`addRect`·`addImageRect`·`addLine`을 쓴다. 요소 만드는 코드를 다시 쓰지 않는다 — 거기에 `appendChild` 순서 같은 규칙이 박혀 있다.

**`template-assets/`** — 표지·마무리 배경처럼 도형으로 재현할 수 없는 이미지. 워드마크나 미션 문구가 구워져 있으면 그 이미지를 그대로 쓰고 도형으로 흉내내지 않는다.

## 5. 검증

**스펙만 쓰고 끝내지 않는다. 한 장을 실제로 지어 본다.**

1. 카탈로그에서 아키타입 하나를 골라 `template.js` 빌더로 슬라이드를 만든다
2. 원본 샘플과 좌표·크기·색을 대조한다
3. 어긋나면 스펙이 틀린 것이다. 슬라이드를 고치지 말고 스펙을 고친다

한 장이 맞으면 계열마다 한 장씩, 넷이면 넷을 더 지어 본다. 제목 위치 계열이 어긋나는 것이 가장 흔하다.

마지막으로 세 가지를 보고한다.

- 아키타입 몇 개를 카탈로그에 넣었고, 몇 개를 **못 재서 비웠는지**
- 제목 위치 계열이 몇 가지, 콘텐츠 상단 y가 몇 가지인지
- 팀 폰트가 이 환경에 있는지 — 없으면 `/fig:deck`이 대체 폰트로 돌고 자간이 달라진다
