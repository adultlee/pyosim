from etl.assembly.parse_21st import parse_21st
from etl.assembly.schema import to_dataframe, COLUMNS
from etl.assembly.validate import run_all_checks
from etl.assembly.official_totals import OFFICIAL_TOP


def test_parse_21st_returns_tuple():
    rows, totals = parse_21st()
    assert isinstance(rows, list)
    assert isinstance(totals, list)


def test_parse_21st_row_columns():
    rows, _ = parse_21st()
    assert len(rows) > 0
    df = to_dataframe(rows)
    assert list(df.columns) == COLUMNS


def test_parse_21st_round():
    rows, _ = parse_21st()
    assert all(r["선거_회차"] == "제21대" for r in rows)


def test_parse_21st_선거구분():
    rows, _ = parse_21st()
    districts = {r["선거구분"] for r in rows}
    assert "지역구" in districts
    assert "비례대표" in districts


def test_parse_21st_passes_validation():
    rows, totals = parse_21st()
    df = to_dataframe(rows)
    official = {k: v for k, v in OFFICIAL_TOP.items() if k[0] == "제21대"}
    errors = run_all_checks(df, totals, official or None)
    assert errors == [], "검증 위반:\n" + "\n".join(f"  {n}: {d}" for n, d in errors[:20])
