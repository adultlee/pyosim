# 쌍둥이 결과 CSV 다운로드 — 설계

작성일: 2026-06-17

## 배경 / 전제

다운로드 기능을 붙이기 전에 **내보낼 CSV(원천 데이터)가 무결한지** 먼저 확인했다.
`data_processed/*.csv` 3종에 ETL 검증 게이트(CSV만으로 재현 가능한 검사)를 재실행 → 위반 0건.

- 중복 키 행, 값 범위(득표 ≤ 투표수 ≤ 선거인수), 공식 1위 득표 대조: 지선·총선·대선 모두 통과.
- 한계: 합계행 대조(`check_totals_match`)는 런타임 totals가 필요해 제외. 총선은 `etl/assembly/official_totals.py`의 `OFFICIAL_TOP`이 비어 있어 공식 득표 대조가 스킵됨(중복·값범위는 통과).

점검 스크립트: `check_csv_integrity.py` (일회성, 재실행 가능).

## 목표

웹앱 방문자가 **현재 화면에 로드된 쌍둥이 결과**(twin_votes JSON)를 회차별 CSV로 다운로드할 수 있게 한다.

- 범위: **프론트엔드만.** `web/public/twin_votes_*.json`은 그대로 둔다. 서버/ETL 변경 없음.
- 데이터는 이미 브라우저에 로드돼 있으므로 클라이언트에서 CSV로 변환해 Blob 다운로드.

## 비범위 (YAGNI)

- 전체 회차 일괄 다운로드
- 화면 필터 적용 결과만 받기 (항상 해당 회차 전체를 내보냄)
- ETL/서버 측 CSV 정적 생성
- 원본 tidy CSV(`data_processed/*.csv`) 다운로드

## 데이터 모델 (입력)

각 라운드 JSON = `{ twins: TwinGroup[] }`. 한 `TwinGroup`은 "같은 두 후보가 같은 득표를 받은 투표소들"의 묶음:

- `category` — 비교단위 문자열 (예: `대선_당일투표`, `지방선거_시도지사_사전투표`)
- `votes` — 동률을 이룬 두 후보 `{후보:득표수}` (정확히 2개)
- `parties?` — `{후보:정당}`
- `total_votes`, `count`(투표소 수), `rank_pair`(순위쌍)
- `locations[]` — 투표소들: `시도, 구시군, 읍면동, 1위, 1위득표, 투표수, 선거인수`

## CSV 형식 (출력)

**행 단위 = 투표소 1개.** 각 그룹의 `locations[]`를 평탄화하고, 그룹 공통값을 매 행 반복.

컬럼(한글 헤더, 이 순서):

```
선거구분, 회차, 비교단위, 후보A, 후보B, 동률득표A, 동률득표B,
정당A, 정당B, 순위쌍, 그룹투표소수,
시도, 구시군, 읍면동, 그투표소1위, 1위득표, 투표수, 선거인수
```

- `선거구분`/`회차`: 다운로드 시점의 선택값(예: `대선`, `14`).
- `비교단위`: `group.category`.
- `후보A/후보B`: `Object.keys(votes)`의 두 값. `동률득표A/B`: 대응 값.
- `정당A/B`: `parties?.[후보A/B]` (없으면 빈 칸).
- `순위쌍`: `"6·7"` 형태 (`rank_pair`).
- `그룹투표소수`: `group.count`.
- 투표소 칼럼: 해당 location의 필드. 없으면 빈 칸.

규칙:
- 값에 `,` `"` 개행 포함 시 `"`로 감싸고 내부 `"`는 `""`로 이스케이프.
- 줄 구분 `\n`. 선두에 **UTF-8 BOM**(`﻿`) — 엑셀 한글 대응(기존 CSV도 `utf-8-sig`).
- `null`/`undefined`/`NaN`은 빈 칸.

## 컴포넌트

### 1. `web/src/twinCsv.ts` (신규)

```
twinGroupsToCsv(twins: TwinGroup[]): string
```

- 헤더 + 평탄화 행을 BOM 포함 문자열로 반환. 순수 함수(부수효과 없음) → 단위 테스트 대상.
- CSV 이스케이프 헬퍼 내부 정의.

### 2. `TwinVoteViewer.tsx` — 다운로드 버튼

- 위치: 요약 줄([TwinVoteViewer.tsx:407](web/src/components/TwinVoteViewer.tsx#L407))의 `flex justify-between` 우측, 페이지 표시 옆.
- 라벨: "CSV 다운로드". 기존 버튼/배지 스타일(`var(--color-...)`) 따름.
- 동작: 해당 회차 **전체 `twins`**(필터 전)를 `twinGroupsToCsv`로 변환 → `Blob([..], {type:'text/csv;charset=utf-8'})` → `URL.createObjectURL` → 임시 `<a download={파일명}>` 클릭 → `revokeObjectURL`.
- 파일명: `pyosim_{선거}_{회차}.csv` (예: `pyosim_대선_14.csv`).
- 빈 데이터면 버튼 비활성화 또는 숨김.

## 검증 기준

1. `cd web && npm run build` (`tsc -b && vite build`) 통과.
2. `twinGroupsToCsv` 단위 테스트:
   - 콤마/따옴표/개행 포함 값이 올바르게 이스케이프된다.
   - 평탄화된 데이터 행 수 == `sum(group.count)` (= 모든 locations 합).
   - `votes` 2개 후보가 `후보A/B`·`동률득표A/B`에 정확히 매핑된다.
   - `parties` 없는 그룹은 정당 칸이 빈 칸이다.
   - 결과 문자열이 BOM으로 시작한다.
3. 브라우저에서 한 회차 다운로드 → 엑셀에서 한글 안 깨지고 컬럼 정렬 정상.

## 테스트 인프라

- 기존 web 테스트 러너 확인 후 동일 방식 사용. 없으면 vitest 도입은 별도 판단(현재 `tests/`는 Python). web 단위 테스트 도구 부재 시 사용자에게 도입 여부 확인.
