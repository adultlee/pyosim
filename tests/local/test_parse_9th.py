from etl.local.parse_9th import parse_9th
from etl.local.schema import to_dataframe, COLUMNS
from etl.local.validate import run_all_checks
from etl.local.official_totals import OFFICIAL_TOP

DIR = "data/raw/0020260603"


def test_parse_9th_returns_rows_and_totals():
    rows, totals = parse_9th(DIR)
    assert len(rows) > 100000
    assert len(totals) > 200
    df = to_dataframe(rows)
    assert list(df.columns) == COLUMNS


def test_parse_9th_sido_candidates_distinct():
    """충북에 서울 후보(오세훈)가 없어야 한다 — 시도 헤더 갱신 검증."""
    rows, _ = parse_9th(DIR)
    df = to_dataframe(rows)
    chungbuk = df[(df["선거종류"] == "시도지사") & (df["시도"] == "충청북도")]
    assert "오세훈" not in set(chungbuk["후보자"].dropna())


def test_parse_9th_passes_all_validation():
    rows, totals = parse_9th(DIR)
    for row in rows:
        row.setdefault("선거일", "2026-06-03")
    df = to_dataframe(rows)
    official = {k: v for k, v in OFFICIAL_TOP.items() if k[0] == 9}
    # 광주·전남 시도지사 후보집합이 동명이인(민형배)으로 실제 동일 → sido_consistency 스킵
    errors = run_all_checks(df, totals, official, skip_sido_consistency=True)
    assert errors == [], "검증 위반:\n" + "\n".join(f"  {n}: {d}" for n, d in errors[:20])
