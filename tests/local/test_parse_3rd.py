from etl.local.parse_3rd import parse_3rd
from etl.local.schema import to_dataframe, COLUMNS
from etl.local.validate import run_all_checks
from etl.local.official_totals import OFFICIAL_TOP

BASE = "data_raw/전국동시지방선거 개표결과(제3회~제6회)/제3회 전국동시지방선거 개표자료"


def test_parse_3rd_returns_rows():
    rows, totals = parse_3rd(BASE)
    assert len(rows) > 10000
    df = to_dataframe(rows)
    assert list(df.columns) == COLUMNS


def test_parse_3rd_no_numeric_emd():
    """읍면동/투표구에 숫자(3157.0)가 들어가면 컬럼 밀림 — 파싱 버그."""
    rows, _ = parse_3rd(BASE)
    df = to_dataframe(rows)
    numeric_emd = df[df["읍면동"].astype(str).str.match(r"^\d+\.?\d*$")]
    assert len(numeric_emd) == 0


def test_parse_3rd_passes_all_validation():
    rows, totals = parse_3rd(BASE)
    for row in rows:
        row.setdefault("선거일", "2002-06-13")
    df = to_dataframe(rows)
    official = {k: v for k, v in OFFICIAL_TOP.items() if k[0] == 3}
    errors = run_all_checks(df, totals, official)
    assert errors == [], "검증 위반:\n" + "\n".join(f"  {n}: {d}" for n, d in errors[:20])
