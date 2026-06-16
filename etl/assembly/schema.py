"""총선 tidy row 스키마 정의."""

import pandas as pd

COLUMNS = [
    "선거_회차", "선거일", "선거구분", "시도", "구시군", "읍면동", "투표구",
    "선거구명", "선거인수", "투표수", "후보자", "정당", "득표수", "무효투표수", "기권수", "level",
]

LEVEL_MAP = {
    "관내사전투표": "사전투표",
    "관외사전투표": "관외사전투표",
    "거소·선상투표": "거소선상",
    "국외부재자투표": "재외투표",
    "재외투표": "재외투표",
}


def normalize_level(raw):
    """투표구명으로 level 판단. 미매핑이면 '당일투표'."""
    key = str(raw or "").strip()
    return LEVEL_MAP.get(key, "당일투표")


def to_dataframe(rows):
    """tidy row dict 리스트를 COLUMNS 순서의 DataFrame으로."""
    return pd.DataFrame(rows, columns=COLUMNS)
