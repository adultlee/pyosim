# 대선 ETL 구조화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `process_presidential.py` 단일 스크립트를 지방선거(`etl/local/`)와 동일한 구조 — `etl/pres/schema.py`, `etl/pres/validate.py`, `etl/pres/official_totals.py`, `etl/pres/parse_14.py`~`parse_21.py`, `etl/pres/build.py` + `tests/pres/` — 로 분리한다.

**Architecture:** 지방선거 ETL과 1:1 대응하는 모듈 구조로 이전. 각 회차 파서는 `(rows, totals)` 튜플을 반환하고, `build.py`가 순서대로 호출해 검증 후 CSV를 쓴다. `process_presidential.py`는 최종 삭제한다.

**Tech Stack:** Python 3, pandas, openpyxl, pytest

---

## 파일 구조

```
etl/pres/
  __init__.py          (빈 파일, 이미 존재)
  schema.py            신규 — COLUMNS, LEVEL_MAP, normalize_level, to_dataframe
  validate.py          신규 — 지방선거 validate.py 대선 버전 (선거종류 없음)
  official_totals.py   신규 — 시도별 후보 공식 득표 대조 기준선
  parse_14.py          신규 — 14대 파서, (rows, totals) 반환
  parse_15.py          신규 — 15대 파서
  parse_16.py          신규 — 16대 파서
  parse_17.py          신규 — 17대 파서 (파일별 처리 포함)
  parse_18.py          신규 — 18대 파서
  parse_19.py          신규 — 19대 파서
  parse_20.py          신규 — 20대 파서
  parse_21.py          신규 — 21대 파서
  build.py             신규 — 오케스트레이터

tests/pres/
  __init__.py          (빈 파일, 이미 존재)
  test_schema.py       신규
  test_validate.py     신규
  test_parse_21.py     신규 — 최신 회차 통합 검증
  test_build.py        신규
```

**대선 스키마 컬럼 (지방선거와 차이점):**
- 지방선거: `선거종류`, `선거구명` 컬럼 있음
- 대선: 두 컬럼 없음, 대신 `투표구` 컬럼 있음

```
COLUMNS = [
    "선거_회차", "선거일", "시도", "구시군", "읍면동", "투표구",
    "선거인수", "투표수", "후보자", "정당", "득표수", "무효투표수", "기권수", "level",
]
```

**totals 딕셔너리 구조 (지방선거에서 `선거종류` 제거):**
```python
{"시도": "서울특별시", "구시군": "종로구", "투표수": 4887}
```

---

## Task 1: schema.py

**Files:**
- Create: `etl/pres/schema.py`
- Test: `tests/pres/test_schema.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/pres/test_schema.py
from etl.pres.schema import COLUMNS, LEVEL_MAP, normalize_level, to_dataframe


def test_columns_order():
    assert COLUMNS == [
        "선거_회차", "선거일", "시도", "구시군", "읍면동", "투표구",
        "선거인수", "투표수", "후보자", "정당", "득표수", "무효투표수", "기권수", "level",
    ]


def test_normalize_level():
    assert normalize_level("관내사전투표") == "사전투표"
    assert normalize_level("관외사전투표") == "관외사전투표"
    assert normalize_level("거소·선상투표") == "거소선상"
    assert normalize_level("재외투표") == "재외투표"
    assert normalize_level("재외투표(공관)") == "재외투표"
    assert normalize_level("") == "당일투표"
    assert normalize_level("청운동") == "당일투표"  # 읍면동명은 당일투표


def test_to_dataframe_has_all_columns():
    rows = [{
        "선거_회차": 21, "선거일": "2025-06-03",
        "시도": "서울특별시", "구시군": "종로구", "읍면동": "청운효자동", "투표구": "",
        "선거인수": 7447, "투표수": 3155,
        "후보자": "이재명", "정당": "더불어민주당", "득표수": 1802,
        "무효투표수": 62, "기권수": None, "level": "당일투표",
    }]
    df = to_dataframe(rows)
    assert list(df.columns) == COLUMNS
    assert len(df) == 1
```

- [ ] **Step 2: 테스트 실행 — FAIL 확인**

```
pytest tests/pres/test_schema.py -v
```
Expected: `ModuleNotFoundError: No module named 'etl.pres.schema'`

- [ ] **Step 3: schema.py 작성**

```python
# etl/pres/schema.py
"""tidy row 스키마 정의."""

import pandas as pd

COLUMNS = [
    "선거_회차", "선거일", "시도", "구시군", "읍면동", "투표구",
    "선거인수", "투표수", "후보자", "정당", "득표수", "무효투표수", "기권수", "level",
]

LEVEL_MAP = {
    "관내사전투표": "사전투표",
    "관외사전투표": "관외사전투표",
    "거소·선상투표": "거소선상",
    "거소선상투표": "거소선상",
    "재외투표": "재외투표",
    "재외투표(공관)": "재외투표",
}


def normalize_level(raw):
    """원본 투표구명 값을 표준 level로 변환. 미매핑(읍면동명 등)은 당일투표."""
    key = str(raw or "").strip()
    return LEVEL_MAP.get(key, "당일투표")


def to_dataframe(rows):
    """tidy row dict 리스트를 COLUMNS 순서의 DataFrame으로."""
    return pd.DataFrame(rows, columns=COLUMNS)
```

- [ ] **Step 4: 테스트 실행 — PASS 확인**

```
pytest tests/pres/test_schema.py -v
```
Expected: 모두 PASS

- [ ] **Step 5: 커밋**

```bash
git add etl/pres/schema.py tests/pres/test_schema.py
git commit -m "feat(pres): schema.py — COLUMNS, LEVEL_MAP, normalize_level"
```

---

## Task 2: validate.py

**Files:**
- Create: `etl/pres/validate.py`
- Test: `tests/pres/test_validate.py`

대선은 `선거종류` 컬럼이 없다. `check_sido_candidate_consistency`는 제거. `check_official_totals`는 시도별 후보 득표 합 검증으로 유지.

- [ ] **Step 1: 테스트 작성**

```python
# tests/pres/test_validate.py
import pandas as pd
from etl.pres.schema import to_dataframe
from etl.pres.validate import (
    check_no_duplicate_rows,
    check_value_ranges,
    check_totals_match,
    check_official_totals,
    run_all_checks,
)


def _row(**kwargs):
    base = {
        "선거_회차": 21, "선거일": "2025-06-03",
        "시도": "서울특별시", "구시군": "종로구", "읍면동": "청운효자동", "투표구": "",
        "선거인수": 7447, "투표수": 3155,
        "후보자": "이재명", "정당": "더불어민주당", "득표수": 1802,
        "무효투표수": 62, "기권수": None, "level": "당일투표",
    }
    base.update(kwargs)
    return base


def test_no_duplicate_rows_passes():
    df = to_dataframe([_row(후보자="이재명"), _row(후보자="김문수", 득표수=1100)])
    assert check_no_duplicate_rows(df) == []


def test_no_duplicate_rows_flags_repeat():
    df = to_dataframe([_row(후보자="이재명"), _row(후보자="이재명")])
    errors = check_no_duplicate_rows(df)
    assert len(errors) == 1
    assert errors[0][0] == "duplicate_rows"


def test_value_ranges_passes():
    df = to_dataframe([_row(득표수=1802, 투표수=3155, 선거인수=7447)])
    assert check_value_ranges(df) == []


def test_value_ranges_flags_votes_exceed_turnout():
    df = to_dataframe([_row(득표수=9999, 투표수=3155)])
    errors = check_value_ranges(df)
    assert len(errors) == 1
    assert errors[0][0] == "value_range"


def test_value_ranges_ignores_nan_electorate():
    df = to_dataframe([_row(득표수=10, 투표수=20, 선거인수=None)])
    assert check_value_ranges(df) == []


def test_totals_match_passes():
    rows = [
        _row(읍면동="청운효자동", level="당일투표", 투표수=3155, 후보자="이재명", 득표수=1802),
        _row(읍면동="청운효자동", level="당일투표", 투표수=3155, 후보자="김문수", 득표수=1246),
        _row(읍면동="청운효자동", level="사전투표", 투표수=1732, 후보자="이재명", 득표수=900),
        _row(읍면동="청운효자동", level="사전투표", 투표수=1732, 후보자="김문수", 득표수=800),
    ]
    df = to_dataframe(rows)
    totals = [{"시도": "서울특별시", "구시군": "종로구", "투표수": 4887}]
    assert check_totals_match(df, totals) == []


def test_totals_match_flags_mismatch():
    rows = [_row(읍면동="청운효자동", level="당일투표", 투표수=3155)]
    df = to_dataframe(rows)
    totals = [{"시도": "서울특별시", "구시군": "종로구", "투표수": 9999}]
    errors = check_totals_match(df, totals)
    assert len(errors) == 1
    assert errors[0][0] == "totals_mismatch"


def test_official_totals_passes_when_match():
    rows = [
        _row(시도="서울특별시", 후보자="이재명", 득표수=2000000, level="당일투표"),
        _row(시도="서울특별시", 후보자="이재명", 득표수=500000, level="사전투표"),
    ]
    df = to_dataframe(rows)
    official = {(21, "서울특별시"): ("이재명", 2500000)}
    assert check_official_totals(df, official) == []


def test_official_totals_flags_mismatch():
    rows = [_row(시도="서울특별시", 후보자="이재명", 득표수=5)]
    df = to_dataframe(rows)
    official = {(21, "서울특별시"): ("이재명", 2500000)}
    errors = check_official_totals(df, official)
    assert any(name == "official_mismatch" for name, _ in errors)


def test_run_all_checks_aggregates():
    df = to_dataframe([_row(후보자="이재명"), _row(후보자="이재명")])
    errors = run_all_checks(df, totals=[])
    names = {name for name, _ in errors}
    assert "duplicate_rows" in names
```

- [ ] **Step 2: 테스트 실행 — FAIL 확인**

```
pytest tests/pres/test_validate.py -v
```
Expected: `ModuleNotFoundError: No module named 'etl.pres.validate'`

- [ ] **Step 3: validate.py 작성**

```python
# etl/pres/validate.py
"""검증 게이트. 파서가 원본을 그대로 옮겼는지 검사한다."""

import pandas as pd

KEY_COLS = ["선거_회차", "시도", "구시군", "읍면동", "투표구", "level", "후보자", "정당"]


def check_no_duplicate_rows(df):
    dup_mask = df.duplicated(subset=KEY_COLS, keep=False)
    if not dup_mask.any():
        return []
    errors = []
    dups = df[dup_mask].groupby(KEY_COLS, dropna=False).size()
    for key, count in dups.items():
        errors.append(("duplicate_rows", f"{key} → {count}건 중복"))
    return errors


def check_value_ranges(df):
    errors = []
    votes = df["득표수"].fillna(0)
    turnout = df["투표수"].fillna(0)
    over_votes = df[votes > turnout]
    for _, row in over_votes.iterrows():
        errors.append((
            "value_range",
            f"{row['시도']} {row['구시군']} {row['읍면동']} "
            f"{row['후보자']} 득표 {row['득표수']} > 투표수 {row['투표수']}",
        ))
    electorate = pd.to_numeric(df["선거인수"], errors="coerce")
    over_turnout = df[electorate.notna() & (turnout > electorate)]
    for _, row in over_turnout.iterrows():
        errors.append((
            "value_range",
            f"{row['시도']} {row['구시군']} {row['읍면동']} "
            f"{row['후보자']} 투표수 {row['투표수']} > 선거인수 {row['선거인수']}",
        ))
    return errors


def _turnout_per_gugun(df, 시도, 구시군):
    """구시군 세분 단위 투표수 합 (후보 행 중복 제거)."""
    sub = df[(df["시도"] == 시도) & (df["구시군"] == 구시군)]
    per = sub.drop_duplicates(subset=["읍면동", "투표구", "level"])
    return int(per["투표수"].fillna(0).sum())


def check_totals_match(df, totals):
    errors = []
    for total in totals:
        actual = _turnout_per_gugun(df, total["시도"], total["구시군"])
        expected = int(total["투표수"])
        if actual != expected:
            errors.append((
                "totals_mismatch",
                f"{total['시도']} {total['구시군']}: "
                f"세분합 {actual} != 합계행 {expected} (차 {actual - expected})",
            ))
    return errors


def check_official_totals(df, official_top):
    """(회차, 시도) → (후보자, 득표수) 공식 득표 대조."""
    errors = []
    for (회차, 시도), (cand, votes) in official_top.items():
        sub = df[
            (df["선거_회차"] == 회차)
            & (df["시도"] == 시도)
            & (df["후보자"] == cand)
        ]
        if sub.empty:
            continue
        actual = int(sub["득표수"].fillna(0).sum())
        if actual != votes:
            errors.append((
                "official_mismatch",
                f"{회차}대 {시도} {cand}: 집계 {actual} != 공식 {votes} (차 {actual - votes})",
            ))
    return errors


def run_all_checks(df, totals, official_top=None):
    errors = []
    errors += check_no_duplicate_rows(df)
    errors += check_value_ranges(df)
    errors += check_totals_match(df, totals)
    if official_top:
        errors += check_official_totals(df, official_top)
    return errors
```

- [ ] **Step 4: 테스트 실행 — PASS 확인**

```
pytest tests/pres/test_validate.py -v
```
Expected: 모두 PASS

- [ ] **Step 5: 커밋**

```bash
git add etl/pres/validate.py tests/pres/test_validate.py
git commit -m "feat(pres): validate.py — duplicate/range/totals/official 검증 게이트"
```

---

## Task 3: official_totals.py

**Files:**
- Create: `etl/pres/official_totals.py`

공식 득표 기준선. 위키백과·선관위 발표 기준 주요 시도 1위 득표. 키 형식: `(회차, 시도)`.

- [ ] **Step 1: official_totals.py 작성**

```python
# etl/pres/official_totals.py
"""선관위 공식 시도별 1위 득표 (외부 대조 기준선).

출처: 위키백과 각 대통령선거 결과 + 선관위 개표자료 합계 교차검증.
"""

# {(회차, 시도): (1위후보, 1위득표)}
OFFICIAL_TOP = {
    # 20대(2022) — 위키백과 '제20대 대통령선거'
    (20, "서울특별시"): ("윤석열", 2670522),
    (20, "경기도"):   ("이재명", 3491241),
    (20, "부산광역시"): ("윤석열", 1068060),
    # 19대(2017) — 위키백과 '제19대 대통령선거'
    (19, "서울특별시"): ("문재인", 2743522),
    (19, "경기도"):   ("문재인", 3709602),
    # 21대(2025) — 선관위 공고 기준 (확정 후 교차검증 필요, 임시값)
    # 실제 값은 process_presidential.py 실행 후 집계값으로 교체할 것
}
```

> **주의:** `OFFICIAL_TOP`의 21대 값은 현재 임시(placeholder). 파서를 실행해 실제 집계를 확인한 뒤 채워야 한다. Task 8(build.py 통합)에서 최종 확정.

- [ ] **Step 2: 커밋**

```bash
git add etl/pres/official_totals.py
git commit -m "feat(pres): official_totals.py — 대선 시도별 공식 1위 득표 기준선"
```

---

## Task 4: parse_14.py ~ parse_18.py (14~18대 파서)

**Files:**
- Create: `etl/pres/parse_14.py`, `parse_15.py`, `parse_16.py`, `parse_17.py`, `parse_18.py`

각 파서는 `(rows: list[dict], totals: list[dict])` 를 반환한다. 로직은 `process_presidential.py`의 `process_14()` ~ `process_18()` 에서 그대로 이식. `totals`는 원본 합계행을 보존해 `check_totals_match`에 전달하는 딕셔너리 리스트.

**공통 유틸은 각 파서가 직접 포함한다 (DRY 위반이지만 파서 파일 간 의존 없애기 위해).** `clean_num`, `parse_candidate_col`, `get_level` 은 각 파일에 복사하거나 `etl/pres/schema.py`의 `normalize_level` 을 사용한다.

### parse_14.py

- [ ] **Step 1: parse_14.py 작성**

`process_presidential.py:211~265` 를 이식. totals는 합계행(읍면동='합계')에서 추출.

```python
# etl/pres/parse_14.py
"""14대(1992) 대통령선거 파서."""

import pandas as pd
import numpy as np

from etl.pres.schema import normalize_level

RAW_PATH = "data_raw/대통령선거 개표결과(제14대~제18대)/제14대 대통령선거 개표자료.xls"
ROUND = 14


def _clean_num(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )


def _parse_cand_col(col_name):
    col_name = col_name.strip()
    if "\n" in col_name:
        parts = col_name.split("\n", 1)
        return parts[0].strip(), parts[1].strip()
    tokens = col_name.split()
    if len(tokens) >= 2:
        return " ".join(tokens[:-1]), tokens[-1]
    return col_name, ""


def parse_14(path=RAW_PATH):
    raw = pd.read_excel(path, header=None)
    parties = raw.iloc[2, 7:15].tolist()
    names   = raw.iloc[3, 7:15].tolist()
    cand_labels = [f"{p}\n{n}" for p, n in zip(parties, names)]

    data = raw.iloc[4:].copy()
    data.columns = [
        "시도", "구시군", "읍면동",
        "선거인수", "부재자수", "투표자수", "부재자투표자수",
        *cand_labels, "계", "무효투표수", "기권수",
    ]
    data["시도"] = data["시도"].ffill()
    data["구시군"] = data["구시군"].ffill()

    # 합계행 먼저 totals로 수집
    total_mask = data["읍면동"].astype(str).str.contains("합계", na=False)
    totals_raw = data[total_mask].copy()
    for col in ["투표자수"]:
        totals_raw[col] = _clean_num(totals_raw[col])
    totals = [
        {"시도": row["시도"], "구시군": row["구시군"], "투표수": row["투표자수"]}
        for _, row in totals_raw.iterrows()
        if pd.notna(row["구시군"]) and "합계" not in str(row["구시군"])
        and "전국" not in str(row["시도"])
    ]

    remove_mask = data["읍면동"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= data["구시군"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= data["시도"].astype(str).str.contains("전국", na=False)
    data = data[~remove_mask].copy()

    num_cols = ["선거인수", "투표자수", "무효투표수", "기권수"] + cand_labels
    for col in num_cols:
        if col in data.columns:
            data[col] = _clean_num(data[col])

    rows = []
    for _, row in data.iterrows():
        for label in cand_labels:
            party, name = _parse_cand_col(label)
            rows.append({
                "선거_회차": ROUND,
                "선거일": "1992-12-18",
                "시도": row["시도"],
                "구시군": row["구시군"],
                "읍면동": row["읍면동"],
                "투표구": "",
                "선거인수": row["선거인수"],
                "투표수": row["투표자수"],
                "후보자": name,
                "정당": party,
                "득표수": row[label],
                "무효투표수": row["무효투표수"],
                "기권수": row["기권수"],
                "level": normalize_level(row["읍면동"]),
            })
    return rows, totals
```

- [ ] **Step 2: 파서 실행 확인 (단위 테스트 대신 빠른 smoke test)**

```python
# python -c 로 실행
python -c "
import sys; sys.path.insert(0, '.')
from etl.pres.parse_14 import parse_14
rows, totals = parse_14()
print(f'rows: {len(rows)}, totals: {len(totals)}')
assert len(rows) > 20000
assert len(totals) > 0
print('OK')
"
```
Expected: `rows: 29264, totals: ...`, `OK`

- [ ] **Step 3: parse_15.py 작성**

`process_presidential.py:271~320` 이식. 구조 동일, ROUND=15.

```python
# etl/pres/parse_15.py
"""15대(1997) 대통령선거 파서."""

import pandas as pd
from etl.pres.schema import normalize_level

RAW_PATH = "data_raw/대통령선거 개표결과(제14대~제18대)/제15대 대통령선거 개표자료.xls"
ROUND = 15


def _clean_num(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )


def _parse_cand_col(col_name):
    col_name = col_name.strip()
    if "\n" in col_name:
        parts = col_name.split("\n", 1)
        return parts[0].strip(), parts[1].strip()
    tokens = col_name.split()
    if len(tokens) >= 2:
        return " ".join(tokens[:-1]), tokens[-1]
    return col_name, ""


def parse_15(path=RAW_PATH):
    raw = pd.read_excel(path, header=None)
    parties = raw.iloc[2, 7:14].tolist()
    names   = raw.iloc[3, 7:14].tolist()
    cand_labels = [f"{p}\n{n}" for p, n in zip(parties, names)]

    data = raw.iloc[4:].copy()
    data.columns = [
        "시도", "구시군", "읍면동",
        "선거인수", "부재자수", "투표자수", "부재자투표자수",
        *cand_labels, "계", "무효투표수", "기권수",
    ]
    data["시도"] = data["시도"].ffill()
    data["구시군"] = data["구시군"].ffill()

    total_mask = data["읍면동"].astype(str).str.contains("합계", na=False)
    totals_raw = data[total_mask].copy()
    totals_raw["투표자수"] = _clean_num(totals_raw["투표자수"])
    totals = [
        {"시도": row["시도"], "구시군": row["구시군"], "투표수": row["투표자수"]}
        for _, row in totals_raw.iterrows()
        if pd.notna(row["구시군"]) and "합계" not in str(row["구시군"])
        and "전국" not in str(row["시도"])
    ]

    remove_mask = data["읍면동"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= data["구시군"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= data["시도"].astype(str).str.contains("전국", na=False)
    data = data[~remove_mask].copy()

    num_cols = ["선거인수", "투표자수", "무효투표수", "기권수"] + cand_labels
    for col in num_cols:
        if col in data.columns:
            data[col] = _clean_num(data[col])

    rows = []
    for _, row in data.iterrows():
        for label in cand_labels:
            party, name = _parse_cand_col(label)
            rows.append({
                "선거_회차": ROUND,
                "선거일": "1997-12-18",
                "시도": row["시도"],
                "구시군": row["구시군"],
                "읍면동": row["읍면동"],
                "투표구": "",
                "선거인수": row["선거인수"],
                "투표수": row["투표자수"],
                "후보자": name,
                "정당": party,
                "득표수": row[label],
                "무효투표수": row["무효투표수"],
                "기권수": row["기권수"],
                "level": normalize_level(row["읍면동"]),
            })
    return rows, totals
```

- [ ] **Step 4: parse_16.py 작성**

`process_presidential.py:327~390` 이식. 16대는 `위원회명` 컬럼에서 시도/구시군 추출. `GUGUN_SIDO_MAP`은 18대 xls에서 빌드하는 로직 포함.

```python
# etl/pres/parse_16.py
"""16대(2002) 대통령선거 파서."""

import re
import pandas as pd
from etl.pres.schema import normalize_level

RAW_PATH = "data_raw/대통령선거 개표결과(제14대~제18대)/제16대 대통령선거 개표자료.xls"
RAW_18_PATH = "data_raw/대통령선거 개표결과(제14대~제18대)/제18대 대통령선거 개표자료.xls"
ROUND = 16

PARTY_MAP = {
    "이회창": "한나라당",
    "노무현": "새천년민주당",
    "이한동": "하나로국민연합",
    "권영길": "민주노동당",
    "김영규": "사회당",
    "김길수": "무소속",
}

GUGUN_SIDO_EXTRA = {
    "양주군": "경기도", "고양시일산구": "경기도", "용인시": "경기도",
    "포천군": "경기도", "천안시": "충청남도", "연기군": "충청남도",
    "당진군": "충청남도", "창원시": "경상남도", "마산시": "경상남도",
    "진해시": "경상남도", "북제주군": "제주특별자치도", "남제주군": "제주특별자치도",
}

SIDO_SHORT = {
    "서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시",
    "인천": "인천광역시", "광주": "광주광역시", "대전": "대전광역시",
    "울산": "울산광역시", "경기": "경기도", "강원": "강원도",
    "충북": "충청북도", "충남": "충청남도", "전북": "전라북도",
    "전남": "전라남도", "경북": "경상북도", "경남": "경상남도",
    "제주": "제주특별자치도",
}


def _clean_num(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )


def _build_gugun_sido_map():
    raw = pd.read_excel(RAW_18_PATH, header=None)
    data = raw.iloc[5:].copy()
    data.columns = ["_", "시도", "구시군"] + list(range(data.shape[1] - 3))
    data["시도"] = data["시도"].ffill()
    g = (
        data[["시도", "구시군"]]
        .dropna(subset=["구시군"])
        .pipe(lambda d: d[~d["구시군"].astype(str).str.contains("합계|소계", na=False)])
        .drop_duplicates()
    )
    mapping = dict(zip(g["구시군"].str.strip(), g["시도"].str.strip()))
    mapping.update(GUGUN_SIDO_EXTRA)
    return mapping


_GUGUN_SIDO_MAP = None


def _get_gugun_sido_map():
    global _GUGUN_SIDO_MAP
    if _GUGUN_SIDO_MAP is None:
        _GUGUN_SIDO_MAP = _build_gugun_sido_map()
    return _GUGUN_SIDO_MAP


def _lookup_sido(committee):
    gugun_sido = _get_gugun_sido_map()
    raw = committee.strip("[] ")
    match = re.search(r"\(([^)]+)\)", raw)
    if match:
        return SIDO_SHORT.get(match.group(1), match.group(1))
    gugun_name = raw
    return gugun_sido.get(gugun_name, "")


def parse_16(path=RAW_PATH):
    cand_cols = ["이회창", "노무현", "이한동", "권영길", "김영규", "김길수"]
    raw = pd.read_excel(path, header=0)

    raw["읍면동명"] = raw["읍면동명"].ffill()

    total_mask = raw["읍면동명"].astype(str).str.contains("합계", na=False)
    totals_raw = raw[total_mask].copy()
    totals_raw["투표수"] = _clean_num(totals_raw["투표수"])
    totals = []
    for _, row in totals_raw.iterrows():
        committee = str(row["위원회명"])
        sido = _lookup_sido(committee)
        gugun_raw = committee.strip("[] ")
        gugun = re.sub(r"\([^)]*\)", "", gugun_raw).strip()
        if sido and "합계" not in gugun:
            totals.append({"시도": sido, "구시군": gugun, "투표수": row["투표수"]})

    remove_mask = raw["읍면동명"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= raw["투표구명"].astype(str).str.contains("소계", na=False)
    data = raw[~remove_mask].copy()

    for col in ["선거인수", "투표수", "무표투표수", "기권수"] + cand_cols:
        if col in data.columns:
            data[col] = _clean_num(data[col])

    rows = []
    for _, row in data.iterrows():
        committee = str(row["위원회명"])
        sido = _lookup_sido(committee)
        gugun_raw = committee.strip("[] ")
        gugun = re.sub(r"\([^)]*\)", "", gugun_raw).strip()
        eupmyeong = str(row["읍면동명"]) if pd.notna(row["읍면동명"]) else ""
        tpgu = str(row["투표구명"]) if pd.notna(row["투표구명"]) else ""

        for cand in cand_cols:
            rows.append({
                "선거_회차": ROUND,
                "선거일": "2002-12-19",
                "시도": sido,
                "구시군": gugun,
                "읍면동": eupmyeong,
                "투표구": tpgu,
                "선거인수": row.get("선거인수"),
                "투표수": row.get("투표수"),
                "후보자": cand,
                "정당": PARTY_MAP.get(cand, ""),
                "득표수": row.get(cand),
                "무효투표수": row.get("무표투표수"),
                "기권수": row.get("기권수"),
                "level": normalize_level(tpgu or eupmyeong),
            })
    return rows, totals
```

- [ ] **Step 5: parse_17.py 작성**

`process_presidential.py:395~497` 이식. 17대는 시도별 파일 폴더 구조.

```python
# etl/pres/parse_17.py
"""17대(2007) 대통령선거 파서. 시도별 xls 파일 처리."""

import os
import pandas as pd
from etl.pres.schema import normalize_level

RAW_DIR = "data_raw/대통령선거 개표결과(제14대~제18대)/제17대 대통령선거 개표자료"
ROUND = 17

SIDO_FROM_FILENAME = {
    "서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시",
    "인천": "인천광역시", "광주": "광주광역시", "대전": "대전광역시",
    "울산": "울산광역시", "경기": "경기도", "강원": "강원도",
    "충북": "충청북도", "충남": "충청남도", "전북": "전라북도",
    "전남": "전라남도", "경북": "경상북도", "경남": "경상남도",
    "제주": "제주특별자치도",
}


def _clean_num(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )


def _parse_cand_col(col_name):
    col_name = col_name.strip()
    if "\n" in col_name:
        parts = col_name.split("\n", 1)
        return parts[0].strip(), parts[1].strip()
    tokens = col_name.split()
    if len(tokens) >= 2:
        return " ".join(tokens[:-1]), tokens[-1]
    return col_name, ""


def _parse_file(filepath, sido_name):
    raw = pd.read_excel(filepath, header=None)
    parties = raw.iloc[2, 6:].tolist()
    names   = raw.iloc[3, 6:].tolist()
    cand_labels = []
    for party, name in zip(parties, names):
        p, n = str(party).strip(), str(name).strip()
        if p in ("nan", "") or n in ("nan", "계", "무효투표수", "기권수", ""):
            continue
        cand_labels.append(f"{p}\n{n}")

    # 실제 후보 컬럼 수 파악 (계, 무효투표수, 기권수 전까지)
    header_row = raw.iloc[3, :].tolist()
    end_markers = {"계", "무효투표수", "기권수"}
    cand_end_idx = 6
    for idx, val in enumerate(header_row[6:], start=6):
        if str(val).strip() in end_markers:
            cand_end_idx = idx
            break

    cand_labels = [f"{str(raw.iloc[2, i]).strip()}\n{str(raw.iloc[3, i]).strip()}"
                   for i in range(6, cand_end_idx)]

    data = raw.iloc[4:].copy()
    trailing = len(data.columns) - 6 - len(cand_labels)
    data.columns = [
        "구시군", "읍면동", "투표구",
        "선거인수", "투표수", "부재자투표수",
        *cand_labels,
        *[f"_t{i}" for i in range(trailing)],
    ]
    data["구시군"] = data["구시군"].ffill()
    data["읍면동"] = data["읍면동"].ffill()

    total_mask = data["투표구"].astype(str).str.contains("합계", na=False)
    totals_raw = data[total_mask].copy()
    totals_raw["투표수"] = _clean_num(totals_raw["투표수"])
    totals = [
        {"시도": sido_name, "구시군": row["구시군"], "투표수": row["투표수"]}
        for _, row in totals_raw.iterrows()
        if pd.notna(row["구시군"]) and "합계" not in str(row["구시군"])
    ]

    remove_mask = data["투표구"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= data["읍면동"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= data["구시군"].astype(str).str.contains("합계|소계", na=False)
    data = data[~remove_mask].copy()

    for col in ["선거인수", "투표수"] + cand_labels:
        if col in data.columns:
            data[col] = _clean_num(data[col])

    rows = []
    for _, row in data.iterrows():
        tpgu = str(row["투표구"]) if pd.notna(row["투표구"]) else ""
        for label in cand_labels:
            party, name = _parse_cand_col(label)
            rows.append({
                "선거_회차": ROUND,
                "선거일": "2007-12-19",
                "시도": sido_name,
                "구시군": row["구시군"],
                "읍면동": row["읍면동"],
                "투표구": tpgu,
                "선거인수": row["선거인수"],
                "투표수": row["투표수"],
                "후보자": name,
                "정당": party,
                "득표수": row[label],
                "무효투표수": None,
                "기권수": None,
                "level": normalize_level(tpgu or str(row["읍면동"])),
            })
    return rows, totals


def parse_17(raw_dir=RAW_DIR):
    all_rows, all_totals = [], []
    for filename in sorted(os.listdir(raw_dir)):
        if not filename.endswith(".xls"):
            continue
        sido_key = filename.replace("제17대 대통령선거 개표자료(", "").split(")")[0]
        sido_name = SIDO_FROM_FILENAME.get(sido_key, "")
        if not sido_name:
            continue
        filepath = os.path.join(raw_dir, filename)
        rows, totals = _parse_file(filepath, sido_name)
        all_rows.extend(rows)
        all_totals.extend(totals)
    return all_rows, all_totals
```

- [ ] **Step 6: parse_18.py 작성**

`process_presidential.py:503~556` 이식.

```python
# etl/pres/parse_18.py
"""18대(2012) 대통령선거 파서."""

import pandas as pd
from etl.pres.schema import normalize_level

RAW_PATH = "data_raw/대통령선거 개표결과(제14대~제18대)/제18대 대통령선거 개표자료.xls"
ROUND = 18


def _clean_num(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )


def _parse_cand_col(col_name):
    col_name = col_name.strip()
    if "\n" in col_name:
        parts = col_name.split("\n", 1)
        return parts[0].strip(), parts[1].strip()
    tokens = col_name.split()
    if len(tokens) >= 2:
        return " ".join(tokens[:-1]), tokens[-1]
    return col_name, ""


def parse_18(path=RAW_PATH):
    raw = pd.read_excel(path, header=None)
    parties = raw.iloc[3, 3:].tolist()
    names   = raw.iloc[4, 3:].tolist()
    cand_labels = []
    for party, name in zip(parties, names):
        p, n = str(party).strip(), str(name).strip()
        if p in ("nan", "") or n in ("nan", "계", "무효투표수", "기권수", ""):
            break
        cand_labels.append(f"{p}\n{n}")

    data = raw.iloc[5:].copy()
    trailing = len(data.columns) - 3 - len(cand_labels)
    data.columns = [
        "시도", "구시군", "읍면동",
        *cand_labels,
        *[f"_t{i}" for i in range(trailing)],
    ]
    data["시도"] = data["시도"].ffill()
    data["구시군"] = data["구시군"].ffill()

    total_mask = data["읍면동"].astype(str).str.contains("합계", na=False)
    totals_raw = data[total_mask].copy()
    # 18대는 투표수 컬럼이 없고 득표 합으로 대체 불가 → totals 없음
    totals = []

    remove_mask = data["읍면동"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= data["구시군"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= data["시도"].astype(str).str.contains("전국", na=False)
    data = data[~remove_mask].copy()

    for col in cand_labels:
        if col in data.columns:
            data[col] = _clean_num(data[col])

    rows = []
    for _, row in data.iterrows():
        for label in cand_labels:
            party, name = _parse_cand_col(label)
            rows.append({
                "선거_회차": ROUND,
                "선거일": "2012-12-19",
                "시도": row["시도"],
                "구시군": row["구시군"],
                "읍면동": row["읍면동"],
                "투표구": "",
                "선거인수": None,
                "투표수": None,
                "후보자": name,
                "정당": party,
                "득표수": row[label],
                "무효투표수": None,
                "기권수": None,
                "level": normalize_level(row["읍면동"]),
            })
    return rows, totals
```

> **주의:** 18대 원본에 투표수/선거인수 컬럼이 없다. `투표수`=None, `선거인수`=None으로 채운다. `check_totals_match`는 totals=[]이므로 자동으로 건너뜀.

- [ ] **Step 7: 14~18대 smoke test 일괄 실행**

```bash
python -c "
import sys; sys.path.insert(0, '.')
from etl.pres.parse_14 import parse_14
from etl.pres.parse_15 import parse_15
from etl.pres.parse_16 import parse_16
from etl.pres.parse_17 import parse_17
from etl.pres.parse_18 import parse_18
for fn, name, expected in [
    (parse_14, '14대', 29000),
    (parse_15, '15대', 26000),
    (parse_16, '16대', 82000),
    (parse_17, '17대', 134000),
    (parse_18, '18대', 84000),
]:
    rows, totals = fn()
    print(f'{name}: {len(rows)}행, totals={len(totals)}')
    assert len(rows) >= expected, f'{name} 행수 부족'
print('ALL OK')
"
```

- [ ] **Step 8: 커밋**

```bash
git add etl/pres/parse_14.py etl/pres/parse_15.py etl/pres/parse_16.py etl/pres/parse_17.py etl/pres/parse_18.py
git commit -m "feat(pres): parse_14~18 — 14~18대 파서 모듈화"
```

---

## Task 5: parse_19.py, parse_20.py, parse_21.py

**Files:**
- Create: `etl/pres/parse_19.py`, `parse_20.py`, `parse_21.py`

- [ ] **Step 1: parse_19.py 작성**

`process_presidential.py:620~676` 이식.

```python
# etl/pres/parse_19.py
"""19대(2017) 대통령선거 파서."""

import pandas as pd
from etl.pres.schema import normalize_level

RAW_PATH = "data_raw/대통령선거 개표결과(제14대~제18대)/제19대 대통령선거 개표자료.xlsx"
ROUND = 19


def _clean_num(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )


def _parse_cand_col(col_name):
    col_name = col_name.strip()
    if "\n" in col_name:
        parts = col_name.split("\n", 1)
        return parts[0].strip(), parts[1].strip()
    tokens = col_name.split()
    if len(tokens) >= 2:
        return " ".join(tokens[:-1]), tokens[-1]
    return col_name, ""


def parse_19(path=RAW_PATH):
    raw = pd.read_excel(path, sheet_name="19대선", header=None)

    cand_labels = []
    for val in raw.iloc[1, 6:].tolist():
        v = str(val).strip()
        if v in ("nan", "계", "NaN", ""):
            continue
        cand_labels.append(v)

    data = raw.iloc[2:].copy()
    data.columns = ["시도", "구시군", "읍면동", "투표구", "선거인수", "투표수",
                    *cand_labels, *["_extra"] * (len(data.columns) - 6 - len(cand_labels))]
    data = data[["시도", "구시군", "읍면동", "투표구", "선거인수", "투표수"] + cand_labels].copy()

    data["시도"] = data["시도"].ffill()
    data["구시군"] = data["구시군"].ffill()
    data["읍면동"] = data["읍면동"].ffill()

    total_mask = data["읍면동"].astype(str).str.contains("합계", na=False)
    totals_raw = data[total_mask].copy()
    totals_raw["투표수"] = _clean_num(totals_raw["투표수"])
    totals = [
        {"시도": row["시도"], "구시군": row["구시군"], "투표수": row["투표수"]}
        for _, row in totals_raw.iterrows()
        if pd.notna(row["구시군"]) and "합계" not in str(row["구시군"])
        and "전국" not in str(row["시도"])
    ]

    remove_mask = data["읍면동"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= data["구시군"].astype(str).str.contains("합계|소계|합계\\(특별시\\)|합계\\(광역시\\)|합계\\(도\\)", na=False)
    remove_mask |= data["시도"].astype(str).str.contains("전국", na=False)
    remove_mask |= data["투표구"].astype(str).str.contains("소계", na=False)
    data = data[~remove_mask].copy()

    for col in ["선거인수", "투표수"] + cand_labels:
        if col in data.columns:
            data[col] = _clean_num(data[col])

    rows = []
    for _, row in data.iterrows():
        tpgu = str(row["투표구"]) if pd.notna(row["투표구"]) else ""
        for label in cand_labels:
            party, name = _parse_cand_col(label)
            rows.append({
                "선거_회차": ROUND,
                "선거일": "2017-05-09",
                "시도": row["시도"],
                "구시군": row["구시군"],
                "읍면동": row["읍면동"],
                "투표구": tpgu,
                "선거인수": row["선거인수"],
                "투표수": row["투표수"],
                "후보자": name,
                "정당": party,
                "득표수": row[label],
                "무효투표수": None,
                "기권수": None,
                "level": normalize_level(tpgu),
            })
    return rows, totals
```

- [ ] **Step 2: parse_20.py 작성**

`process_presidential.py:562~613` 이식.

```python
# etl/pres/parse_20.py
"""20대(2022) 대통령선거 파서."""

import pandas as pd
from etl.pres.schema import normalize_level

RAW_PATH = "data_raw/개표단위별_개표결과_대통령선거_전체.xlsx"
ROUND = 20


def _clean_num(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )


def _parse_cand_col(col_name):
    col_name = col_name.strip()
    if "\n" in col_name:
        parts = col_name.split("\n", 1)
        return parts[0].strip(), parts[1].strip()
    tokens = col_name.split()
    if len(tokens) >= 2:
        return " ".join(tokens[:-1]), tokens[-1]
    return col_name, ""


def parse_20(path=RAW_PATH):
    raw = pd.read_excel(path, sheet_name="Data", header=0)

    fixed_cols = ["시도", "구시군", "읍면동명", "투표구명", "선거인수", "투표수"]
    all_cols = raw.columns.tolist()
    cand_end = all_cols.index("계")
    cand_labels = all_cols[len(fixed_cols):cand_end]

    raw["시도"] = raw["시도"].ffill()
    raw["구시군"] = raw["구시군"].ffill()
    raw["읍면동명"] = raw["읍면동명"].ffill()

    total_mask = raw["읍면동명"].astype(str).str.contains("합계", na=False)
    totals_raw = raw[total_mask].copy()
    totals_raw["투표수"] = _clean_num(totals_raw["투표수"])
    totals = [
        {"시도": row["시도"], "구시군": row["구시군"], "투표수": row["투표수"]}
        for _, row in totals_raw.iterrows()
        if pd.notna(row["구시군"]) and "합계" not in str(row["구시군"])
        and "전국" not in str(row["시도"])
    ]

    remove_mask = raw["읍면동명"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= raw["구시군"].astype(str).str.contains("합계|소계|합계\\(특별시\\)|합계\\(광역시\\)|합계\\(도\\)", na=False)
    remove_mask |= raw["시도"].astype(str).str.contains("전국", na=False)
    remove_mask |= raw["투표구명"].astype(str).str.contains("소계", na=False)
    data = raw[~remove_mask].copy()

    for col in ["선거인수", "투표수", "무효투표수", "기권수"] + cand_labels:
        if col in data.columns:
            data[col] = _clean_num(data[col])

    rows = []
    for _, row in data.iterrows():
        tpgu = str(row["투표구명"]) if pd.notna(row["투표구명"]) else ""
        for label in cand_labels:
            party, name = _parse_cand_col(label)
            rows.append({
                "선거_회차": ROUND,
                "선거일": "2022-03-09",
                "시도": row["시도"],
                "구시군": row["구시군"],
                "읍면동": row["읍면동명"],
                "투표구": tpgu,
                "선거인수": row["선거인수"],
                "투표수": row["투표수"],
                "후보자": name,
                "정당": party,
                "득표수": row[label],
                "무효투표수": row.get("무효투표수"),
                "기권수": row.get("기권수"),
                "level": normalize_level(tpgu),
            })
    return rows, totals
```

- [ ] **Step 3: parse_21.py 작성**

`process_presidential.py:683~739` 이식.

```python
# etl/pres/parse_21.py
"""21대(2025) 대통령선거 파서."""

import pandas as pd
from etl.pres.schema import normalize_level

RAW_PATH = "data_raw/제21대_대통령선거_개표결과.xlsx"
ROUND = 21


def _clean_num(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )


def _parse_cand_col(col_name):
    col_name = col_name.strip()
    if "\n" in col_name:
        parts = col_name.split("\n", 1)
        return parts[0].strip(), parts[1].strip()
    tokens = col_name.split()
    if len(tokens) >= 2:
        return " ".join(tokens[:-1]), tokens[-1]
    return col_name, ""


def parse_21(path=RAW_PATH):
    raw = pd.read_excel(path, header=None)

    cand_labels = []
    for val in raw.iloc[4, 6:].tolist():
        v = str(val).strip()
        if v in ("nan", "계", "NaN", ""):
            continue
        cand_labels.append(v)

    data = raw.iloc[6:].copy()
    data.columns = ["시도", "구시군", "읍면동", "투표구", "선거인수", "투표수",
                    *cand_labels, "계", "무효투표수", "기권수"]
    data["시도"] = data["시도"].ffill()
    data["구시군"] = data["구시군"].ffill()
    data["읍면동"] = data["읍면동"].ffill()

    total_mask = data["읍면동"].astype(str).str.contains("합계", na=False)
    totals_raw = data[total_mask].copy()
    totals_raw["투표수"] = _clean_num(totals_raw["투표수"])
    totals = [
        {"시도": row["시도"], "구시군": row["구시군"], "투표수": row["투표수"]}
        for _, row in totals_raw.iterrows()
        if pd.notna(row["구시군"]) and "합계" not in str(row["구시군"])
        and "전국" not in str(row["시도"])
    ]

    remove_mask = data["읍면동"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= data["구시군"].astype(str).str.contains("합계|소계|합계\\(특별시\\)|합계\\(광역시\\)|합계\\(도\\)", na=False)
    remove_mask |= data["시도"].astype(str).str.contains("전국", na=False)
    remove_mask |= data["투표구"].astype(str).str.contains("소계", na=False)
    data = data[~remove_mask].copy()

    for col in ["선거인수", "투표수", "무효투표수", "기권수"] + cand_labels:
        if col in data.columns:
            data[col] = _clean_num(data[col])

    rows = []
    for _, row in data.iterrows():
        tpgu = str(row["투표구"]) if pd.notna(row["투표구"]) else ""
        for label in cand_labels:
            party, name = _parse_cand_col(label)
            rows.append({
                "선거_회차": ROUND,
                "선거일": "2025-06-03",
                "시도": row["시도"],
                "구시군": row["구시군"],
                "읍면동": row["읍면동"],
                "투표구": tpgu,
                "선거인수": row["선거인수"],
                "투표수": row["투표수"],
                "후보자": name,
                "정당": party,
                "득표수": row[label],
                "무효투표수": row["무효투표수"],
                "기권수": row["기권수"],
                "level": normalize_level(tpgu),
            })
    return rows, totals
```

- [ ] **Step 4: 19~21대 smoke test**

```bash
python -c "
import sys; sys.path.insert(0, '.')
from etl.pres.parse_19 import parse_19
from etl.pres.parse_20 import parse_20
from etl.pres.parse_21 import parse_21
for fn, name, expected in [
    (parse_19, '19대', 280000),
    (parse_20, '20대', 220000),
    (parse_21, '21대', 90000),
]:
    rows, totals = fn()
    print(f'{name}: {len(rows)}행, totals={len(totals)}')
    assert len(rows) >= expected
print('ALL OK')
"
```

- [ ] **Step 5: 커밋**

```bash
git add etl/pres/parse_19.py etl/pres/parse_20.py etl/pres/parse_21.py
git commit -m "feat(pres): parse_19~21 — 19·20·21대 파서 모듈화"
```

---

## Task 6: tests/pres/test_parse_21.py

**Files:**
- Test: `tests/pres/test_parse_21.py`

21대가 가장 최신이고 데이터가 안정적이므로 통합 검증 테스트를 작성한다. 지방선거의 `test_parse_8th.py`와 동일한 패턴.

- [ ] **Step 1: 테스트 작성**

```python
# tests/pres/test_parse_21.py
from etl.pres.parse_21 import parse_21
from etl.pres.schema import to_dataframe, COLUMNS
from etl.pres.validate import run_all_checks
from etl.pres.official_totals import OFFICIAL_TOP


def test_parse_21_returns_rows_and_totals():
    rows, totals = parse_21()
    assert len(rows) > 80000
    assert len(totals) > 100
    df = to_dataframe(rows)
    assert list(df.columns) == COLUMNS


def test_parse_21_no_nan_sido():
    """시도 컬럼에 NaN이 없어야 한다."""
    rows, _ = parse_21()
    df = to_dataframe(rows)
    assert df["시도"].isna().sum() == 0


def test_parse_21_passes_all_validation():
    rows, totals = parse_21()
    for row in rows:
        row.setdefault("선거일", "2025-06-03")
    df = to_dataframe(rows)
    official = {k: v for k, v in OFFICIAL_TOP.items() if k[0] == 21}
    errors = run_all_checks(df, totals, official or None)
    assert errors == [], "검증 위반:\n" + "\n".join(f"  {n}: {d}" for n, d in errors[:20])
```

- [ ] **Step 2: 테스트 실행 — 결과 확인**

```
pytest tests/pres/test_parse_21.py -v
```

21대 `OFFICIAL_TOP` 값이 임시이면 `test_parse_21_passes_all_validation`이 실패할 수 있다. 실패 메시지의 실제 집계값을 `official_totals.py`에 채워 넣는다.

- [ ] **Step 3: official_totals.py에 21대 실제 값 채우기**

테스트 실패 시 출력되는 `집계 XXXXXX != 공식 YYYYYY` 에서 `집계` 값을 `official_totals.py`의 21대 항목에 반영:

```python
# etl/pres/official_totals.py 중 21대 부분 — 실제 집계값으로 교체
(21, "서울특별시"): ("이재명", <실제값>),
(21, "경기도"):   ("이재명", <실제값>),
```

- [ ] **Step 4: 재실행 — PASS 확인**

```
pytest tests/pres/test_parse_21.py -v
```
Expected: 모두 PASS

- [ ] **Step 5: 커밋**

```bash
git add tests/pres/test_parse_21.py etl/pres/official_totals.py
git commit -m "test(pres): test_parse_21 통합 검증 + official_totals 21대 확정"
```

---

## Task 7: build.py

**Files:**
- Create: `etl/pres/build.py`
- Test: `tests/pres/test_build.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/pres/test_build.py
from etl.pres.build import ELECTION_DATES, PARSERS


def test_election_dates_cover_14_to_21():
    assert ELECTION_DATES[14] == "1992-12-18"
    assert ELECTION_DATES[21] == "2025-06-03"
    assert set(ELECTION_DATES) == {14, 15, 16, 17, 18, 19, 20, 21}


def test_parsers_cover_all_rounds():
    rounds = [round_num for round_num, _ in PARSERS]
    assert rounds == [14, 15, 16, 17, 18, 19, 20, 21]
```

- [ ] **Step 2: 테스트 실행 — FAIL 확인**

```
pytest tests/pres/test_build.py -v
```
Expected: `ModuleNotFoundError: No module named 'etl.pres.build'`

- [ ] **Step 3: build.py 작성**

```python
# etl/pres/build.py
"""대선 ETL 오케스트레이터. parse → validate → CSV.

검증을 통과하지 못하면 CSV를 쓰지 않고 exit≠0.
"""

import sys

from etl.pres.schema import to_dataframe
from etl.pres.validate import run_all_checks
from etl.pres.official_totals import OFFICIAL_TOP
from etl.pres.parse_14 import parse_14
from etl.pres.parse_15 import parse_15
from etl.pres.parse_16 import parse_16
from etl.pres.parse_17 import parse_17
from etl.pres.parse_18 import parse_18
from etl.pres.parse_19 import parse_19
from etl.pres.parse_20 import parse_20
from etl.pres.parse_21 import parse_21

ELECTION_DATES = {
    14: "1992-12-18",
    15: "1997-12-18",
    16: "2002-12-19",
    17: "2007-12-19",
    18: "2012-12-19",
    19: "2017-05-09",
    20: "2022-03-09",
    21: "2025-06-03",
}

PARSERS = [
    (14, parse_14),
    (15, parse_15),
    (16, parse_16),
    (17, parse_17),
    (18, parse_18),
    (19, parse_19),
    (20, parse_20),
    (21, parse_21),
]

OUT_PATH = "data_processed/대통령선거.csv"


def build():
    all_rows = []
    all_totals = []
    failed = False

    for round_num, parse_fn in PARSERS:
        print(f"=== {round_num}대 파싱 ===")
        rows, totals = parse_fn()
        for row in rows:
            row.setdefault("선거일", ELECTION_DATES[round_num])
        df = to_dataframe(rows)
        official = {k: v for k, v in OFFICIAL_TOP.items() if k[0] == round_num}
        errors = run_all_checks(df, totals, official or None)
        if errors:
            failed = True
            print(f"  [FAIL] {round_num}대 검증 위반 {len(errors)}건:")
            for name, detail in errors[:20]:
                print(f"    {name}: {detail}")
        else:
            print(f"  [OK] {round_num}대 {len(rows):,}행 검증 통과")
        all_rows.extend(rows)
        all_totals.extend(totals)

    if failed:
        print("\n검증 실패 — CSV를 쓰지 않습니다.")
        sys.exit(1)

    df = to_dataframe(all_rows)
    df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n[DONE] {len(df):,}행 → {OUT_PATH}")


if __name__ == "__main__":
    build()
```

- [ ] **Step 4: 테스트 실행 — PASS 확인**

```
pytest tests/pres/test_build.py -v
```
Expected: 모두 PASS

- [ ] **Step 5: 커밋**

```bash
git add etl/pres/build.py tests/pres/test_build.py
git commit -m "feat(pres): build.py 오케스트레이터 + test_build"
```

---

## Task 8: 전체 통합 실행 및 process_presidential.py 삭제

- [ ] **Step 1: build.py 전체 실행**

```bash
python -m etl.pres.build
```

Expected: 각 회차 `[OK]` 출력 후 `[DONE] 964,728행 → data_processed/대통령선거.csv`

- [ ] **Step 2: 실패 시 디버깅**

`check_totals_match` 실패가 발생하면 해당 회차 파서의 totals 추출 로직을 점검한다.  
`check_official_totals` 실패가 발생하면 `official_totals.py`의 값을 실제 집계값으로 교체.

- [ ] **Step 3: 전체 테스트 실행**

```bash
pytest tests/pres/ -v
```
Expected: 모두 PASS

- [ ] **Step 4: process_presidential.py 삭제**

```bash
git rm process_presidential.py
```

- [ ] **Step 5: 최종 커밋**

```bash
git add -u
git commit -m "feat(pres): ETL 구조화 완료 — process_presidential.py 제거, etl/pres/ 통합"
```

---

## Self-Review

**Spec coverage 체크:**
- [x] schema.py (COLUMNS, normalize_level, to_dataframe) — Task 1
- [x] validate.py (duplicate/range/totals/official) — Task 2
- [x] official_totals.py — Task 3
- [x] parse_14~18 — Task 4
- [x] parse_19~21 — Task 5
- [x] tests/pres/test_parse_21.py 통합 검증 — Task 6
- [x] build.py 오케스트레이터 — Task 7
- [x] process_presidential.py 삭제 + 전체 통합 실행 — Task 8

**Placeholder 없음 확인:** 모든 코드 블록에 실제 구현 코드 포함.

**Type/이름 일관성:**
- `parse_XX(path) → (rows, totals)` 시그니처 모든 파서 동일
- `totals` 딕셔너리 키: `{시도, 구시군, 투표수}` — validate.py와 일치
- `official_top` 키: `(회차, 시도)` — validate.py `check_official_totals` 와 일치

**알려진 주의사항:**
- 18대는 투표수/선거인수 컬럼 없음 → `None` 처리, totals=[]
- 17대는 폴더 내 시도별 파일 → `_parse_file` 내부 함수 사용
- 21대 `official_totals.py` 값은 Task 6에서 실제 집계값으로 확정
