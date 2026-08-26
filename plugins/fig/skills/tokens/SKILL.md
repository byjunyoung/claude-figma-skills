---
name: tokens
description: Audits whether the colors on a Figma frame or page are bound to design system tokens, and maps and binds hardcoded colors to the right token. Derives token-to-hex from bindings already in the file so every mapping has evidence, grades the results, and auto-proposes only the safe ones. Lint mode (check only) and bind mode are separate. Which library and which token groups come from the design_system section of figma-conventions.yaml; on auto it detects the library the file is connected to. Triggers - "/fig:tokens", "check the token bindings", "find unbound colors", "토큰 바인딩 검수", "하드코딩 색상 검사", "디자인시스템 연동 점검".
allowed-tools: AskUserQuestion, mcp__plugin_figma_figma__use_figma, mcp__plugin_figma_figma__search_design_system, mcp__plugin_figma_figma__get_screenshot, mcp__plugin_figma_figma__get_metadata
---

# fig:tokens — 디자인시스템 토큰 바인딩 검수·정비

프레임 안의 색이 "디자인시스템 변수에 묶여 있는가"를 검수하고, 묶이지 않은 하드코딩 색을 **근거 있는 매핑**으로 토큰에 연결한다. 색 하나하나가 토큰을 타야 테마·리브랜딩·일관성이 유지되므로, 핸드오프 전 마지막 점검 단계로 쓴다.

**전제**: `use_figma` 호출 전 반드시 `figma:figma-use` 스킬을 먼저 로드한다.

## When to invoke

- "이 프레임 색이 토큰에 다 묶였는지 봐줘", "변수 안 묶인 색 찾아줘"
- "하드코딩 hex를 토큰으로 일괄 바꿔줘"
- 디자인 완성 후 핸드오프 직전 토큰 연동 점검

## When NOT to invoke

- 프레임 네이밍·섹션 정리 → `/fig:prep`
- 구조·흐름 규칙 위반 검증 → `/fig:lint`
- 흐름 화살표 → `/fig:arrows`
- 토큰(변수) 자체를 새로 만들기 → `figma:figma-generate-library`
- 화면 디자인 생성 → `figma:figma-generate-design`

## Inputs

- `figma_url` (필수): 검수할 페이지·프레임 URL
- `mode` (선택): Lint 모드(검사만) / 바인딩 실행. 생략하면 검사 후 매핑표로 제안한다

규칙 원천은 `figma-conventions.yaml` 이다 — `resolve-config.py --js <fileKey>` 로 `design_system` 절(라이브러리·토큰군·임계)을 읽는다.

## 왜 이 스킬이 따로 필요한가 — 도구 제약

- **`get_metadata`로는 색을 못 본다.** 메타데이터에는 노드 ID·타입·좌표·크기만 있고 fill/stroke/effect 색 정보가 없다. 게다가 큰 프레임은 메타데이터가 토큰 한도를 넘겨 통째로 실패한다. 따라서 **색 검사·바인딩은 전부 `use_figma` 스크립트로 노드를 직접 순회**해서 한다.
- **`search_design_system`은 토큰의 hex 값을 주지 않는다.** 토큰의 이름·키·scope·소속 라이브러리만 준다. 실제 색값은 따로 알아내야 한다(아래 "토큰 hex 역추출").

## 토큰 출처 — 자동 감지 + hex 역추출 (핵심)

매핑의 신뢰도는 "이 토큰이 실제로 무슨 색인가"를 정확히 아는 데서 나온다. 두 경로를 병행한다.

1. **연결 라이브러리 감지**: `search_design_system` 으로 설정 `design_system.token_prefixes` 의 토큰군을 조회해 이름·키를 확보한다. 대상 라이브러리는 `design_system.library` 가 정하고, `auto` 면 파일에 연결된 라이브러리를 감지한다. **라이브러리 이름을 본문에 박지 않는다** — 파일마다 다르다. `token_prefixes` 가 비어 있으면 역추출 맵(2번)에 등장한 접두사를 그대로 후보로 쓴다.
2. **기존 바인딩에서 토큰→hex 역추출 (가장 신뢰도 높음)**: 같은 파일에서 *이미 변수에 바인딩된* 색들을 순회해 `{토큰명 → 실제 hex}` 맵을 만든다. 바인딩된 paint는 `boundVariables.color`로 토큰 ID를, `paint.color`로 마지막 해석된 실제 색을 함께 들고 있다. 이 파일이 실제로 그 토큰을 어떤 색으로 쓰는지를 그대로 보여주므로 매핑의 1차 근거가 된다.

> **주의 — 토큰 표면값은 요청 hex와 다를 수 있다.** 예를 들어 "어떤 회색을 `fill/primary`로 바꿔줘"라고 해도 `fill/primary`의 실제값은 그 회색과 미세하게 다를 수 있다(토큰화가 목적이면 정상). 색이 바뀌는 경우 **반드시 미리보기에 "이 토큰은 #AAA → 화면이 #BBB로 바뀜"을 명시**한다.

## 검사 대상 속성

fill · stroke · 텍스트 색(TEXT 노드의 fills) · 효과 색(effects의 color)을 모두 검사한다. 속성별로 매칭 가능한 토큰 scope가 다르다(예: 배경 fill ↔ `FRAME_FILL/SHAPE_FILL`, 테두리 ↔ `STROKE`, 텍스트 ↔ `TEXT_FILL`). **속성과 scope가 맞는 토큰끼리만 매핑한다** — 텍스트색을 테두리 토큰에 묶지 않는다.

## 제외 대상 (검수·바인딩 모두에서 건드리지 않음)

| 대상 | 이유 |
|---|---|
| 컴포넌트 **인스턴스 내부** 색 | 인스턴스 오버라이드라 깨지기 쉽고, 원본 컴포넌트(라이브러리) 쪽에서 토큰화해야 할 별도 이슈. 인스턴스 노드 *자신*의 색(오버라이드)은 대상이나, 그 *내부 자식*은 제외 |
| 작업용 스캐폴딩 | 설정 `naming` 의 스캐폴딩 이름 규약(`arrow_delimiter`·`label_prefix`·`state_chain_prefix`)에 걸리는 노드와 `section_style`·`placeholder_style` 로 칠해진 것 — `/fig:arrows`·`/fig:prep` 산출물이라 토큰화 대상이 아니다 |
| 사용자가 지정한 보호 영역 | 아카이브·템플릿 등 |

발견한 제외 항목은 **고치지 말고 보고만** 한다(특히 인스턴스 내부 색은 "컴포넌트 정비 이슈"로 따로 묶어 전달).

## 등급 분류 — 안전한 것만 자동 제안

미바인딩 색을, 같은 속성의 가장 가까운 토큰과 대조해 3등급으로 나눈다.

| 등급 | 기준 | 처리 |
|---|---|---|
| 1등급 — 정확/근접 일치 | 토큰 hex 와 동일하거나 채널 차가 설정 `design_system.match_threshold_channel` 이하 | 바인딩해도 색이 사실상 안 변함 → **자동 매핑 제안** |
| 2등급 — 색 변동 | 가장 가까운 토큰과 눈에 띄게 차이남(팔레트 밖 색) | 스냅하면 색이 바뀜 → **보고만, 진행은 사용자 판단** |
| 3등급 — 대응 토큰 없음 | 어느 토큰과도 멀거나 브랜드/특수색 | 바인딩 비권장, 보고만 |

임계값은 기준선일 뿐이다 — 경계의 색은 "Δ 얼마"를 같이 보여줘 사용자가 판단하게 한다.

## Lint 모드 — 검사만 (쓰기 없음)

"검사만/현황만" 요청이거나 정비 전 파악 단계. 읽기 전용으로 리포트만 낸다:

- 대상 범위 안 미바인딩 색을 **hex별로 집계**(속성·곳 수·대표 위치), 인스턴스 내부/스캐폴딩/직접수정가능으로 분류
- 직접 수정 가능한 색은 등급 분류표 + 추천 토큰·Δ를 붙인다
- 수정은 하지 않고, 별도 go를 받아 아래 Procedure로 진행

## Procedure

### 1. 토큰 사전 구축

- `search_design_system` 으로 설정 `design_system` 의 토큰군 이름·키 확보
- 대상 프레임을 순회해 **기존 바인딩 색 → {토큰명, 실제 hex}** 역추출 맵 생성
- 두 결과를 합쳐 `{토큰명, 키, scope, hex}` 사전을 만든다 — 매핑의 근거 테이블

### 2. 미바인딩 색 스캔 (읽기 전용)

- 대상 프레임을 순회하며 fill·stroke·텍스트·효과의 **SOLID이고 미바인딩**인 색을 hex별 집계
- 각 노드를 인스턴스 내부 / 스캐폴딩 / 직접수정가능으로 분류(아래 스니펫)
- 직접수정가능 색에 대해 사전과 대조해 등급·추천토큰·Δ 산출 → 매핑표

### 3. 매핑 확정 (사용자 선택)

- 1등급을 표로 제시. **하나의 hex가 의미가 다른 두 토큰에 동일 매칭되면**(예: 흰색이 `Static/white`와 `Background/normal/normal` 둘 다) 임의로 고르지 말고 의미 차이를 붙여 선택하게 한다
- 2·3등급은 보고만 하고, 진행 여부는 사용자에게
- 색이 바뀌는 매핑(2등급 등)은 변동 사실을 명시

### 4. 바인딩 (미리보기 → go, 단계 분할)

- 확정 매핑을 **미리보기**(대상·hex→토큰·곳 수·제외 사항)로 보여주고 **go**를 받는다
- 양이 많으면 **프레임별 또는 색상별로 분할** 실행 — 한 번에 다 쓰지 않는다
- `importVariableByKeyAsync`로 토큰을 임포트하고, hex가 정확히 일치하는 미바인딩 paint만 바인딩

### 5. 검증 (필수)

- **바인딩 후 재스캔**해 "직접 수정 가능한 대상 색의 미바인딩 잔여 = 0"을 확인한다
- 집계 단계의 곳 수와 실제 바인딩 수가 다를 수 있다 — 인스턴스 내부 노드 탐색 범위가 호출 간 흔들려 분류가 달라질 수 있기 때문(추정). **누락이 아님은 재스캔의 잔여 0으로 입증**하고, 차이는 정직하게 보고한다
- 남은 인스턴스 내부 색·2/3등급은 "이번 범위 밖"으로 분리해 보고

## 구현 스니펫

색→hex, 인스턴스 내부 판정:

```js
function hex(c){const f=x=>Math.round(x*255).toString(16).padStart(2,"0").toUpperCase();return "#"+f(c.r)+f(c.g)+f(c.b);}
function insideInstance(n){let p=n.parent;while(p){if(p.type==="INSTANCE")return true;p=p.parent;}return false;}
```

토큰→hex 역추출 (기존 바인딩 사용례에서):

```js
const map={}; // varId -> {name, hexes:{}, count}
for(const id of ROOT_IDS){
  const root=await figma.getNodeByIdAsync(id);
  for(const n of [root,...root.findAll(()=>true)]){
    for(const key of ["fills","strokes"]){
      const arr=n[key]; if(!Array.isArray(arr)) continue;
      for(const p of arr){
        if(p.type==="SOLID"&&p.visible!==false&&p.boundVariables&&p.boundVariables.color){
          const vid=p.boundVariables.color.id;
          if(!map[vid]){const v=await figma.variables.getVariableByIdAsync(vid);map[vid]={name:v?v.name:"?",hexes:{},count:0};}
          map[vid].count++; const h=hex(p.color); map[vid].hexes[h]=(map[vid].hexes[h]||0)+1;
        }
      }
    }
  }
}
return Object.values(map).map(e=>({name:e.name,count:e.count,hex:Object.keys(e.hexes).join(",")}));
```

미바인딩 색 집계 (직접수정가능/인스턴스내부 분류):

```js
const agg={};
for(const id of ROOT_IDS){
  const root=await figma.getNodeByIdAsync(id);
  for(const n of [root,...root.findAll(()=>true)]){
    const ii=insideInstance(n);
    for(const key of ["fills","strokes"]){
      const arr=n[key]; if(!Array.isArray(arr)) continue;
      for(const p of arr){
        if(p.type!=="SOLID"||p.visible===false) continue;
        if(p.boundVariables&&p.boundVariables.color) continue;
        const k=key+"|"+hex(p.color);
        if(!agg[k]) agg[k]={prop:key,hex:hex(p.color),editable:0,inInstance:0,examples:[]};
        agg[k][ii?"inInstance":"editable"]++;
        if(agg[k].examples.length<4) agg[k].examples.push((ii?"⟨inst⟩":"")+n.name+" ["+n.type+"]");
      }
    }
  }
}
return Object.values(agg).sort((a,b)=>b.editable-a.editable);
```

> 텍스트 색은 위 `fills`에 TEXT 노드로 포함된다. 효과 색은 `n.effects`의 `color`를 같은 방식으로 추가 검사하고, 바인딩은 효과 전용 API를 쓴다(d.ts에서 `setBoundVariableForEffect` 계열 확인).

바인딩 (hex 정확 일치만, 새 paint 재할당):

```js
const V={ tokenA: await figma.variables.importVariableByKeyAsync("KEY_A"), /* ... */ };
const fillMap={"#FFFFFF":V.tokenA, /* hex: variable */ };
const strokeMap={/* ... */};
const counts={};
const root=await figma.getNodeByIdAsync(FRAME_ID);
for(const n of [root,...root.findAll(()=>true)]){
  if(insideInstance(n)) continue;                 // 인스턴스 내부 제외
  for(const [key,mapObj] of [["fills",fillMap],["strokes",strokeMap]]){
    const arr=n[key]; if(!Array.isArray(arr)||!arr.length) continue;
    let changed=false;
    const next=arr.map(p=>{
      if(p.type==="SOLID"&&p.visible!==false&&!(p.boundVariables&&p.boundVariables.color)){
        const v=mapObj[hex(p.color)];
        if(v){changed=true;counts[v.name]=(counts[v.name]||0)+1;return figma.variables.setBoundVariableForPaint(p,"color",v);}
      }
      return p;                                    // fills는 읽기전용 — map으로 새 배열 생성
    });
    if(changed) n[key]=next;
  }
}
return {frame:FRAME_ID, counts};
```

검증 (잔여 0 확인):

```js
let editableLeft=0;
for(const id of ROOT_IDS){
  const root=await figma.getNodeByIdAsync(id);
  for(const n of [root,...root.findAll(()=>true)]){
    if(insideInstance(n)) continue;
    for(const key of ["fills","strokes"]){
      const arr=n[key]; if(!Array.isArray(arr)) continue;
      for(const p of arr){
        if(p.type==="SOLID"&&p.visible!==false&&!(p.boundVariables&&p.boundVariables.color)&&TARGET_HEXES.includes(hex(p.color))) editableLeft++;
      }
    }
  }
}
return {editableLeft};   // 0이어야 완료
```

## Constraints

- **쓰기 전 미리보기 → go.** 매핑표 확정과 바인딩 실행은 분리, 바인딩은 프레임별/색상별 단계 분할
- **인스턴스 내부 색·스캐폴딩은 건드리지 않는다** — 보고만
- 속성과 토큰 scope가 맞을 때만 매핑(텍스트색↔텍스트토큰 등)
- 색이 바뀌는 매핑은 변동을 미리보기에 명시 — 토큰명만 보고 색이 같다고 단정하지 않는다
- 한 호출당 작업량을 작게, 단계마다 재스캔/스크린샷으로 검증
- 검증되지 않은 "완료"를 쓰지 않는다 — 잔여 0을 재스캔으로 입증

## Notes

- 매핑의 1차 근거는 항상 **이 파일이 실제로 쓰는 토큰값**(역추출 맵)이다 — 토큰 이름의 어감으로 추측하지 않는다
- "미바인딩 색이 많다"가 곧 "누가 깜빡함"은 아니다 — 팔레트 밖 색이 섞여 들어온 상태일 수 있으니 2·3등급은 디자인 판단으로 넘긴다
- 인스턴스 내부의 대량 하드코딩 색은 이 스킬의 범위가 아니라 **컴포넌트(라이브러리) 정비 과제**로 따로 제기한다
