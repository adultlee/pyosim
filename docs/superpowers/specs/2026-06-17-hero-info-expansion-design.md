# 히어로 정보 확장 설계

작성일: 2026-06-17

## 목표

웹앱 상단 "히어로" 영역에 보여주는 정보를 확장한다. 현재 히어로는 (1) 상단 설명 글 + (2) 선택 회차 4개 수치 카드뿐이다. 다음 4가지를 추가한다:

1. **전체 누적 통계** — 지선·총선·대선 전 회차를 통튼 규모
2. **회차 간 추세** — 선택된 선거종류의 회차별 사례 수 추이
3. **선택 회차 대표 사례** — 기존 4개 카드 (즉시 표시로 개선)
4. **최다 반복 상위 N** — 기존 1개 → 상위 3~5개 리스트

## 핵심 구조 결정

프론트는 `twin_votes_index.json`(가벼움, 전 회차) + 선택한 한 회차 JSON만 로드한다. 전체 통계·추세를 위해 모든 회차 JSON을 여는 것은 무겁다. 따라서:

- **`analyze_twin_votes.py`가 index에 회차별 집계를 미리 굽는다.** 회차 JSON 파일 포맷은 건드리지 않는다.
- 상위 N(상위 후보쌍 정렬)은 회차 JSON에서 계산 — index에 다 넣기엔 과하다.

## 1. 데이터 레이어 — `index.json` 풍부화

### Python (`analyze_twin_votes.py`)

`twinStats.ts`의 회차 집계 로직을 Python으로 이식한다. 동일 묶음 키 규칙:
`category | json(group) | rank_pair join '-' | 정렬한 후보쌍 join '='`.

`_write_election`이 각 회차마다 계산해 `rounds_meta`에 담는다:

```jsonc
"지방선거": {
  "rounds": [...], "counts": {...}, "roundLabels": {...},   // 기존 유지(하위호환)
  "rounds_meta": {
    "9": {
      "pairCount": 412,          // 서로 다른 후보쌍 수
      "totalLocations": 1830,    // 모든 사례의 일치 투표소 합
      "groupCount": 837,         // 쌍둥이 그룹 수 (= counts와 동일값)
      "topPair": { "names": ["박찬대","유정복"],
                   "parties": ["더불어민주당","국민의힘"],
                   "locations": 2 }
    }
  }
}
```

index 루트에 선거종류별 전체 누적 합계도 굽는다:

```jsonc
"totals": {
  "지방선거": { "pairCount": N, "totalLocations": N, "groupCount": N },
  "총선":    { ... },
  "대선":    { ... },
  "all":     { "pairCount": N, "totalLocations": N, "groupCount": N }
}
```

- `pairCount`/`totalLocations`는 회차별 합이 아니라 **회차 무관 전체 후보쌍 집계의 합**으로 정의(누적). 구현 단순화를 위해: 전체 = Σ(회차별 pairCount·totalLocations). pairCount는 회차 내에서 dedup되므로 회차 합산은 "회차별 고유쌍의 총합"이 된다(서로 다른 회차의 동명 쌍은 별개로 셈) — 누적 규모 지표로 의도에 맞음.

### 타입 (`web/src/types.ts`)

```ts
export interface RoundMeta {
  pairCount: number
  totalLocations: number
  groupCount: number
  topPair: { names: [string, string]; parties: [string?, string?]; locations: number } | null
}
export interface ElectionIndex {
  rounds: string[]
  counts: Record<string, number>
  roundLabels: Record<string, string>
  rounds_meta?: Record<string, RoundMeta>   // 옵셔널 — 구 index 하위호환
}
export interface TwinTotals { pairCount: number; totalLocations: number; groupCount: number }
export interface TwinIndex {
  elections: Record<string, ElectionIndex>
  totals?: Record<string, TwinTotals>        // 옵셔널
}
```

옵셔널로 두어 index 재생성 전 구 파일로도 흰 화면 없이 동작.

## 2. UI — 히어로 4영역

`App.tsx` main 안, 설명 글 ~ 탭 ~ 카드 사이에 배치.

### (A) 전체 누적 띠
- 위치: 설명 글(라인 100~119) 바로 아래. 선거종류와 무관하게 항상 표시.
- 내용: "지선 3~9회 · 총선 16~22대 · 대선 14~21대 통틀어 — 동일 득표 사례 **N건** / 후보쌍 **N쌍** / 일치 투표소 **N곳**".
- 소스: `index.totals.all`. `totals` 없으면 영역 숨김.

### (B) 회차 추세
- 위치: 선거종류 탭 + 회차 탭 아래.
- 내용: 선택된 선거종류의 회차별 `groupCount`(없으면 `counts`)를 작은 막대들로. 막대 높이 = 값/최댓값. 선택 회차 강조색(accent). 막대 클릭 → 해당 회차 선택.
- 라이브러리 미사용(div 높이 막대). 각 막대 아래 회차 라벨, 위 또는 호버에 값.
- 소스: `rounds_meta` 우선, 폴백 `counts`.

### (C) 선택 회차 카드 4개
- 기존 4카드 유지. **소스를 회차 JSON → `rounds_meta[선택회차]`로 변경** → 회차 JSON 로드 전에도 즉시 표시.
- `rounds_meta` 없으면 폴백으로 기존 `computeRoundStats(data)` 사용(로드 후 표시).

### (D) 최다 반복 상위 N
- 기존 4번째 카드("최다 반복 후보쌍" 1개)를, **회차 JSON 로드 후** 상위 3~5개 미니 리스트로 확장.
- 로드 전: `rounds_meta.topPair` 1개만 표시. 로드 후: 상위 N 리스트로 교체.
- `twinStats.ts`: `topPair` → `topPairs: [...]`(정렬된 상위 N) 반환하도록 확장. 기존 `topPair`는 `topPairs[0]`로 유지하거나 호출부 수정.

## 컴포넌트 경계

- `twinStats.ts` — 회차 JSON → 상위 N 등 회차 단위 파생값. (D)용.
- `App.tsx` — index에서 (A)(B)(C) 직접 읽음. 추세 막대는 작은 인라인 블록 또는 `HeroTrend` 소형 컴포넌트로 분리(App.tsx 비대화 방지).
- Python `_round_meta(twins)` 헬퍼 — `_write_election` 안에서 회차별 호출.

## 검증 / 성공 기준

1. `python analyze_twin_votes.py` 실행 → index.json에 `rounds_meta`·`totals` 포함, 기존 회차 JSON 변화 없음.
2. Python `_round_meta` 결과가 `twinStats.computeRoundStats`와 동일 회차에서 같은 pairCount/totalLocations/groupCount/topPair를 내는지 1개 회차 대조.
3. `npm run build` 통과(tsc).
4. dev에서: (A) 누적 띠 표시, (B) 막대 클릭 시 회차 전환, (C) 회차 클릭 즉시(JSON 로드 전) 카드 수치 표시, (D) 로드 후 상위 N 리스트.
5. 구 index.json(rounds_meta 없음)으로도 흰 화면 없이 폴백 동작.

## 배포 주의

- index 재생성은 `data/raw` 보유 컴퓨터에서만 가능. 커밋 전 `python analyze_twin_votes.py` 실행 필요.
- `vite.config.ts` base는 `/` 유지.

## YAGNI / 비범위

- 차트 라이브러리 추가 안 함.
- 회차 간 후보쌍 동일성 추적(같은 쌍이 여러 회차 반복) 안 함 — 누적은 단순 합산.
