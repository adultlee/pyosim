from etl.pres.schema import COLUMNS, LEVEL_MAP, to_dataframe, normalize_level


def test_columns_order():
    assert COLUMNS == [
        "선거_회차", "선거일", "시도", "구시군", "읍면동", "투표구",
        "선거인수", "투표수", "후보자", "정당", "득표수", "무효투표수", "기권수", "level",
    ]


def test_normalize_level():
    assert normalize_level("관내사전투표") == "사전투표"
    assert normalize_level("관외사전투표") == "관외사전투표"
    assert normalize_level("거소·선상투표") == "거소선상"
    assert normalize_level("재외투표") == "재외투표"
    assert normalize_level("재외투표(공관)") == "재외투표"
    assert normalize_level("") == "당일투표"
    assert normalize_level("청운동") == "당일투표"  # 읍면동명은 당일투표


def test_to_dataframe_has_all_columns():
    rows = [{
        "선거_회차": 21, "선거일": "2025-06-03",
        "시도": "서울특별시", "구시군": "종로구", "읍면동": "청운효자동", "투표구": "",
        "선거인수": 7447, "투표수": 3155,
        "후보자": "이재명", "정당": "더불어민주당", "득표수": 1802,
        "무효투표수": 62, "기권수": None, "level": "당일투표",
    }]
    df = to_dataframe(rows)
    assert list(df.columns) == COLUMNS
    assert len(df) == 1
