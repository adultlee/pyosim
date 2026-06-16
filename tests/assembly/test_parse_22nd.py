import pytest
import pandas as pd
from etl.assembly.parse_22nd import parse_22nd
from etl.assembly.schema import COLUMNS


def test_parse_22nd_returns_tuple():
    rows, totals = parse_22nd()
    assert isinstance(rows, list)
    assert isinstance(totals, list)


def test_parse_22nd_row_columns():
    rows, _ = parse_22nd()
    assert len(rows) > 0
    first = rows[0]
    for col in COLUMNS:
        assert col in first, f"Missing column: {col}"


def test_parse_22nd_round():
    rows, _ = parse_22nd()
    assert all(r["선거_회차"] == "제22대" for r in rows)


def test_parse_22nd_선거구분():
    rows, _ = parse_22nd()
    districts = {r["선거구분"] for r in rows}
    assert "지역구" in districts
    assert "비례대표" in districts


def test_parse_22nd_totals_have_required_keys():
    _, totals = parse_22nd()
    for total in totals:
        assert "선거구분" in total
        assert "시도" in total
        assert "선거구명" in total
        assert "투표수" in total
