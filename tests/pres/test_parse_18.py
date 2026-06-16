from etl.pres.parse_18 import parse_18
from etl.pres.schema import to_dataframe, COLUMNS
from etl.pres.validate import run_all_checks
from etl.pres.official_totals import OFFICIAL_TOP

ELECTION_DATE = "2012-12-19"


def test_parse_18_returns_rows_and_totals():
    rows, totals = parse_18()
    assert len(rows) > 0
    assert isinstance(totals, list)
    df = to_dataframe(rows)
    assert list(df.columns) == COLUMNS


def test_parse_18_no_nan_sido():
    rows, _ = parse_18()
    df = to_dataframe(rows)
    assert df["시도"].isna().sum() == 0


def test_parse_18_passes_all_validation():
    rows, totals = parse_18()
    for row in rows:
        row.setdefault("선거일", ELECTION_DATE)
    df = to_dataframe(rows)
    official = {k: v for k, v in OFFICIAL_TOP.items() if k[0] == 18}
    errors = run_all_checks(df, totals, official or None)
    assert errors == [], "검증 위반:\n" + "\n".join(f"  {n}: {d}" for n, d in errors[:20])
