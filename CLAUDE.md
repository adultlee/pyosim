# CLAUDE.md

표심(pyosim) — 한국 선거 개표결과에서 **쌍둥이 득표**(서로 다른 투표소에서 같은 두 후보가 같은 득표수를 받은 사례)를 찾아 보여주는 도구.

## 무엇을 하는 프로젝트인가

선관위 개표결과 원본(XLS/XLSX/HTML)을 파싱 → 정규화 tidy CSV → 쌍둥이 득표 분석 JSON → 정적 웹앱으로 시각화.

배경: 2026-06-03 9회 지선 인천 송도1·2동 관내사전투표에서 양당 후보 득표가 완전 일치한 논란("5.9억분의1 확률" 주장)에 대해, "과거 선거에서 이런 일이 얼마나 자주 있었나"를 **빈도**로 보여준다. 부정선거 탐지가 아니라 중립적 맥락 데이터이며, 확률 계산은 하지 않는다.

## 쌍둥이 득표 정의 (★ 핵심 — 2026-06-17 확정)

같은 **비교 단위** 안에서, **서로 다른 두 투표소(읍면동)에서 같은 두 후보가 같은 득표수**를 받으면 쌍둥이다. = **투표소 "간" 반복**.

- 예: A동 관내사전투표 박찬대 583 = 유정복 583, **그리고** B동 관내사전투표에서도 박찬대 583 = 유정복 583 → 쌍둥이.
- **순위 무관**: 1·2위뿐 아니라 인접한 어떤 순위 쌍(2·3위, 5·6위…)이어도 됨. 단 같은 투표소 내 **인접 순위**여야 함.
- **최소 득표 임계값: 각 후보 10표 이상**인 동률만 인정. (1표=1표 같은 군소후보 저득표 동률은 노이즈이므로 제외 — 이게 이 도구의 핵심 품질 기준.)
- **이름과 표수 둘 다 일치**해야 함 (표수만 같고 후보 다른 건 쌍둥이 아님).
- **같은 투표 구분(level)끼리만** 비교 (관내사전투표는 관내사전투표끼리, 선거일투표는 선거일투표끼리). **합계(`계`) 행은 절대 비교 대상에 넣지 않는다** — 사전+선거일이 우연히 합산 동률이 되는 가짜 사례를 만들기 때문.
- **최소 단위 = 읍면동 × 투표구분으로 통일.** 회차마다 원본 단위가 다름(3회 지선은 투표구 `가리봉제1동제3투`까지, 9회·총선·대선은 읍면동까지). 투표구는 읍면동으로 합산해 통일한다(`제N투`·`투표소` 접미사 제거). 시·구로 올리지 않음(득표 커져 동률 안 남). 자세한 정의·카드 스펙·정당색표는 `docs/twin-vote-spec.md` 참조.

비교 단위 (선거별 group key):
- 대선: (회차, level) — 전국
- 총선 지역구: (회차, 선거구분, 선거구명, level) / 총선 비례: (회차, 선거구분, level)
- 지방선거 시도지사·교육감·광역비례: (회차, 선거종류, 시도그룹, level)
- 지방선거 나머지: (회차, 선거종류, 시도, 구시군, level)

**주의 — 했던 실수:** ① "투표소 내 1·2위 동률"(한 투표소에서 1위=2위)과 혼동하지 말 것. 그건 다른 정의이고, 이 프로젝트는 **투표소 간 반복**이다. ② `계` 합계 행을 투표소로 착각하면 가짜 동률이 대량 잡힌다.

## 구조

```
etl/                 선거종류별 파서 (Python, TDD)
  local/             지방선거  — parse_3rd ~ parse_9th, build.py, validate.py
  assembly/          총선      — parse_16th ~ parse_22nd
  pres/              대선      — parse_14 ~ parse_21
analyze_twin_votes.py  tidy CSV → web/public/twin_votes_*.json 굽는 스크립트
web/                 Vite + React + TS 정적 SPA (배포 대상)
  public/            twin_votes_{선거}_{회차}.json + twin_votes_index.json + votes_{선거}_{회차}.csv.gz(개표 원본 다운로드) + votes_csv_index.json
  src/App.tsx        index.json 읽고 회차별 JSON fetch
data/raw/            선관위 원본 (gitignore, 로컬 전용)
data_processed/      tidy CSV 산출물 (gitignore, ETL로 재생성)
```

## ETL 파이프라인

각 선거종류는 독립 오케스트레이터를 가진다. **검증을 통과해야만 CSV를 쓴다** (실패 시 exit≠0).

```bash
python -m etl.local.build       # 지방선거  → data_processed/지방선거.csv
python -m etl.assembly.build    # 총선      → data_processed/국회의원선거.csv
python -m etl.pres.build        # 대선      → data_processed/대통령선거.csv
python analyze_twin_votes.py    # CSV 3종 → web/public/twin_votes_*.json + index
python split_votes_csv.py        # CSV 3종 → web/public/votes_*.csv.gz + votes_csv_index.json (회차별 다운로드용)
```

- 파서는 **TDD로 작성**한다. 새 회차 파서는 `etl/<종류>/validate.py`의 검증 게이트(공식 득표 총합 대조 등)를 통과해야 한다.
- `nec-csv-parser` 에이전트가 한 회차/선거종류 파서를 TDD로 구현하는 전용 도구다.
- 출력 JSON 파일명 규칙: `twin_votes_{선거명}_{회차}.json` (예: `twin_votes_지방선거_9.json`, `twin_votes_총선_제22대.json`). `App.tsx`의 fetch 경로와 정확히 일치해야 한다.

## 웹앱 / 배포

```bash
cd web && npm install      # 최초 1회 (루트 npm i는 web 의존성을 설치하지 않음)
npm run dev                # 루트에서 — vite dev server
npm run build              # tsc -b && vite build → web/dist
```

- **배포: Vercel로 통일.** GitHub(`adultlee/pyosim`) `main` push 시 자동 배포. 주소: https://pyosim.vercel.app
- Vercel 프로젝트의 **Root Directory = `web`**. 빌드 설정은 `web/vercel.json`(`framework: vite`)이 담당.
- **`vite.config.ts`의 `base`는 반드시 `'/'`** — Vercel은 루트 도메인이라 하위경로 base(`/pyosim/`)를 넣으면 에셋이 404 나고 흰 화면이 된다. (과거 GitHub Pages용 `/pyosim/` base 때문에 이 사고가 있었음.)

## 작업 범위

지방선거가 먼저 완성됐고, 총선·대선은 **같은 검증 게이트로 후속 확장**한 결과다. 새 선거종류/회차를 붙일 때도 동일하게 parse → validate → CSV → analyze 흐름을 따른다.
