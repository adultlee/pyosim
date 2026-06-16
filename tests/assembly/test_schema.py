import pytest
from etl.assembly.schema import COLUMNS, normalize_level, to_dataframe


def test_columns_include_투표구():
    assert "투표구" in COLUMNS
    assert "선거구분" in COLUMNS
    assert "선거_회차" in COLUMNS


def test_normalize_level_known():
    assert normalize_level("관내사전투표") == "사전투표"
    assert normalize_level("관외사전투표") == "관외사전투표"
    assert normalize_level("거소·선상투표") == "거소선상"
    assert normalize_level("국외부재자투표") == "재외투표"
    assert normalize_level("재외투표") == "재외투표"


def test_normalize_level_unknown_returns_당일투표():
    assert normalize_level("제1투표구") == "당일투표"
    assert normalize_level("") == "당일투표"
    assert normalize_level(None) == "당일투표"


def test_to_dataframe_columns():
    import pandas as pd
    rows = [{"선거_회차": "제22대", "선거일": "2024-04-10", "선거구분": "지역구",
             "시도": "서울", "구시군": "종로구", "읍면동": "청운효자동", "투표구": "제1투표구",
             "선거구명": "서울 종로구", "선거인수": 100, "투표수": 80,
             "후보자": "홍길동", "정당": "더불어민주당", "득표수": 50,
             "무효투표수": 2, "기권수": 18, "level": "당일투표"}]
    df = to_dataframe(rows)
    assert list(df.columns) == COLUMNS
    assert len(df) == 1
