import pandas as pd
from etl.local.schema import COLUMNS, LEVEL_MAP, to_dataframe, normalize_level


def test_columns_order():
    assert COLUMNS == [
        "선거_회차", "선거일", "선거종류", "시도", "구시군", "읍면동",
        "선거구명", "선거인수", "투표수", "후보자", "정당", "득표수",
        "무효투표수", "기권수", "level",
    ]


def test_normalize_level():
    assert normalize_level("선거일투표") == "당일투표"
    assert normalize_level("관내사전투표") == "사전투표"
    assert normalize_level("관외사전투표") == "관외사전투표"
    assert normalize_level("거소투표") == "거소선상"
    assert normalize_level("거소·선상투표") == "거소선상"
    assert normalize_level("선상투표") == "거소선상"
    # 오투입표 라벨은 회차 무관하게 '잘못투입'으로 통일
    assert normalize_level("잘못 투입·구분된 투표지") == "잘못투입"
    assert normalize_level("잘못투입된투표지") == "잘못투입"
    assert normalize_level("잘못투입") == "잘못투입"


def test_to_dataframe_has_all_columns():
    rows = [{
        "선거_회차": 8, "선거일": "2022-06-01", "선거종류": "시도지사",
        "시도": "서울특별시", "구시군": "종로구", "읍면동": "청운효자동",
        "선거구명": "서울특별시", "선거인수": 7447, "투표수": 3155,
        "후보자": "오세훈", "정당": "국민의힘", "득표수": 1802,
        "무효투표수": 62, "기권수": None, "level": "당일투표",
    }]
    df = to_dataframe(rows)
    assert list(df.columns) == COLUMNS
    assert len(df) == 1
