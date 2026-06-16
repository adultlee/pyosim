from etl.assembly.parse_19th import parse_19th
from etl.assembly.schema import to_dataframe, COLUMNS
from etl.assembly.validate import run_all_checks
from etl.assembly.official_totals import OFFICIAL_TOP


def test_parse_19th_returns_tuple():
    rows, totals = parse_19th()
    assert isinstance(rows, list)
    assert isinstance(totals, list)


def test_parse_19th_row_columns():
    rows, _ = parse_19th()
    assert len(rows) > 0
    df = to_dataframe(rows)
    assert list(df.columns) == COLUMNS


def test_parse_19th_round():
    rows, _ = parse_19th()
    assert all(r["선거_회차"] == "제19대" for r in rows)


def test_parse_19th_선거구분():
    rows, _ = parse_19th()
    districts = {r["선거구분"] for r in rows}
    assert "지역구" in districts
    assert "비례대표" in districts


def test_parse_19th_passes_validation():
    rows, totals = parse_19th()
    df = to_dataframe(rows)
    official = {k: v for k, v in OFFICIAL_TOP.items() if k[0] == "제19대"}
    errors = run_all_checks(df, totals, official or None)
    assert errors == [], "검증 위반:\n" + "\n".join(f"  {n}: {d}" for n, d in errors[:20])
