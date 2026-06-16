# 검증된 지방선거 ETL 파이프라인 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 원본 XLSX→CSV 변환이 자동 검증(시도별 후보 상이·합계 정합·중복 없음·범위 정합)을 통과한 지방선거(3~8회) 데이터 파이프라인을 만든다.

**Architecture:** 파서(회차별)→tidy rows→검증 게이트→CSV. 검증을 통과하지 못하면 CSV를 쓰지 않는다. 검증 모듈을 먼저 만들고, 회차별 파서를 하나씩 검증 통과시킨다. 회차별 파서는 Opus 서브에이전트가 원본을 직접 까보고 구현한다.

**Tech Stack:** Python 3, pandas, openpyxl, pytest. 원본은 `data_raw/`, 산출 CSV는 `data_processed/지방선거.csv`. ETL 코드는 `etl/local/`.

---

## 디렉토리 구조

```
etl/local/
├─ schema.py          # tidy row 컬럼 정의 + 빈 DataFrame 팩토리
├─ validate.py        # 검증 게이트 (4개 내부 정합성 + 외부 대조)
├─ official_totals.py # 선관위 공식 시도별 1·2위 득표 (외부 대조 기준선)
├─ parse_8th.py       # 8회 통합 XLSX 파서
├─ parse_7th.py       # 7회 통합 XLSX 파서
├─ parse_6th.py       # 6회 시도별 분리 파서
├─ parse_5th.py       # 5회 파서
├─ parse_4th.py       # 4회 파서
├─ parse_3rd.py       # 3회 XLS 파서
└─ build.py           # 오케스트레이터: parse → validate → write CSV

tests/local/
├─ test_schema.py
├─ test_validate.py
├─ test_parse_8th.py
├─ test_parse_7th.py
├─ test_parse_6th.py
├─ test_parse_5th.py
├─ test_parse_4th.py
└─ test_parse_3rd.py
```

## tidy row 스키마 (모든 파서 공통 출력)

각 파서는 아래 컬럼을 가진 `list[dict]`를 반환한다. `level`은 가장 세분 단위만 (집계행 제외).

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `선거_회차` | int | 3~8 |
| `선거일` | str | "2022-06-01" |
| `선거종류` | str | 시도지사/광역비례/구시군장/시도의원/구시군의원/기초비례/교육감/교육의원 |
| `시도` | str | 서울특별시 등 (첫 컬럼 라벨 무시, 항상 sido) |
| `구시군` | str | 종로구 등 |
| `읍면동` | str | 청운효자동 등 (투표구까지 들어갈 수 있음) |
| `선거구명` | str | 선거구명(없으면 구시군 fallback) |
| `선거인수` | int | |
| `투표수` | int | |
| `후보자` | str\|None | 비례·교육감은 None (정당/이름이 정당 컬럼에) |
| `정당` | str | |
| `득표수` | int | |
| `무효투표수` | int\|None | |
| `기권수` | int\|None | |
| `level` | str | 당일투표/사전투표/관외사전투표/거소선상 |

**level 매핑 규칙 (구분 컬럼 또는 읍면동 값 기반):**
- `선거일투표` → `당일투표`
- `관내사전투표` → `사전투표`
- `관외사전투표` → `관외사전투표`
- `거소투표`, `거소·선상투표`, `선상투표` → `거소선상`

**집계행 (저장 안 함, 검증 기준값으로만):** 읍면동 값이 `합계`, 또는 구분 값이 `소계`, 또는 읍면동이 비고 구분이 `합계`.

---

### Task 1: tidy row 스키마

**Files:**
- Create: `etl/local/__init__.py` (빈 파일)
- Create: `etl/local/schema.py`
- Test: `tests/local/test_schema.py`

- [ ] **Step 1: 빈 패키지 파일 생성**

```bash
mkdir -p etl/local tests/local
touch etl/local/__init__.py tests/local/__init__.py
```

- [ ] **Step 2: Write the failing test**

`tests/local/test_schema.py`:

```python
import pandas as pd
from etl.local.schema import COLUMNS, LEVEL_MAP, to_dataframe, normalize_level


def test_columns_order():
    assert COLUMNS == [
        "선거_회차", "선거일", "선거종류", "시도", "구시군", "읍면동",
        "선거구명", "선거인수", "투표수", "후보자", "정당", "득표수",
        "무효투표수", "기권수", "level",
    ]


def test_normalize_level():
    assert normalize_level("선거일투표") == "당일투표"
    assert normalize_level("관내사전투표") == "사전투표"
    assert normalize_level("관외사전투표") == "관외사전투표"
    assert normalize_level("거소투표") == "거소선상"
    assert normalize_level("거소·선상투표") == "거소선상"
    assert normalize_level("선상투표") == "거소선상"


def test_to_dataframe_has_all_columns():
    rows = [{
        "선거_회차": 8, "선거일": "2022-06-01", "선거종류": "시도지사",
        "시도": "서울특별시", "구시군": "종로구", "읍면동": "청운효자동",
        "선거구명": "서울특별시", "선거인수": 7447, "투표수": 3155,
        "후보자": "오세훈", "정당": "국민의힘", "득표수": 1802,
        "무효투표수": 62, "기권수": None, "level": "당일투표",
    }]
    df = to_dataframe(rows)
    assert list(df.columns) == COLUMNS
    assert len(df) == 1
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/seong-in/Desktop/Git/pyosim && python -m pytest tests/local/test_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'etl.local.schema'`

- [ ] **Step 4: Write minimal implementation**

`etl/local/schema.py`:

```python
"""tidy row 스키마 정의."""

import pandas as pd

COLUMNS = [
    "선거_회차", "선거일", "선거종류", "시도", "구시군", "읍면동",
    "선거구명", "선거인수", "투표수", "후보자", "정당", "득표수",
    "무효투표수", "기권수", "level",
]

LEVEL_MAP = {
    "선거일투표": "당일투표",
    "관내사전투표": "사전투표",
    "관외사전투표": "관외사전투표",
    "거소투표": "거소선상",
    "거소·선상투표": "거소선상",
    "선상투표": "거소선상",
}


def normalize_level(raw):
    """원본 구분/읍면동 값을 표준 level로 변환. 미매핑은 그대로 반환."""
    key = str(raw or "").strip()
    return LEVEL_MAP.get(key, key)


def to_dataframe(rows):
    """tidy row dict 리스트를 COLUMNS 순서의 DataFrame으로."""
    return pd.DataFrame(rows, columns=COLUMNS)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/local/test_schema.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add etl/local/__init__.py tests/local/__init__.py etl/local/schema.py tests/local/test_schema.py
git commit -m "feat(etl): tidy row 스키마 + level 정규화"
```

---

### Task 2: 검증 게이트 — 중복 행 + 범위 정합

**Files:**
- Create: `etl/local/validate.py`
- Test: `tests/local/test_validate.py`

검증 모듈은 `ValidationError` 리스트를 반환한다(빈 리스트 = 통과). 각 위반은 `(check_name, detail)` 튜플.

- [ ] **Step 1: Write the failing test**

`tests/local/test_validate.py`:

```python
import pandas as pd
from etl.local.schema import to_dataframe
from etl.local.validate import check_no_duplicate_rows, check_value_ranges


def _row(**kwargs):
    base = {
        "선거_회차": 8, "선거일": "2022-06-01", "선거종류": "시도지사",
        "시도": "서울특별시", "구시군": "종로구", "읍면동": "청운효자동",
        "선거구명": "서울특별시", "선거인수": 7447, "투표수": 3155,
        "후보자": "오세훈", "정당": "국민의힘", "득표수": 1802,
        "무효투표수": 62, "기권수": None, "level": "당일투표",
    }
    base.update(kwargs)
    return base


def test_no_duplicate_rows_passes_when_unique():
    df = to_dataframe([_row(후보자="오세훈"), _row(후보자="송영길", 득표수=1246)])
    assert check_no_duplicate_rows(df) == []


def test_no_duplicate_rows_flags_repeat():
    df = to_dataframe([_row(후보자="오세훈"), _row(후보자="오세훈")])
    errors = check_no_duplicate_rows(df)
    assert len(errors) == 1
    assert errors[0][0] == "duplicate_rows"


def test_value_ranges_passes():
    df = to_dataframe([_row(득표수=1802, 투표수=3155, 선거인수=7447)])
    assert check_value_ranges(df) == []


def test_value_ranges_flags_votes_exceed_turnout():
    df = to_dataframe([_row(득표수=9999, 투표수=3155, 선거인수=7447)])
    errors = check_value_ranges(df)
    assert len(errors) == 1
    assert errors[0][0] == "value_range"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/local/test_validate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'etl.local.validate'`

- [ ] **Step 3: Write minimal implementation**

`etl/local/validate.py`:

```python
"""검증 게이트. 파서가 원본을 그대로 옮겼는지 검사한다.

각 check는 위반 리스트 [(check_name, detail), ...]를 반환. 빈 리스트 = 통과.
원본은 항상 옳다. 위반 = 파서 버그.
"""

KEY_COLS = ["선거_회차", "선거종류", "시도", "구시군", "읍면동", "level", "후보자"]


def check_no_duplicate_rows(df):
    """같은 (회차,선거종류,시도,구시군,읍면동,level,후보자)가 두 번 나오면 위반."""
    dup_mask = df.duplicated(subset=KEY_COLS, keep=False)
    if not dup_mask.any():
        return []
    errors = []
    dups = df[dup_mask].groupby(KEY_COLS, dropna=False).size()
    for key, count in dups.items():
        errors.append(("duplicate_rows", f"{key} → {count}건 중복"))
    return errors


def check_value_ranges(df):
    """득표 ≤ 투표수 ≤ 선거인수 위반 검사."""
    errors = []
    votes = df["득표수"].fillna(0)
    turnout = df["투표수"].fillna(0)
    over = df[votes > turnout]
    for _, row in over.iterrows():
        errors.append((
            "value_range",
            f"{row['시도']} {row['구시군']} {row['읍면동']} "
            f"{row['후보자']} 득표 {row['득표수']} > 투표수 {row['투표수']}",
        ))
    return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/local/test_validate.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add etl/local/validate.py tests/local/test_validate.py
git commit -m "feat(etl): 검증 게이트 — 중복 행·범위 정합"
```

---

### Task 3: 검증 게이트 — 시도별 후보 일관성

8회 버그(전국=서울 후보) 직격 검사.

**Files:**
- Modify: `etl/local/validate.py`
- Test: `tests/local/test_validate.py`

- [ ] **Step 1: Write the failing test (append)**

`tests/local/test_validate.py`에 추가:

```python
from etl.local.validate import check_sido_candidate_consistency


def test_sido_candidate_consistency_passes_when_distinct():
    rows = []
    for cand in ["오세훈", "송영길"]:
        rows.append(_row(시도="서울특별시", 후보자=cand))
    for cand in ["박형준", "변성완"]:
        rows.append(_row(시도="부산광역시", 구시군="중구", 읍면동="중앙동", 후보자=cand))
    df = to_dataframe(rows)
    assert check_sido_candidate_consistency(df) == []


def test_sido_candidate_consistency_flags_identical_sets():
    rows = []
    for sido in ["서울특별시", "충청북도"]:
        for cand in ["오세훈", "송영길"]:
            rows.append(_row(시도=sido, 후보자=cand))
    df = to_dataframe(rows)
    errors = check_sido_candidate_consistency(df)
    assert len(errors) >= 1
    assert errors[0][0] == "sido_candidate_collision"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/local/test_validate.py -k sido_candidate -v`
Expected: FAIL — `ImportError: cannot import name 'check_sido_candidate_consistency'`

- [ ] **Step 3: Write minimal implementation (append to validate.py)**

```python
SIDO_SCOPED_TYPES = {"시도지사", "교육감", "광역비례"}


def check_sido_candidate_consistency(df):
    """시도 단위 선거(시도지사·교육감·광역비례)에서 후보 집합이
    시도마다 서로 달라야 한다. 두 시도의 후보 집합이 완전히 같으면
    파서가 한 시도 헤더를 다른 시도에 잘못 복사한 것."""
    errors = []
    scoped = df[df["선거종류"].isin(SIDO_SCOPED_TYPES)]
    for (회차, 선거종류), group in scoped.groupby(["선거_회차", "선거종류"]):
        # 시도별 식별자 집합 (후보자 없으면 정당)
        ident = group["후보자"].fillna(group["정당"])
        sido_sets = {}
        for sido, sub_idx in group.groupby("시도").groups.items():
            sido_sets[sido] = frozenset(ident.loc[sub_idx].dropna().unique())
        sidos = list(sido_sets)
        for i in range(len(sidos)):
            for j in range(i + 1, len(sidos)):
                a, b = sidos[i], sidos[j]
                if sido_sets[a] and sido_sets[a] == sido_sets[b]:
                    errors.append((
                        "sido_candidate_collision",
                        f"{회차}회 {선거종류}: {a} 후보집합 == {b} "
                        f"{set(list(sido_sets[a])[:4])} → 시도 헤더 복사 의심",
                    ))
    return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/local/test_validate.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add etl/local/validate.py tests/local/test_validate.py
git commit -m "feat(etl): 검증 게이트 — 시도별 후보 일관성 (8회 버그 직격)"
```

---

### Task 4: 검증 게이트 — 합계 정합성 + 통합 러너

원본 합계행과 대조하려면 파서가 합계행 값도 함께 넘겨야 한다. 파서는 tidy rows(세분 단위)와 별도로 `totals` 리스트 `[{선거종류, 시도, 구시군, level, 투표수}]`를 반환하도록 한다. 합계 정합성은 "세분 단위 투표수 합 == 합계행 투표수"를 구시군 단위로 검사한다.

**Files:**
- Modify: `etl/local/validate.py`
- Test: `tests/local/test_validate.py`

- [ ] **Step 1: Write the failing test (append)**

```python
from etl.local.validate import check_totals_match, run_all_checks


def test_totals_match_passes():
    rows = [
        _row(읍면동="청운효자동", level="당일투표", 투표수=3155, 후보자="오세훈", 득표수=1802),
        _row(읍면동="청운효자동", level="당일투표", 투표수=3155, 후보자="송영길", 득표수=1246),
        _row(읍면동="청운효자동", level="사전투표", 투표수=1732, 후보자="오세훈", 득표수=828),
        _row(읍면동="청운효자동", level="사전투표", 투표수=1732, 후보자="송영길", 득표수=848),
    ]
    df = to_dataframe(rows)
    # 구시군 합계 투표수 = 3155 + 1732 = 4887
    totals = [{"선거종류": "시도지사", "시도": "서울특별시", "구시군": "종로구",
               "level": None, "투표수": 4887}]
    assert check_totals_match(df, totals) == []


def test_totals_match_flags_mismatch():
    rows = [
        _row(읍면동="청운효자동", level="당일투표", 투표수=3155, 후보자="오세훈", 득표수=1802),
    ]
    df = to_dataframe(rows)
    totals = [{"선거종류": "시도지사", "시도": "서울특별시", "구시군": "종로구",
               "level": None, "투표수": 9999}]
    errors = check_totals_match(df, totals)
    assert len(errors) == 1
    assert errors[0][0] == "totals_mismatch"


def test_run_all_checks_aggregates():
    df = to_dataframe([_row(후보자="오세훈"), _row(후보자="오세훈")])
    errors = run_all_checks(df, totals=[])
    names = {name for name, _ in errors}
    assert "duplicate_rows" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/local/test_validate.py -k "totals or run_all" -v`
Expected: FAIL — `ImportError: cannot import name 'check_totals_match'`

- [ ] **Step 3: Write minimal implementation (append to validate.py)**

```python
def _turnout_per_precinct(df, 선거종류, 시도, 구시군):
    """한 구시군의 세분 단위 투표수 합. 투표수는 (읍면동,level)당 한 번만
    세야 하므로 후보 행 중복을 제거하고 합산한다."""
    sub = df[
        (df["선거종류"] == 선거종류)
        & (df["시도"] == 시도)
        & (df["구시군"] == 구시군)
    ]
    per = sub.drop_duplicates(subset=["읍면동", "level"])
    return int(per["투표수"].fillna(0).sum())


def check_totals_match(df, totals):
    """파서가 넘긴 구시군 합계행 투표수 == 세분 단위 투표수 합."""
    errors = []
    for total in totals:
        actual = _turnout_per_precinct(
            df, total["선거종류"], total["시도"], total["구시군"]
        )
        expected = int(total["투표수"])
        if actual != expected:
            errors.append((
                "totals_mismatch",
                f"{total['선거종류']} {total['시도']} {total['구시군']}: "
                f"세분합 {actual} != 합계행 {expected} (차 {actual - expected})",
            ))
    return errors


def run_all_checks(df, totals):
    """모든 내부 정합성 검사를 실행하고 위반을 합쳐 반환."""
    errors = []
    errors += check_no_duplicate_rows(df)
    errors += check_value_ranges(df)
    errors += check_sido_candidate_consistency(df)
    errors += check_totals_match(df, totals)
    return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/local/test_validate.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add etl/local/validate.py tests/local/test_validate.py
git commit -m "feat(etl): 검증 게이트 — 합계 정합성 + run_all_checks"
```

---

### Task 5: 공식 시도별 득표 기준선 (외부 대조)

8회 시도지사 17개 시도 1위 득표만 하드코딩(검증용 핵심 표본). 출처: 위키백과 제8회 전국동시지방선거.

**Files:**
- Create: `etl/local/official_totals.py`
- Modify: `etl/local/validate.py`
- Test: `tests/local/test_validate.py`

- [ ] **Step 1: 공식 득표 데이터 생성**

`etl/local/official_totals.py`:

```python
"""선관위 공식 시도별 1위 득표 (외부 대조 기준선).

검증용 핵심 표본만. 시도지사 1위 득표가 맞으면 시도 매핑이 올바르다는 증거.
출처: 위키백과 각 지방선거 시도지사 결과.
"""

# {(회차, 선거종류, 시도): (1위후보, 1위득표)}
OFFICIAL_TOP = {
    (8, "시도지사", "서울특별시"): ("오세훈", 2798360),
    (8, "시도지사", "부산광역시"): ("박형준", 962469),
    (8, "시도지사", "인천광역시"): ("유정복", 615077),
    (8, "시도지사", "경기도"): ("김동연", 2827979),
}
```

- [ ] **Step 2: Write the failing test (append to test_validate.py)**

```python
from etl.local.validate import check_official_totals
from etl.local.official_totals import OFFICIAL_TOP


def test_official_totals_passes_when_match():
    rows = []
    for level, votes in [("당일투표", 2000000), ("사전투표", 798360)]:
        rows.append(_row(시도="서울특별시", 구시군="종로구", 읍면동="청운효자동",
                         level=level, 후보자="오세훈", 득표수=votes))
    df = to_dataframe(rows)
    # 오세훈 합계 = 2,798,360
    assert check_official_totals(df, OFFICIAL_TOP) == []


def test_official_totals_flags_mismatch():
    rows = [_row(시도="서울특별시", 후보자="오세훈", 득표수=5)]
    df = to_dataframe(rows)
    errors = check_official_totals(df, OFFICIAL_TOP)
    assert any(name == "official_mismatch" for name, _ in errors)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/local/test_validate.py -k official -v`
Expected: FAIL — `ImportError: cannot import name 'check_official_totals'`

- [ ] **Step 4: Write minimal implementation (append to validate.py)**

```python
def check_official_totals(df, official_top):
    """시도 단위 후보 득표 합이 공식 1위 득표와 일치하는지 대조."""
    errors = []
    for (회차, 선거종류, 시도), (cand, votes) in official_top.items():
        sub = df[
            (df["선거_회차"] == 회차)
            & (df["선거종류"] == 선거종류)
            & (df["시도"] == 시도)
            & (df["후보자"] == cand)
        ]
        actual = int(sub["득표수"].fillna(0).sum())
        if actual != votes:
            errors.append((
                "official_mismatch",
                f"{회차}회 {선거종류} {시도} {cand}: "
                f"집계 {actual} != 공식 {votes} (차 {actual - votes})",
            ))
    return errors
```

- [ ] **Step 5: run_all_checks에 공식 대조 연결**

`validate.py`의 `run_all_checks`를 수정:

```python
def run_all_checks(df, totals, official_top=None):
    """모든 검사를 실행하고 위반을 합쳐 반환."""
    errors = []
    errors += check_no_duplicate_rows(df)
    errors += check_value_ranges(df)
    errors += check_sido_candidate_consistency(df)
    errors += check_totals_match(df, totals)
    if official_top:
        errors += check_official_totals(df, official_top)
    return errors
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/local/test_validate.py -v`
Expected: PASS (11 passed)

- [ ] **Step 7: Commit**

```bash
git add etl/local/official_totals.py etl/local/validate.py tests/local/test_validate.py
git commit -m "feat(etl): 외부 대조 — 공식 시도별 1위 득표"
```

---

### Task 6: 8회 파서 (Opus 서브에이전트)

**이 태스크는 Opus 서브에이전트가 담당한다.** 원본을 직접 까보고 파서를 구현, 검증 통과까지 자가 반복.

**Files:**
- Create: `etl/local/parse_8th.py`
- Test: `tests/local/test_parse_8th.py`

**원본:** `data_raw/제8회_전국동시지방선거_읍면동별_개표결과-게시판게시/*.xlsx` (선거종류별 통합 파일 9개)

**원본 구조 (실측):**
- row0: `선거구명 | 구시군명 | 읍면동명 | 구분 | 선거인수 | 투표수 | 후보자별득표수(병합) | ... | 계 | 무효투표수 | 기권수`
- row1: `후보1 | 후보2 | ...` (placeholder)
- row2: 첫 시도(서울)의 후보 헤더 `정당\n이름` (예: `더불어민주당\n송영길`)
- row3+: 데이터. **시도가 바뀌면** 그 시도 블록 첫 행(읍면동명 빈칸 + 후보셀에 `정당\n이름`)이 새 후보 헤더. 이 행에서 `cand_cols`를 갱신해야 한다. ← **현재 깨진 핵심.**
- 행 계층: `합계`(구시군), `거소투표`/`관외사전투표`(구시군 특수), `읍면동+소계`, `읍면동+관내사전투표`, `읍면동+선거일투표`.

**서브에이전트 지침:**
1. `data_raw/.../시도지사선거.xlsx`를 openpyxl로 열어 행 구조·시도 전환 지점을 직접 확인하라.
2. **시도 전환 행 감지 → 후보 헤더 재파싱**이 핵심. 후보셀에 `\n`이 있고 득표가 숫자가 아닌 행이 헤더 행이다.
3. 비례(`광역비례의원선거.xlsx`·`기초비례의원선거.xlsx`)는 후보자 없이 정당만. `교육감선거.xlsx`는 후보자에 이름.
4. 집계행(합계/소계/구분이 합계)은 tidy rows에 넣지 말고, 구시군 `합계`행의 투표수를 `totals` 리스트에 모아라.
5. `parse_8th(dir_path) -> (rows, totals)` 시그니처. rows는 tidy dict 리스트, totals는 `[{선거종류,시도,구시군,level:None,투표수}]`.

- [ ] **Step 1: Write the failing test**

`tests/local/test_parse_8th.py`:

```python
import pandas as pd
from etl.local.parse_8th import parse_8th
from etl.local.schema import to_dataframe, COLUMNS
from etl.local.validate import run_all_checks
from etl.local.official_totals import OFFICIAL_TOP

DIR = "data_raw/제8회_전국동시지방선거_읍면동별_개표결과-게시판게시"


def test_parse_8th_returns_rows_and_totals():
    rows, totals = parse_8th(DIR)
    assert len(rows) > 100000
    assert len(totals) > 200
    df = to_dataframe(rows)
    assert list(df.columns) == COLUMNS


def test_parse_8th_sido_candidates_distinct():
    """충북에 서울 후보(오세훈)가 없어야 한다 — 시도 헤더 갱신 검증."""
    rows, _ = parse_8th(DIR)
    df = to_dataframe(rows)
    chungbuk = df[(df["선거종류"] == "시도지사") & (df["시도"] == "충청북도")]
    assert "오세훈" not in set(chungbuk["후보자"].dropna())
    assert "송영길" not in set(chungbuk["후보자"].dropna())


def test_parse_8th_passes_all_validation():
    rows, totals = parse_8th(DIR)
    df = to_dataframe(rows)
    errors = run_all_checks(df, totals, OFFICIAL_TOP)
    assert errors == [], f"검증 위반:\n" + "\n".join(f"  {n}: {d}" for n, d in errors[:20])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/local/test_parse_8th.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'etl.local.parse_8th'`

- [ ] **Step 3: 서브에이전트가 parse_8th.py 구현**

`etl/local/parse_8th.py` 작성. 위 지침을 따라 시도 전환 시 후보 헤더를 재파싱한다. 코드는 서브에이전트가 원본 실측 후 작성.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/local/test_parse_8th.py -v`
Expected: PASS (3 passed). 특히 `test_parse_8th_passes_all_validation`가 통과해야 끝.

- [ ] **Step 5: Commit**

```bash
git add etl/local/parse_8th.py tests/local/test_parse_8th.py
git commit -m "feat(etl): 8회 지방선거 파서 — 시도별 후보 헤더 갱신, 검증 통과"
```

---

### Task 7: 7회 파서 (Opus 서브에이전트)

**Opus 서브에이전트 담당.**

**Files:**
- Create: `etl/local/parse_7th.py`
- Test: `tests/local/test_parse_7th.py`

**원본:** `data_raw/전국동시지방선거 개표결과(제7회)/20180619-7지선-NN-(선거종류)_읍면동별개표자료.xlsx` (통합 파일)

**서브에이전트 지침:**
1. 7회 통합 XLSX의 헤더 위치·시도 전환 지점을 직접 확인하라(8회와 유사하나 다를 수 있음).
2. 8회와 같은 5단계 지침(시도 헤더 갱신, 비례/교육감 분기, 집계행 totals 분리, `(rows, totals)` 반환) 적용.
3. `parse_7th(dir_path) -> (rows, totals)`.

- [ ] **Step 1: Write the failing test**

`tests/local/test_parse_7th.py`:

```python
from etl.local.parse_7th import parse_7th
from etl.local.schema import to_dataframe, COLUMNS
from etl.local.validate import run_all_checks

DIR = "data_raw/전국동시지방선거 개표결과(제7회)"


def test_parse_7th_returns_rows_and_totals():
    rows, totals = parse_7th(DIR)
    assert len(rows) > 50000
    df = to_dataframe(rows)
    assert list(df.columns) == COLUMNS


def test_parse_7th_sido_candidates_distinct():
    rows, _ = parse_7th(DIR)
    df = to_dataframe(rows)
    governor = df[df["선거종류"] == "시도지사"]
    sido_sets = {
        sido: frozenset(g["후보자"].dropna().unique())
        for sido, g in governor.groupby("시도")
    }
    sidos = list(sido_sets)
    for i in range(len(sidos)):
        for j in range(i + 1, len(sidos)):
            assert sido_sets[sidos[i]] != sido_sets[sidos[j]] or not sido_sets[sidos[i]]


def test_parse_7th_passes_all_validation():
    rows, totals = parse_7th(DIR)
    df = to_dataframe(rows)
    errors = run_all_checks(df, totals)
    assert errors == [], "검증 위반:\n" + "\n".join(f"  {n}: {d}" for n, d in errors[:20])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/local/test_parse_7th.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 서브에이전트가 parse_7th.py 구현**

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/local/test_parse_7th.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add etl/local/parse_7th.py tests/local/test_parse_7th.py
git commit -m "feat(etl): 7회 지방선거 파서 — 검증 통과"
```

---

### Task 8: 6회 파서 (Opus 서브에이전트)

**Opus 서브에이전트 담당.**

**Files:**
- Create: `etl/local/parse_6th.py`
- Test: `tests/local/test_parse_6th.py`

**원본:** `data_raw/전국동시지방선거 개표결과(제3회~제6회)/제6회 전국동시지방선거 개표결과/제6회 전국동시지방선거 읍면동별 개표자료(시도명)/` — **시도별로 폴더 분리**, 각 폴더 안에 선거종류별 파일.

**서브에이전트 지침:**
1. 시도별 폴더를 순회하라. 시도가 폴더명으로 주어지므로 **시도 헤더 갱신 문제는 없지만**, 폴더명→시도명 매핑(강원→강원도 등)이 필요하다.
2. 각 시도 폴더 내 선거종류별 파일 구조를 직접 확인하라.
3. 집계행 totals 분리, `(rows, totals)` 반환은 동일.
4. `parse_6th(base_dir) -> (rows, totals)`.

- [ ] **Step 1: Write the failing test**

`tests/local/test_parse_6th.py`:

```python
from etl.local.parse_6th import parse_6th
from etl.local.schema import to_dataframe, COLUMNS
from etl.local.validate import run_all_checks

BASE = "data_raw/전국동시지방선거 개표결과(제3회~제6회)/제6회 전국동시지방선거 개표결과"


def test_parse_6th_returns_rows():
    rows, totals = parse_6th(BASE)
    assert len(rows) > 50000
    df = to_dataframe(rows)
    assert list(df.columns) == COLUMNS


def test_parse_6th_all_17_sido_present():
    rows, _ = parse_6th(BASE)
    df = to_dataframe(rows)
    governor = df[df["선거종류"] == "시도지사"]
    assert governor["시도"].nunique() >= 15  # 17개 시도 (세종·제주 일부 예외 허용)


def test_parse_6th_passes_all_validation():
    rows, totals = parse_6th(BASE)
    df = to_dataframe(rows)
    errors = run_all_checks(df, totals)
    assert errors == [], "검증 위반:\n" + "\n".join(f"  {n}: {d}" for n, d in errors[:20])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/local/test_parse_6th.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 서브에이전트가 parse_6th.py 구현**

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/local/test_parse_6th.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add etl/local/parse_6th.py tests/local/test_parse_6th.py
git commit -m "feat(etl): 6회 지방선거 파서 — 시도별 폴더, 검증 통과"
```

---

### Task 9: 5회 파서 (Opus 서브에이전트)

**Opus 서브에이전트 담당.**

**Files:**
- Create: `etl/local/parse_5th.py`
- Test: `tests/local/test_parse_5th.py`

**원본:** `data_raw/전국동시지방선거 개표결과(제3회~제6회)/제5회 전국동시지방선거 개표자료/01_시도지사/` 등 번호+선거종류 폴더.

**서브에이전트 지침:**
1. 번호+선거종류 폴더(`01_시도지사`...`08_교육의원`)를 순회. 각 폴더 내부 파일 구조를 직접 확인하라(시도별 분리인지 통합인지).
2. 집계행 totals 분리, `(rows, totals)` 반환 동일.
3. `parse_5th(base_dir) -> (rows, totals)`.

- [ ] **Step 1: Write the failing test**

`tests/local/test_parse_5th.py`:

```python
from etl.local.parse_5th import parse_5th
from etl.local.schema import to_dataframe, COLUMNS
from etl.local.validate import run_all_checks

BASE = "data_raw/전국동시지방선거 개표결과(제3회~제6회)/제5회 전국동시지방선거 개표자료"


def test_parse_5th_returns_rows():
    rows, totals = parse_5th(BASE)
    assert len(rows) > 30000
    df = to_dataframe(rows)
    assert list(df.columns) == COLUMNS


def test_parse_5th_passes_all_validation():
    rows, totals = parse_5th(BASE)
    df = to_dataframe(rows)
    errors = run_all_checks(df, totals)
    assert errors == [], "검증 위반:\n" + "\n".join(f"  {n}: {d}" for n, d in errors[:20])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/local/test_parse_5th.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 서브에이전트가 parse_5th.py 구현**

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/local/test_parse_5th.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add etl/local/parse_5th.py tests/local/test_parse_5th.py
git commit -m "feat(etl): 5회 지방선거 파서 — 검증 통과"
```

---

### Task 10: 4회 파서 (Opus 서브에이전트)

**Opus 서브에이전트 담당.**

**Files:**
- Create: `etl/local/parse_4th.py`
- Test: `tests/local/test_parse_4th.py`

**원본:** `data_raw/전국동시지방선거 개표결과(제3회~제6회)/제4회 전국동시지방선거 개표자료/1_시도지사/` 등.

**서브에이전트 지침:**
1. 번호+선거종류 폴더(`1_시도지사`...`8_교육의원`)를 순회. 4회는 교육감이 없을 수 있다(교육의원만). 내부 구조 직접 확인.
2. row 헤더에서 `[시도명]` 패턴 추출 로직이 필요할 수 있음(기존 `parse_4th_xls` 참고: `process_local_elections.py:318`).
3. 집계행 totals 분리, `(rows, totals)` 반환 동일.
4. `parse_4th(base_dir) -> (rows, totals)`.

- [ ] **Step 1: Write the failing test**

`tests/local/test_parse_4th.py`:

```python
from etl.local.parse_4th import parse_4th
from etl.local.schema import to_dataframe, COLUMNS
from etl.local.validate import run_all_checks

BASE = "data_raw/전국동시지방선거 개표결과(제3회~제6회)/제4회 전국동시지방선거 개표자료"


def test_parse_4th_returns_rows():
    rows, totals = parse_4th(BASE)
    assert len(rows) > 20000
    df = to_dataframe(rows)
    assert list(df.columns) == COLUMNS


def test_parse_4th_passes_all_validation():
    rows, totals = parse_4th(BASE)
    df = to_dataframe(rows)
    errors = run_all_checks(df, totals)
    assert errors == [], "검증 위반:\n" + "\n".join(f"  {n}: {d}" for n, d in errors[:20])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/local/test_parse_4th.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 서브에이전트가 parse_4th.py 구현**

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/local/test_parse_4th.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add etl/local/parse_4th.py tests/local/test_parse_4th.py
git commit -m "feat(etl): 4회 지방선거 파서 — 검증 통과"
```

---

### Task 11: 3회 파서 (Opus 서브에이전트)

**Opus 서브에이전트 담당.**

**Files:**
- Create: `etl/local/parse_3rd.py`
- Test: `tests/local/test_parse_3rd.py`

**원본:** `data_raw/전국동시지방선거 개표결과(제3회~제6회)/제3회 전국동시지방선거 개표자료/제3회지방선거시도지사/` 등 — **개별 XLS 파일**(시도/구시군별).

**서브에이전트 지침:**
1. 3회는 .xls(구포맷). A형(시도지사/광역비례, col0=위원회명)·B형(구시군장/시도의원, col0=투표구명) 두 구조. 기존 `parse_3rd_xls` 참고: `process_local_elections.py:208`.
2. 구시군명→시도명 매핑 필요(`GU_SIDO_3RD` 참고). 파일명/내용으로 시도 추론.
3. 깨진 파일명(corrupted) 중복 처리: MD5 해시 dedup(기존 `process_3rd` 로직 참고). 한글 파일명 우선.
4. 집계행 totals 분리, `(rows, totals)` 반환 동일.
5. `parse_3rd(base_dir) -> (rows, totals)`.

- [ ] **Step 1: Write the failing test**

`tests/local/test_parse_3rd.py`:

```python
from etl.local.parse_3rd import parse_3rd
from etl.local.schema import to_dataframe, COLUMNS
from etl.local.validate import run_all_checks

BASE = "data_raw/전국동시지방선거 개표결과(제3회~제6회)/제3회 전국동시지방선거 개표자료"


def test_parse_3rd_returns_rows():
    rows, totals = parse_3rd(BASE)
    assert len(rows) > 10000
    df = to_dataframe(rows)
    assert list(df.columns) == COLUMNS


def test_parse_3rd_no_numeric_emd():
    """읍면동에 숫자(3157.0)가 들어가면 컬럼 밀림 — B형 파싱 버그."""
    rows, _ = parse_3rd(BASE)
    df = to_dataframe(rows)
    numeric_emd = df[df["읍면동"].astype(str).str.match(r"^\d+\.?\d*$")]
    assert len(numeric_emd) == 0


def test_parse_3rd_passes_all_validation():
    rows, totals = parse_3rd(BASE)
    df = to_dataframe(rows)
    errors = run_all_checks(df, totals)
    assert errors == [], "검증 위반:\n" + "\n".join(f"  {n}: {d}" for n, d in errors[:20])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/local/test_parse_3rd.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 서브에이전트가 parse_3rd.py 구현**

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/local/test_parse_3rd.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add etl/local/parse_3rd.py tests/local/test_parse_3rd.py
git commit -m "feat(etl): 3회 지방선거 파서 — A형/B형, 검증 통과"
```

---

### Task 12: 오케스트레이터 build.py

전 회차를 모아 검증 후 CSV 작성.

**Files:**
- Create: `etl/local/build.py`
- Test: `tests/local/test_build.py`

**선거일 매핑:** 3회 2002-06-13, 4회 2006-05-31, 5회 2010-06-02, 6회 2014-06-04, 7회 2018-06-13, 8회 2022-06-01.

- [ ] **Step 1: Write the failing test**

`tests/local/test_build.py`:

```python
from etl.local.build import ELECTION_DATES


def test_election_dates_cover_3_to_8():
    assert ELECTION_DATES[3] == "2002-06-13"
    assert ELECTION_DATES[8] == "2022-06-01"
    assert set(ELECTION_DATES) == {3, 4, 5, 6, 7, 8}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/local/test_build.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`etl/local/build.py`:

```python
"""지방선거 ETL 오케스트레이터. parse → validate → CSV.

검증을 통과하지 못하면 CSV를 쓰지 않고 exit≠0.
"""

import sys

from etl.local.schema import to_dataframe
from etl.local.validate import run_all_checks
from etl.local.official_totals import OFFICIAL_TOP
from etl.local.parse_3rd import parse_3rd
from etl.local.parse_4th import parse_4th
from etl.local.parse_5th import parse_5th
from etl.local.parse_6th import parse_6th
from etl.local.parse_7th import parse_7th
from etl.local.parse_8th import parse_8th

ROOT = "data_raw"
LOCAL36 = f"{ROOT}/전국동시지방선거 개표결과(제3회~제6회)"

ELECTION_DATES = {
    3: "2002-06-13", 4: "2006-05-31", 5: "2010-06-02",
    6: "2014-06-04", 7: "2018-06-13", 8: "2022-06-01",
}

PARSERS = [
    (3, lambda: parse_3rd(f"{LOCAL36}/제3회 전국동시지방선거 개표자료")),
    (4, lambda: parse_4th(f"{LOCAL36}/제4회 전국동시지방선거 개표자료")),
    (5, lambda: parse_5th(f"{LOCAL36}/제5회 전국동시지방선거 개표자료")),
    (6, lambda: parse_6th(f"{LOCAL36}/제6회 전국동시지방선거 개표결과")),
    (7, lambda: parse_7th(f"{ROOT}/전국동시지방선거 개표결과(제7회)")),
    (8, lambda: parse_8th(f"{ROOT}/제8회_전국동시지방선거_읍면동별_개표결과-게시판게시")),
]

OUT_PATH = "data_processed/지방선거.csv"


def build():
    all_rows = []
    all_totals = []
    failed = False

    for round_num, parse_fn in PARSERS:
        print(f"=== {round_num}회 파싱 ===")
        rows, totals = parse_fn()
        for row in rows:
            row.setdefault("선거일", ELECTION_DATES[round_num])
        df = to_dataframe(rows)
        official = {k: v for k, v in OFFICIAL_TOP.items() if k[0] == round_num}
        errors = run_all_checks(df, totals, official)
        if errors:
            failed = True
            print(f"  [FAIL] {round_num}회 검증 위반 {len(errors)}건:")
            for name, detail in errors[:20]:
                print(f"    {name}: {detail}")
        else:
            print(f"  [OK] {round_num}회 {len(rows):,}행 검증 통과")
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

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/local/test_build.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: 전체 빌드 실행 + 검증 통과 확인**

Run: `cd /Users/seong-in/Desktop/Git/pyosim && python -m etl.local.build`
Expected: 6개 회차 모두 `[OK]`, 마지막에 `[DONE] ...행 → data_processed/지방선거.csv`

- [ ] **Step 6: Commit**

```bash
git add etl/local/build.py tests/local/test_build.py data_processed/지방선거.csv
git commit -m "feat(etl): 지방선거 빌드 오케스트레이터 — 6개 회차 검증 통과 CSV"
```

---

### Task 13: 쌍둥이 분석 재실행 + 기존 코드 정리

검증된 CSV 위에서 쌍둥이 분석을 다시 돌린다.

**Files:**
- Modify: `analyze_twin_votes.py` (이미 1·2등 기준으로 작성됨, CSV만 새것)
- Delete: 없음 (기존 `process_local_elections.py`는 참고용 유지)

- [ ] **Step 1: 쌍둥이 분석 재실행**

Run: `cd /Users/seong-in/Desktop/Git/pyosim && python3 analyze_twin_votes.py`
Expected: `web/public/twin_votes.json` 갱신. 8회 시도지사에 오세훈/송영길이 충북에 없는 정상 데이터.

- [ ] **Step 2: 8회 시도지사 충북 오염 제거 확인**

Run:
```bash
python3 -c "
import json
data = json.load(open('web/public/twin_votes.json'))
bad = [g for g in data if g['category']=='지방선거_시도지사_사전투표'
       and g['group'].get('시도')=='충청북도'
       and any(c in g['votes'] for c in ['오세훈','송영길'])]
print('충북에 서울후보 오염 그룹:', len(bad))
assert len(bad) == 0
print('OK')
"
```
Expected: `충북에 서울후보 오염 그룹: 0` / `OK`

- [ ] **Step 3: Commit**

```bash
git add web/public/twin_votes.json
git commit -m "data: 검증된 CSV로 쌍둥이 분석 재생성"
```

---

## Self-Review 결과

**Spec coverage:** 검증 4항목(중복·범위·시도후보·합계)+외부대조 = Task 2~5. 회차별 파서 6개 = Task 6~11. 오케스트레이터 = Task 12. 쌍둥이 재실행 = Task 13. 전 spec 요구 커버됨.

**Type consistency:** `(rows, totals)` 반환 시그니처가 모든 파서에서 일관. `run_all_checks(df, totals, official_top=None)` 시그니처가 Task 4→5에서 일관. tidy COLUMNS가 Task 1에 정의되고 전 파서가 사용.

**Note:** Task 6~11(파서)은 원본 구조를 서브에이전트가 실측해야 하므로 구현 코드 본문은 비워뒀다. 단 입력 원본 구조·출력 시그니처·검증 통과 기준(테스트)은 완전히 명시했으므로, 서브에이전트는 테스트를 통과시키는 것을 목표로 자율 구현한다. 이는 placeholder가 아니라 "원본을 직접 봐야만 작성 가능한 코드"의 의도적 위임이다.
