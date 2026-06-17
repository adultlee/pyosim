# 개표 원본 CSV 회차별 다운로드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 웹앱 방문자가 전체 개표 원본 tidy CSV를 선거×회차 단위 gzip 파일로 내려받게 한다.

**Architecture:** Python 분할 스크립트가 `data_processed/*.csv`를 회차별 `.csv.gz` + 매니페스트 JSON으로 `web/public`에 굽는다. 프론트엔드는 매니페스트를 fetch해 현재 회차의 정적 `.csv.gz` 링크를 통계 요약 줄에 버튼으로 노출한다.

**Tech Stack:** Python 3 (pandas, gzip 표준라이브러리), Vite + React + TypeScript.

## Global Constraints

- 분할 CSV는 `utf-8-sig`(BOM) 인코딩 — 엑셀 한글 대응. 원본 컬럼/내용 그대로, 변형 금지.
- 출력 파일명 규칙: `votes_{선거}_{회차}.csv.gz`. 선거 라벨은 `지방선거`/`총선`/`대선` (twin_votes_index.json elections 키와 동일). 회차키는 CSV `선거_회차` 컬럼값 그대로의 문자열 (지선·대선=`9`/`14`, 총선=`제22대`), 단 공백은 `_`로 치환.
- 선거종류명 매핑: CSV 파일 `국회의원선거`→`총선`, `대통령선거`→`대선`, `지방선거`→`지방선거`.
- 출력 디렉터리: `web/public`.
- 변수명은 의미를 담을 것 (단일 문자 금지) — 프로젝트 CLAUDE.md 규칙.
- 모든 회차 .gz 파일은 100MB 미만이어야 한다 (GitHub 단일 파일 제한). 실측상 최대 ~4MB이나 분할 스크립트가 초과 시 경고 로그.

---

### Task 1: 분할 핵심 함수 — 회차별 gzip CSV 굽기

**Files:**
- Create: `split_votes_csv.py`
- Test: `tests/test_split_votes_csv.py`

**Interfaces:**
- Produces:
  - `ELECTION_NAME_MAP: dict[str, str]` — `{"국회의원선거": "총선", "대통령선거": "대선", "지방선거": "지방선거"}`
  - `round_key(round_value: str) -> str` — 회차 컬럼값을 파일명용 키로 (공백→`_`)
  - `write_round_gzip(df_round: pandas.DataFrame, out_path: str) -> int` — 한 회차 DataFrame을 utf-8-sig CSV로 gzip 압축해 out_path에 쓰고, **압축 후 바이트 수**를 반환

- [ ] **Step 1: Write the failing test**

```python
# tests/test_split_votes_csv.py
"""split_votes_csv 의 회차별 gzip 굽기 검증."""
import gzip
import io

import pandas as pd

from split_votes_csv import ELECTION_NAME_MAP, round_key, write_round_gzip


def test_election_name_map():
    assert ELECTION_NAME_MAP["국회의원선거"] == "총선"
    assert ELECTION_NAME_MAP["대통령선거"] == "대선"
    assert ELECTION_NAME_MAP["지방선거"] == "지방선거"


def test_round_key_replaces_space():
    assert round_key("제22대") == "제22대"
    assert round_key("9") == "9"
    assert round_key("관내 사전") == "관내_사전"


def test_write_round_gzip_roundtrip(tmp_path):
    df = pd.DataFrame({"시도": ["서울", "부산"], "득표수": ["10", "20"]})
    out_path = tmp_path / "votes_대선_14.csv.gz"
    size = write_round_gzip(df, str(out_path))
    assert size > 0
    assert out_path.stat().st_size == size
    with gzip.open(out_path, "rt", encoding="utf-8-sig") as handle:
        restored = pd.read_csv(io.StringIO(handle.read()), dtype=str)
    assert list(restored.columns) == ["시도", "득표수"]
    assert len(restored) == 2
    assert restored.iloc[0]["시도"] == "서울"


def test_write_round_gzip_has_bom(tmp_path):
    df = pd.DataFrame({"시도": ["서울"]})
    out_path = tmp_path / "x.csv.gz"
    write_round_gzip(df, str(out_path))
    with gzip.open(out_path, "rb") as handle:
        raw = handle.read()
    assert raw.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_split_votes_csv.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'split_votes_csv'`

- [ ] **Step 3: Write minimal implementation**

```python
# split_votes_csv.py
"""data_processed/*.csv 를 선거×회차 단위 gzip CSV + 매니페스트로 분할한다.

analyze_twin_votes.py 다음 단계. 산출물은 web/public 에 떨어지며 배포에 포함된다.
"""
import gzip
import json
import os

import pandas as pd

OUT_DIR = "web/public"
MANIFEST_PATH = f"{OUT_DIR}/votes_csv_index.json"

ELECTION_NAME_MAP = {
    "국회의원선거": "총선",
    "대통령선거": "대선",
    "지방선거": "지방선거",
}

SOURCE_FILES = {
    "국회의원선거": "data_processed/국회의원선거.csv",
    "대통령선거": "data_processed/대통령선거.csv",
    "지방선거": "data_processed/지방선거.csv",
}

SIZE_LIMIT_BYTES = 100 * 1024 * 1024  # GitHub 단일 파일 한계


def round_key(round_value):
    """회차 컬럼값을 파일명용 키로. 공백은 _ 로 치환 (App.tsx fetch 규칙과 동일)."""
    return str(round_value).replace(" ", "_")


def write_round_gzip(df_round, out_path):
    """한 회차 DataFrame 을 utf-8-sig CSV 로 직렬화해 gzip 으로 out_path 에 쓴다.
    압축 후 바이트 수를 반환."""
    csv_bytes = df_round.to_csv(index=False).encode("utf-8-sig")
    with gzip.open(out_path, "wb") as handle:
        handle.write(csv_bytes)
    return os.path.getsize(out_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_split_votes_csv.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add split_votes_csv.py tests/test_split_votes_csv.py
git commit -m "feat: 회차별 gzip CSV 굽기 핵심 함수 + 테스트"
```

---

### Task 2: 분할 오케스트레이터 + 매니페스트

**Files:**
- Modify: `split_votes_csv.py` (Task 1에서 만든 파일에 추가)
- Test: `tests/test_split_votes_csv.py` (추가)

**Interfaces:**
- Consumes: `ELECTION_NAME_MAP`, `round_key`, `write_round_gzip` (Task 1)
- Produces:
  - `split_one(source_csv_name: str, source_path: str, out_dir: str) -> dict` — 한 소스 CSV를 회차별 gz로 굽고 `{회차키: {"file": str, "rows": int, "bytes": int}}` 반환
  - `main() -> None` — SOURCE_FILES 전부 처리, 매니페스트(`{선거라벨: {회차키: meta}}`)를 MANIFEST_PATH에 기록, 100MB 초과 시 경고 출력

- [ ] **Step 1: Write the failing test**

```python
# tests/test_split_votes_csv.py 에 추가
import os

from split_votes_csv import split_one


def test_split_one_groups_by_round(tmp_path):
    source = tmp_path / "대통령선거.csv"
    pd.DataFrame({
        "선거_회차": ["14", "14", "15"],
        "시도": ["서울", "부산", "서울"],
        "득표수": ["10", "20", "30"],
    }).to_csv(source, index=False)

    manifest = split_one("대통령선거", str(source), str(tmp_path))

    assert set(manifest.keys()) == {"14", "15"}
    assert manifest["14"]["file"] == "votes_대선_14.csv.gz"
    assert manifest["14"]["rows"] == 2
    assert manifest["15"]["rows"] == 1
    assert manifest["14"]["bytes"] > 0
    assert os.path.exists(os.path.join(str(tmp_path), "votes_대선_14.csv.gz"))


def test_split_one_assembly_round_label(tmp_path):
    source = tmp_path / "국회의원선거.csv"
    pd.DataFrame({
        "선거_회차": ["제22대", "제21대"],
        "시도": ["서울", "부산"],
    }).to_csv(source, index=False)

    manifest = split_one("국회의원선거", str(source), str(tmp_path))

    assert manifest["제22대"]["file"] == "votes_총선_제22대.csv.gz"
    assert manifest["제21대"]["rows"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_split_votes_csv.py::test_split_one_groups_by_round -v`
Expected: FAIL with `ImportError: cannot import name 'split_one'`

- [ ] **Step 3: Write minimal implementation**

`split_votes_csv.py` 끝에 추가:

```python
def split_one(source_csv_name, source_path, out_dir):
    """한 소스 CSV 를 회차별 gz 로 굽고 매니페스트 조각을 반환."""
    election_label = ELECTION_NAME_MAP[source_csv_name]
    df = pd.read_csv(source_path, dtype=str)
    df["선거_회차"] = df["선거_회차"].astype(str)
    manifest = {}
    for round_value, df_round in df.groupby("선거_회차"):
        key = round_key(round_value)
        file_name = f"votes_{election_label}_{key}.csv.gz"
        out_path = os.path.join(out_dir, file_name)
        size = write_round_gzip(df_round, out_path)
        if size >= SIZE_LIMIT_BYTES:
            print(f"  ⚠️ {file_name}: {size / 1024 / 1024:.1f}MB (100MB 초과!)")
        manifest[key] = {"file": file_name, "rows": int(len(df_round)), "bytes": int(size)}
    return manifest


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    full_manifest = {}
    for source_csv_name, source_path in SOURCE_FILES.items():
        if not os.path.exists(source_path):
            print(f"건너뜀 (원본 없음): {source_path}")
            continue
        election_label = ELECTION_NAME_MAP[source_csv_name]
        print(f"분할: {source_path} → {election_label}")
        full_manifest[election_label] = split_one(source_csv_name, source_path, OUT_DIR)
        for key, meta in sorted(full_manifest[election_label].items()):
            print(f"  {key}: {meta['rows']:,}행 → {meta['bytes'] / 1024 / 1024:.1f}MB")
    with open(MANIFEST_PATH, "w", encoding="utf-8") as handle:
        json.dump(full_manifest, handle, ensure_ascii=False, indent=1)
    print(f"매니페스트: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_split_votes_csv.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add split_votes_csv.py tests/test_split_votes_csv.py
git commit -m "feat: 분할 오케스트레이터 + 매니페스트 생성"
```

---

### Task 3: 실제 분할 산출물 생성 + 매니페스트/회차키 정합 검증

**Files:**
- Create (산출물, 커밋): `web/public/votes_*.csv.gz`, `web/public/votes_csv_index.json`

이 태스크는 실제 데이터로 스크립트를 돌려 산출물을 커밋하고, 매니페스트 회차키가 twin_votes_index.json 회차키와 1:1 일치하는지(버튼이 항상 매칭되도록) 확인한다.

- [ ] **Step 1: 분할 스크립트 실행**

Run: `python split_votes_csv.py`
Expected: `web/public/votes_*.csv.gz` 다수 + `web/public/votes_csv_index.json` 생성. 모든 파일 < 100MB. 최대 총선 21대 ~4MB.

- [ ] **Step 2: gz 해제 후 행 수가 원본 회차 행 수와 일치하는지 확인**

Run:
```bash
python -c "
import gzip, json, pandas as pd
manifest = json.load(open('web/public/votes_csv_index.json'))
checks = [('대통령선거','대선','19'), ('국회의원선거','총선','제22대'), ('지방선거','지방선거','7')]
for source, label, key in checks:
    full = pd.read_csv(f'data_processed/{source}.csv', dtype=str)
    full['선거_회차'] = full['선거_회차'].astype(str)
    expected = (full['선거_회차'] == key).sum()
    with gzip.open(f'web/public/{manifest[label][key][\"file\"]}', 'rt', encoding='utf-8-sig') as handle:
        actual = sum(1 for _ in handle) - 1  # 헤더 제외
    assert actual == expected == manifest[label][key]['rows'], (label, key, actual, expected)
    print(f'OK {label} {key}: {actual}행')
"
```
Expected: 세 줄 모두 `OK ...`, 단언 통과.

- [ ] **Step 3: 매니페스트 회차키 == twin_votes_index 회차키 검증**

Run:
```bash
python -c "
import json
votes = json.load(open('web/public/votes_csv_index.json'))
twin = json.load(open('web/public/twin_votes_index.json'))['elections']
for label in votes:
    twin_rounds = set(twin[label]['rounds'])
    votes_rounds = set(votes[label].keys())
    assert votes_rounds == twin_rounds, (label, votes_rounds ^ twin_rounds)
    print(f'OK {label}: {len(votes_rounds)} 회차 일치')
"
```
Expected: 세 선거 모두 회차키 집합 일치 (`OK ...`).

- [ ] **Step 4: Commit**

```bash
git add web/public/votes_*.csv.gz web/public/votes_csv_index.json
git commit -m "data: 회차별 개표 원본 CSV gzip 산출물 + 매니페스트"
```

---

### Task 4: 프론트엔드 타입 + 매니페스트 로드

**Files:**
- Modify: `web/src/types.ts`
- Modify: `web/src/App.tsx`

**Interfaces:**
- Produces (types.ts):
  - `interface VotesCsvMeta { file: string; rows: number; bytes: number }`
  - `type VotesCsvIndex = Record<string, Record<string, VotesCsvMeta>>` — `{선거: {회차: meta}}`
- Produces (App.tsx): TwinVoteViewer 에 `csvMeta={VotesCsvMeta | null}` prop 전달

- [ ] **Step 1: types.ts 에 타입 추가**

`web/src/types.ts` 끝에 추가:

```typescript
export interface VotesCsvMeta {
  file: string
  rows: number
  bytes: number
}

// {선거종류: {회차키: meta}} — split_votes_csv.py 가 생성.
export type VotesCsvIndex = Record<string, Record<string, VotesCsvMeta>>
```

- [ ] **Step 2: App.tsx 에서 매니페스트 fetch**

[web/src/App.tsx:14](web/src/App.tsx#L14) 의 useState 블록에 추가 (import 에 `VotesCsvIndex` 추가):

```typescript
  const [votesCsvIndex, setVotesCsvIndex] = useState<VotesCsvIndex | null>(null)
```

[web/src/App.tsx:28](web/src/App.tsx#L28) 의 index fetch useEffect 아래에 새 useEffect 추가:

```typescript
  useEffect(() => {
    fetch('/votes_csv_index.json')
      .then(response => (response.ok ? response.json() : null))
      .then(setVotesCsvIndex)
      .catch(() => setVotesCsvIndex(null))  // 매니페스트 없으면 버튼만 숨김
  }, [])
```

- [ ] **Step 3: TwinVoteViewer 호출에 csvMeta 전달**

[web/src/App.tsx:250](web/src/App.tsx#L250) 의 TwinVoteViewer 호출을 수정:

```typescript
        {data && selectedRound !== null && (
          <TwinVoteViewer
            data={data}
            roundLabel={currentElectionIndex?.roundLabels[selectedRound] ?? selectedRound}
            electionType={selectedElection}
            round={selectedRound}
            csvMeta={votesCsvIndex?.[selectedElection]?.[selectedRound] ?? null}
          />
        )}
```

- [ ] **Step 4: 타입체크 통과 확인** (Task 5에서 viewer prop 추가 후 함께 빌드하므로, 여기서는 단독으로 prop 미정의 에러가 날 수 있음 — Task 5 직후 빌드한다)

Run: `cd web && npx tsc -b 2>&1 | head` (csvMeta prop 미정의 에러 1건 예상 — Task 5에서 해소)
Expected: TwinVoteViewer 의 csvMeta prop 관련 에러만. 다른 에러 없음.

- [ ] **Step 5: Commit**

```bash
git add web/src/types.ts web/src/App.tsx
git commit -m "feat: votes_csv_index 매니페스트 로드 + viewer 에 csvMeta 전달"
```

---

### Task 5: 다운로드 버튼 — 통계 요약 줄

**Files:**
- Modify: `web/src/components/TwinVoteViewer.tsx`

**Interfaces:**
- Consumes: `VotesCsvMeta` (types.ts), `csvMeta` prop (App.tsx)

- [ ] **Step 1: import 와 prop 타입 추가**

[web/src/components/TwinVoteViewer.tsx:2](web/src/components/TwinVoteViewer.tsx#L2) 의 types import 에 `VotesCsvMeta` 추가:

```typescript
import type { TwinGroup, TwinData, VotesCsvMeta } from '../types'
```

[web/src/components/TwinVoteViewer.tsx:246-256](web/src/components/TwinVoteViewer.tsx#L246-L256) 의 컴포넌트 시그니처에 csvMeta 추가:

```typescript
export default function TwinVoteViewer({
  data,
  roundLabel,
  electionType,
  round,
  csvMeta,
}: {
  data: TwinData
  roundLabel: string
  electionType: string
  round: string | null
  csvMeta: VotesCsvMeta | null
}) {
```

- [ ] **Step 2: 요약 줄에 다운로드 버튼 추가**

[web/src/components/TwinVoteViewer.tsx:407-416](web/src/components/TwinVoteViewer.tsx#L407-L416) 의 요약 줄 블록을 수정. 기존 페이지 표시 `<span>` 우측에 버튼을 둔다. 우측 그룹을 묶어 정렬:

```tsx
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
          {roundLabel} · 후보쌍 {filtered.length.toLocaleString()}개 · {({ count: '반복 횟수', major: '주요 정당', cases: '사례 수', votes: '득표 큰' } as const)[sortBy]} 순
        </span>
        <div className="flex items-center gap-3">
          {totalPages > 1 && (
            <span className="text-xs font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
              {page} / {totalPages} 페이지
            </span>
          )}
          {csvMeta && (
            <a
              href={`/${csvMeta.file}`}
              download
              title="이 회차 전체 투표소 개표결과(tidy CSV)를 gzip 압축으로 내려받습니다. 해제하면 .csv 입니다."
              className="text-xs font-mono px-2.5 py-1 rounded-lg"
              style={{ backgroundColor: 'var(--color-surface-2)', color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }}
            >
              ⬇ 개표 원본 CSV ({(csvMeta.bytes / 1024 / 1024).toFixed(1)}MB, gzip)
            </a>
          )}
        </div>
      </div>
```

- [ ] **Step 3: 빌드 통과 확인**

Run: `cd web && npx tsc -b`
Expected: 에러 없음 (exit 0).

- [ ] **Step 4: 프로덕션 빌드 통과 확인**

Run: `cd web && npm run build`
Expected: `tsc -b && vite build` 성공, `web/dist` 생성.

- [ ] **Step 5: 브라우저 수동 확인**

Run: `cd web && npm run dev` 후 회차 선택.
Expected: 요약 줄 우측에 "⬇ 개표 원본 CSV (N.NMB, gzip)" 버튼 표시. 클릭 시 `votes_{선거}_{회차}.csv.gz` 다운로드. 해제 후 엑셀에서 한글 정상, 행 수가 회차 전체와 일치.

- [ ] **Step 6: Commit**

```bash
git add web/src/components/TwinVoteViewer.tsx
git commit -m "feat: 통계 요약 줄에 개표 원본 CSV 다운로드 버튼"
```

---

### Task 6: 운영 문서 갱신

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: ETL 파이프라인 절에 분할 단계 추가**

`CLAUDE.md` 의 ETL 파이프라인 코드블록([CLAUDE.md](CLAUDE.md)) 끝, `python analyze_twin_votes.py` 줄 다음에 추가:

```
python split_votes_csv.py        # CSV 3종 → web/public/votes_*.csv.gz + votes_csv_index.json (회차별 다운로드용)
```

- [ ] **Step 2: 구조 설명에 산출물 한 줄 추가**

`web/` `public/` 설명([CLAUDE.md](CLAUDE.md))에 한 줄 추가:

```
  public/            twin_votes_{선거}_{회차}.json + twin_votes_index.json + votes_{선거}_{회차}.csv.gz(개표 원본 다운로드) + votes_csv_index.json
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: 회차별 CSV 분할 단계 ETL 파이프라인에 추가"
```

---

## 검증 요약

- 전 회차 .gz < 100MB (Task 3 Step 1) ✔
- gz 해제 행 수 == 원본 회차 행 수 == 매니페스트 rows (Task 3 Step 2) ✔
- 매니페스트 회차키 == twin_votes_index 회차키 (Task 3 Step 3) ✔
- BOM 유지 (Task 1) ✔
- `npm run build` 통과 (Task 5 Step 4) ✔
- 브라우저 다운로드·해제·한글 (Task 5 Step 5) ✔
