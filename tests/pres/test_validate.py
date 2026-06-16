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
