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
