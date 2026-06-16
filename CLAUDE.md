# CLAUDE.md

표심(pyosim) — 한국 선거 개표결과에서 **쌍둥이 득표**(1·2등 후보의 이름과 득표수가 완전히 동일한 투표구)를 찾아 보여주는 도구.

## 무엇을 하는 프로젝트인가

선관위 개표결과 원본(XLS/XLSX/HTML)을 파싱 → 정규화 tidy CSV → 쌍둥이 득표 분석 JSON → 정적 웹앱으로 시각화.

- **쌍둥이 득표 기준:** 같은 그룹 안에서 1등과 2등 후보의 **이름이 같고 득표수도 정확히 같은** 경우. 임계값·근사 없음. 통계적 이상을 주장하지 않는 **중립적 탐색 도구**다.

## 구조

```
etl/                 선거종류별 파서 (Python, TDD)
  local/             지방선거  — parse_3rd ~ parse_9th, build.py, validate.py
  assembly/          총선      — parse_16th ~ parse_22nd
  pres/              대선      — parse_14 ~ parse_21
analyze_twin_votes.py  tidy CSV → web/public/twin_votes_*.json 굽는 스크립트
web/                 Vite + React + TS 정적 SPA (배포 대상)
  public/            twin_votes_{선거}_{회차}.json + twin_votes_index.json
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
