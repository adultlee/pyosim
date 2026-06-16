import pandas as pd
import pytest
from etl.assembly.validate import (
    check_no_duplicate_rows,
    check_value_ranges,
    check_totals_match,
    check_official_totals,
    run_all_checks,
)
from etl.assembly.schema import COLUMNS


def _make_row(**kwargs):
    defaults = {
        "선거_회차": "제22대", "선거일": "2024-04-10", "선거구분": "지역구",
        "시도": "서울", "구시군": "종로구", "읍면동": "청운효자동", "투표구": "제1투표구",
        "선거구명": "서울 종로", "선거인수": 1000, "투표수": 800,
        "후보자": "홍길동", "정당": "더불어민주당", "득표수": 400,
        "무효투표수": 10, "기권수": 190, "level": "당일투표",
    }
    defaults.update(kwargs)
    return defaults


def test_no_duplicate_rows_pass():
    rows = [_make_row(후보자="홍길동"), _make_row(후보자="김철수")]
    df = pd.DataFrame(rows, columns=COLUMNS)
    assert check_no_duplicate_rows(df) == []


def test_no_duplicate_rows_fail():
    rows = [_make_row(), _make_row()]
    df = pd.DataFrame(rows, columns=COLUMNS)
    errors = check_no_duplicate_rows(df)
    assert len(errors) > 0
    assert errors[0][0] == "duplicate_rows"


def test_value_ranges_pass():
    rows = [_make_row(선거인수=1000, 투표수=800, 득표수=400)]
    df = pd.DataFrame(rows, columns=COLUMNS)
    assert check_value_ranges(df) == []


def test_value_ranges_fail_득표_over_투표():
    rows = [_make_row(투표수=100, 득표수=101)]
    df = pd.DataFrame(rows, columns=COLUMNS)
    errors = check_value_ranges(df)
    assert any(e[0] == "value_range" for e in errors)


def test_value_ranges_fail_투표_over_선거인():
    rows = [_make_row(선거인수=100, 투표수=101, 득표수=50)]
    df = pd.DataFrame(rows, columns=COLUMNS)
    errors = check_value_ranges(df)
    assert any(e[0] == "value_range" for e in errors)


def test_totals_match_pass():
    rows = [
        _make_row(후보자="홍길동", 투표수=800),
        _make_row(후보자="김철수", 투표수=800),
    ]
    df = pd.DataFrame(rows, columns=COLUMNS)
    totals = [{"선거구분": "지역구", "시도": "서울", "선거구명": "서울 종로", "투표수": 800}]
    assert check_totals_match(df, totals) == []


def test_totals_match_fail():
    rows = [_make_row(후보자="홍길동", 투표수=800)]
    df = pd.DataFrame(rows, columns=COLUMNS)
    totals = [{"선거구분": "지역구", "시도": "서울", "선거구명": "서울 종로", "투표수": 900}]
    errors = check_totals_match(df, totals)
    assert len(errors) == 1
    assert errors[0][0] == "totals_mismatch"


def test_official_totals_pass():
    rows = [_make_row(후보자="홍길동", 득표수=500)]
    df = pd.DataFrame(rows, columns=COLUMNS)
    official = {("제22대", "지역구", "서울"): ("홍길동", 500)}
    assert check_official_totals(df, official) == []


def test_official_totals_fail():
    rows = [_make_row(후보자="홍길동", 득표수=400)]
    df = pd.DataFrame(rows, columns=COLUMNS)
    official = {("제22대", "지역구", "서울"): ("홍길동", 500)}
    errors = check_official_totals(df, official)
    assert errors[0][0] == "official_mismatch"


def test_run_all_checks_clean():
    rows = [_make_row(후보자="홍길동"), _make_row(후보자="김철수")]
    df = pd.DataFrame(rows, columns=COLUMNS)
    assert run_all_checks(df, []) == []
