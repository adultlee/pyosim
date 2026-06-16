from etl.local.parse_7th import parse_7th
from etl.local.schema import to_dataframe, COLUMNS
from etl.local.validate import run_all_checks
from etl.local.official_totals import OFFICIAL_TOP

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
        sido: frozenset(group["후보자"].dropna().unique())
        for sido, group in governor.groupby("시도")
    }
    sidos = list(sido_sets)
    for first_idx in range(len(sidos)):
        for second_idx in range(first_idx + 1, len(sidos)):
            left, right = sido_sets[sidos[first_idx]], sido_sets[sidos[second_idx]]
            assert left != right or not left


def test_parse_7th_passes_all_validation():
    rows, totals = parse_7th(DIR)
    for row in rows:
        row.setdefault("선거일", "2018-06-13")
    df = to_dataframe(rows)
    official = {k: v for k, v in OFFICIAL_TOP.items() if k[0] == 7}
    errors = run_all_checks(df, totals, official)
    assert errors == [], "검증 위반:\n" + "\n".join(f"  {n}: {d}" for n, d in errors[:20])
