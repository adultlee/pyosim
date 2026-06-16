from etl.local.parse_6th import parse_6th
from etl.local.schema import to_dataframe, COLUMNS
from etl.local.validate import run_all_checks
from etl.local.official_totals import OFFICIAL_TOP

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
    assert governor["시도"].nunique() >= 15


def test_parse_6th_passes_all_validation():
    rows, totals = parse_6th(BASE)
    for row in rows:
        row.setdefault("선거일", "2014-06-04")
    df = to_dataframe(rows)
    official = {k: v for k, v in OFFICIAL_TOP.items() if k[0] == 6}
    errors = run_all_checks(df, totals, official)
    assert errors == [], "검증 위반:\n" + "\n".join(f"  {n}: {d}" for n, d in errors[:20])
