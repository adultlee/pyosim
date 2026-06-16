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


from etl.local.validate import check_totals_match, run_all_checks


def test_totals_match_passes():
    rows = [
        _row(읍면동="청운효자동", level="당일투표", 투표수=3155, 후보자="오세훈", 득표수=1802),
        _row(읍면동="청운효자동", level="당일투표", 투표수=3155, 후보자="송영길", 득표수=1246),
        _row(읍면동="청운효자동", level="사전투표", 투표수=1732, 후보자="오세훈", 득표수=828),
        _row(읍면동="청운효자동", level="사전투표", 투표수=1732, 후보자="송영길", 득표수=848),
    ]
    df = to_dataframe(rows)
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


def test_sido_candidate_consistency_ignores_proportional():
    """광역비례는 정당 단위라 모든 시도에서 같은 정당 집합이 정상. 오탐 금지."""
    rows = []
    for sido in ["서울특별시", "부산광역시"]:
        for party in ["더불어민주당", "국민의힘", "정의당"]:
            rows.append(_row(선거종류="광역비례", 시도=sido,
                             구시군="중구", 읍면동="중앙동",
                             후보자=None, 정당=party, 득표수=100))
    df = to_dataframe(rows)
    assert check_sido_candidate_consistency(df) == []


def test_value_ranges_flags_turnout_exceeds_electorate():
    df = to_dataframe([_row(득표수=10, 투표수=9999, 선거인수=7447)])
    errors = check_value_ranges(df)
    assert any(name == "value_range" for name, _ in errors)


def test_value_ranges_ignores_nan_electorate():
    df = to_dataframe([_row(득표수=10, 투표수=20, 선거인수=None)])
    # 선거인수 NaN이면 상한 검사 스킵 (득표≤투표는 통과)
    assert check_value_ranges(df) == []


from etl.local.validate import check_official_totals
from etl.local.official_totals import OFFICIAL_TOP


def test_official_totals_passes_when_match():
    rows = []
    for level, votes in [("당일투표", 2000000), ("사전투표", 608277)]:
        rows.append(_row(시도="서울특별시", 구시군="종로구", 읍면동="청운효자동",
                         level=level, 후보자="오세훈", 득표수=votes))
    df = to_dataframe(rows)
    assert check_official_totals(df, OFFICIAL_TOP) == []


def test_official_totals_flags_mismatch():
    rows = [_row(시도="서울특별시", 후보자="오세훈", 득표수=5)]
    df = to_dataframe(rows)
    errors = check_official_totals(df, OFFICIAL_TOP)
    assert any(name == "official_mismatch" for name, _ in errors)
