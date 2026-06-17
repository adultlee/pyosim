# 개표 원본 CSV 회차별 다운로드 — 설계

작성일: 2026-06-17 (개정 — 초안의 "쌍둥이 결과 CSV"에서 **전체 개표 원본 CSV** 제공으로 방향 변경)

## 배경 / 전제

다운로드 기능을 붙이기 전에 **내보낼 CSV(원천 데이터)가 무결한지** 먼저 확인했다.
`data_processed/*.csv` 3종에 ETL 검증 게이트(CSV만으로 재현 가능한 검사)를 재실행 → 위반 0건.

- 중복 키 행, 값 범위(득표 ≤ 투표수 ≤ 선거인수), 공식 1위 득표 대조: 지선·총선·대선 모두 통과.
- 한계: 합계행 대조(`check_totals_match`)는 런타임 totals가 필요해 제외. 총선은 `etl/assembly/official_totals.py`의 `OFFICIAL_TOP`이 비어 있어 공식 득표 대조가 스킵됨(중복·값범위는 통과).

점검 스크립트: `check_csv_integrity.py` (일회성, 재실행 가능).

## 목표

웹앱 방문자가 **전체 개표 원본 tidy CSV**(`data_processed/*.csv`)를 **선거×회차 단위로 나눠서** 다운로드할 수 있게 한다. 쌍둥이로 걸러진 결과가 아니라 모든 투표소 개표 원천 데이터를 제공한다.

## 왜 나눠야 하는가 (실측)

| 파일 | 총 크기 | 가장 큰 회차 |
|---|---|---|
| 국회의원선거.csv | 422MB | 제21대 121MB, 제22대 99MB |
| 지방선거.csv | 184MB | 7회 34MB |
| 대통령선거.csv | 113MB | 19대 27MB |

- 통째로는 브라우저 다운로드/호스팅에 부적합.
- 회차별로 나눠도 총선 21대가 121MB → **GitHub 단일 파일 100MB 하드 제한 초과**.
- → **gzip 압축**으로 해소. 개표 데이터는 반복 문자열이 많아 압축률이 매우 높음. **실측: 총선 21대 121MB → 4.1MB (3%).** 전체 회차 .gz 합계도 수 MB 수준.

## 결정 사항

- **분할 단위:** 선거×회차 (웹 회차 선택 단위와 일치).
- **형식:** 각 회차 CSV를 `.csv.gz`(gzip)로 압축해 `web/public/`에 커밋.
- **다운로드 UX:** 버튼은 `.csv.gz`를 **그대로** 다운로드(브라우저 측 압축 해제 없음). 사용자가 직접 해제(맥/리눅스 더블클릭, 윈도우 기본 지원). 압축 파일임을 안내 문구로 표기.
- **호스팅:** Vercel `web/public` 정적 서빙. 별도 LFS·외부 스토리지 없음.

## 비범위 (YAGNI)

- 전체 회차 일괄(zip) 다운로드
- 브라우저 측 gzip 해제 후 .csv 제공
- 시도/구시군 등 더 잘게 나누기
- ETL 자체 변경 (`data_processed` 산출 방식은 그대로)

## 파일명 / 매핑 규칙

기존 JSON 규칙(`twin_votes_{선거}_{회차}`)과 평행하게 둔다. CSV의 `선거_회차` 컬럼 값으로 행을 나누되 파일명은 웹 회차 키와 맞춘다:

| 선거종류 | CSV 컬럼값 예 | 웹 회차키 | 출력 파일명 |
|---|---|---|---|
| 지방선거 | `9` | `9` | `votes_지방선거_9.csv.gz` |
| 대선 | `14` | `14` | `votes_대선_14.csv.gz` |
| 총선 | `제22대` | `제22대` | `votes_총선_제22대.csv.gz` |

(선거종류 라벨 `지방선거`/`총선`/`대선`은 `twin_votes_index.json`의 `elections` 키와 동일.)

## 컴포넌트

### 1. 분할 스크립트 — `split_votes_csv.py` (신규, Python)

- 입력: `data_processed/{지방선거|국회의원선거|대통령선거}.csv`.
- 동작: 각 파일을 `선거_회차` 컬럼 값으로 그룹화 → 회차별 부분 CSV를 **gzip 스트림**으로 `web/public/votes_{선거}_{회차}.csv.gz`에 기록.
  - 선거종류명 매핑: 국회의원선거→`총선`, 대통령선거→`대선`, 지방선거→`지방선거`.
  - CSV는 `utf-8-sig`(BOM) 유지(엑셀 한글 대응), 헤더 포함, `data_processed` 원본 컬럼/내용 그대로.
- 산출 후 각 파일 크기를 로그로 출력(100MB 초과 시 경고).
- ETL 흐름 문서(CLAUDE.md/README)에 `analyze_twin_votes.py` 다음 단계로 추가.

### 2. 다운로드 매니페스트 — `web/public/votes_csv_index.json` (분할 스크립트가 생성)

버튼이 "이 회차 파일이 존재하는가/크기"를 알 수 있도록 메타를 둔다:

```json
{
  "대선": { "14": { "file": "votes_대선_14.csv.gz", "rows": 29272, "bytes": 1234567 }, ... },
  "총선": { "제22대": { ... } },
  "지방선거": { "9": { ... } }
}
```

(웹은 회차 선택값으로 이 매니페스트를 조회해 링크·크기 표시. 매니페스트 없거나 키 없으면 버튼 숨김 → 하위호환.)

### 3. 다운로드 버튼 — `TwinVoteViewer.tsx`

- 위치: 요약 줄([TwinVoteViewer.tsx:407](web/src/components/TwinVoteViewer.tsx#L407))의 `flex justify-between` 우측, 페이지 표시 옆.
- 표시: "개표 원본 CSV 내려받기 (NN MB, gzip)" — 매니페스트의 bytes로 크기 표기.
- 동작: `<a href="/votes_{선거}_{회차}.csv.gz" download>` 정적 링크. 임시 Blob 불필요(정적 파일이라 href 직접).
- 매니페스트에 해당 회차 없으면 버튼 미표시.
- 안내: 압축 파일이며 해제하면 전체 투표소 개표결과 tidy CSV임을 한 줄 툴팁/캡션.

### 4. 매니페스트 로드 — `App.tsx`

- 기존 `twin_votes_index.json` fetch 지점에서 `votes_csv_index.json`도 함께 fetch(실패해도 앱 동작 — 버튼만 숨김).
- TwinVoteViewer에 현재 선거·회차의 csv 메타를 prop으로 전달.

## 검증 기준

1. `python split_votes_csv.py` 실행 → `web/public/votes_*.csv.gz` + `votes_csv_index.json` 생성.
   - 모든 회차 파일 < 100MB (특히 총선 21대).
   - 임의 회차 `.gz` 해제 → 행 수가 `data_processed` 해당 회차 행 수와 일치, 헤더 동일, BOM 유지.
   - 매니페스트의 회차 키가 `twin_votes_index.json`의 회차 키와 1:1 일치(버튼이 항상 매칭).
2. `cd web && npm run build` (`tsc -b && vite build`) 통과.
3. 브라우저: 회차 선택 → 버튼 표시·크기 정확 → 클릭 시 `.csv.gz` 다운로드 → 해제 후 엑셀에서 한글 정상.

## 테스트

- 분할 스크립트: Python `tests/`에 단위 테스트 추가(작은 합성 DataFrame → 분할 → gz 해제 후 행 수·헤더·매니페스트 키 검증). 기존 `tests/` 패턴 따름.
- 프론트엔드: 테스트 러너 부재 → 타입체크(`tsc`) + 브라우저 수동 확인. (web에 vitest 도입은 이번 범위 밖.)

## 운영 메모

- `data_processed/*.csv`는 gitignore지만 **분할 산출물 `web/public/votes_*.csv.gz`는 커밋**된다(배포에 필요). 실측 압축률(~3%) 기준 전체 합계는 수 MB 수준이라 레포 부담 적음.
- 원본 재생성 시 분할 스크립트도 다시 돌려 `.gz` 갱신.
